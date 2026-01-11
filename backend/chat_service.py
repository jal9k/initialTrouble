"""
Core chat service for TechTim(e).

This module contains the ChatService class which orchestrates conversations
with the LLM, including multi-turn tool execution. It is designed to be
called either from:
- FastAPI routes (HTTP/WebSocket mode)
- PyWebView API bridge (desktop mode)

The service is stateful and maintains conversation history per session.

NOTE: This is extracted from main.py to support desktop mode while
preserving all existing patterns including analytics integration.
"""
import asyncio
import uuid
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Any
from datetime import datetime

from .config import get_settings
from .llm import LLMRouter, ChatMessage
from .tools import ToolRegistry, get_registry
from .prompts import AgentType, load_prompt

if TYPE_CHECKING:
    from analytics import AnalyticsCollector, AnalyticsStorage

logger = logging.getLogger("techtime.chat_service")


# =============================================================================
# Response Models (matching main.py patterns)
# =============================================================================

@dataclass
class ToolUsedInfo:
    """Information about a tool that was used."""
    name: str
    success: bool
    duration_ms: int | None = None


@dataclass
class ResponseDiagnosticsData:
    """Diagnostics information about the response."""
    confidence_score: float = 0.5
    thoughts: list[str] = field(default_factory=list)
    tools_used: list[ToolUsedInfo] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "confidence_score": self.confidence_score,
            "thoughts": self.thoughts,
            "tools_used": [
                {"name": t.name, "success": t.success, "duration_ms": t.duration_ms}
                for t in self.tools_used
            ],
        }


@dataclass
class ChatServiceResponse:
    """
    Response from a completed chat turn.
    
    Matches the structure of ChatResponseModel in main.py.
    """
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    session_id: str | None = None
    diagnostics: ResponseDiagnosticsData | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "response": self.content,
            "tool_calls": self.tool_calls,
            "conversation_id": self.session_id,
            "diagnostics": self.diagnostics.to_dict() if self.diagnostics else None,
        }


@dataclass
class StreamChunk:
    """
    A chunk of streaming response data.
    
    Used for real-time updates during chat processing.
    """
    type: str  # "content", "tool_call", "tool_result", "done", "error"
    data: dict


# =============================================================================
# Chat Service
# =============================================================================

class ChatService:
    """
    Orchestrates chat interactions with LLM and tool execution.
    
    This service manages the conversation loop where:
    1. User sends a message
    2. LLM processes and may request tool calls
    3. Tools are executed
    4. Results are fed back to LLM
    5. Loop continues until LLM provides a final response
    
    The service integrates with analytics for session tracking.
    
    Example:
        service = ChatService()
        await service.initialize()
        response = await service.chat("session-123", "My WiFi isn't working")
        print(response.content)
    """
    
    def __init__(
        self,
        llm_router: LLMRouter | None = None,
        tool_registry: ToolRegistry | None = None,
        analytics_collector: "AnalyticsCollector | None" = None,
        analytics_storage: "AnalyticsStorage | None" = None,
    ):
        """
        Initialize the chat service.
        
        Args:
            llm_router: LLM client router. If None, creates on initialize().
            tool_registry: Tool registry. If None, uses the global registry.
            analytics_collector: Analytics collector for tracking.
            analytics_storage: Analytics storage for persistence.
        """
        self._settings = get_settings()
        self._llm_router = llm_router
        self._tool_registry = tool_registry
        self._analytics_collector = analytics_collector
        self._analytics_storage = analytics_storage
        
        # In-memory conversation state
        self._conversations: dict[str, list[ChatMessage]] = {}
        self._session_map: dict[str, str] = {}  # conv_id -> analytics session_id
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize the service (call once at startup).
        
        This sets up the LLM router, tool registry, and analytics.
        """
        if self._initialized:
            return
        
        # Initialize LLM router
        if self._llm_router is None:
            self._llm_router = LLMRouter(
                self._settings,
                analytics_collector=self._analytics_collector
            )
        
        # Initialize tool registry
        if self._tool_registry is None:
            self._tool_registry = get_registry()
        
        # Connect analytics to tool registry
        if self._analytics_collector and self._tool_registry:
            self._tool_registry.set_analytics(self._analytics_collector)
        
        # Register diagnostic tools
        from .diagnostics import register_all_diagnostics
        register_all_diagnostics(self._tool_registry)
        
        self._initialized = True
        logger.info(
            f"ChatService initialized with {len(self._tool_registry)} tools"
        )
    
    def set_analytics(
        self,
        collector: "AnalyticsCollector",
        storage: "AnalyticsStorage",
    ) -> None:
        """Set analytics collector and storage after initialization."""
        self._analytics_collector = collector
        self._analytics_storage = storage
        
        if self._llm_router:
            self._llm_router.set_analytics(collector)
        if self._tool_registry:
            self._tool_registry.set_analytics(collector)
    
    def _get_or_create_conversation(
        self,
        session_id: str | None,
    ) -> tuple[str, list[ChatMessage], bool]:
        """
        Get or create a conversation.
        
        Returns:
            Tuple of (conversation_id, messages, is_new)
        """
        conv_id = session_id or str(uuid.uuid4())
        is_new = conv_id not in self._conversations
        
        if is_new:
            # Initialize with system prompt (diagnostic agent)
            system_prompt = load_prompt(AgentType.DIAGNOSTIC)
            self._conversations[conv_id] = [
                ChatMessage(role="system", content=system_prompt)
            ]
            
            # Start analytics session
            if self._analytics_collector:
                session = self._analytics_collector.start_session(session_id=conv_id)
                self._session_map[conv_id] = session.session_id
            
            logger.debug(f"Created new conversation: {conv_id}")
        
        return conv_id, self._conversations[conv_id], is_new
    
    async def chat(
        self,
        session_id: str | None,
        user_message: str,
        max_tool_rounds: int | None = None,
    ) -> ChatServiceResponse:
        """
        Process a chat message and return the complete response.
        
        This method blocks until the LLM finishes generating its response
        and all tool calls have been executed.
        
        Args:
            session_id: The conversation session ID (creates new if None)
            user_message: The user's input message
            max_tool_rounds: Maximum tool execution iterations (default from settings)
        
        Returns:
            ChatServiceResponse with the assistant's reply and any tool results
        """
        if not self._initialized:
            await self.initialize()
        
        if max_tool_rounds is None:
            max_tool_rounds = self._settings.max_tool_rounds
        
        conv_id, messages, is_new = self._get_or_create_conversation(session_id)
        
        # Initialize diagnostics tracking
        diagnostics = ResponseDiagnosticsData()
        diagnostics.thoughts.append(f"Processing user message: {len(user_message)} chars")
        
        # Record user message in analytics
        if self._analytics_collector:
            self._analytics_collector.record_user_message(user_message)
        
        # Add user message
        user_msg = ChatMessage(role="user", content=user_message)
        messages.append(user_msg)
        
        # Persist user message to database
        if self._analytics_storage:
            from analytics.models import ChatMessage as DBChatMessage
            self._analytics_storage.save_message(
                DBChatMessage(
                    session_id=conv_id,
                    role="user",
                    content=user_message,
                )
            )
        
        logger.info(f"[{conv_id}] Processing message: {user_message[:100]}...")
        
        # Get tool definitions
        tools = self._tool_registry.get_all_definitions()
        diagnostics.thoughts.append(f"Available tools: {len(tools)}")
        
        # Multi-turn tool execution loop (from main.py pattern)
        tool_results: list[dict] = []
        
        for iteration in range(max_tool_rounds):
            # Force tool call on first iteration, allow auto on subsequent
            tool_choice = "required" if iteration == 0 else "auto"
            
            diagnostics.thoughts.append(
                f"Tool loop iteration {iteration + 1}, tool_choice={tool_choice}"
            )
            
            response = await self._llm_router.chat(
                messages=messages,
                tools=tools,
                temperature=0.3,
                tool_choice=tool_choice,
            )
            
            # Update session backend info after first LLM call
            if iteration == 0 and is_new and self._analytics_collector:
                if self._llm_router.active_backend:
                    self._analytics_collector.set_session_backend(
                        backend=self._llm_router.active_backend,
                        model_name=self._llm_router.active_model or "unknown",
                        had_fallback=self._llm_router.had_fallback,
                    )
            
            # If no tool calls, we're done with the loop
            if not response.has_tool_calls or not response.message.tool_calls:
                diagnostics.thoughts.append(
                    f"No tool calls in iteration {iteration + 1}, ending loop"
                )
                break
            
            # Add assistant message with tool_calls to conversation
            messages.append(response.message)
            diagnostics.thoughts.append(
                f"LLM requested {len(response.message.tool_calls)} tool call(s)"
            )
            
            # Execute each tool call
            for tool_call in response.message.tool_calls:
                tool_start_time = time.perf_counter()
                
                result = await self._tool_registry.execute(tool_call)
                tool_duration_ms = int((time.perf_counter() - tool_start_time) * 1000)
                
                # Track tool in diagnostics
                diagnostics.tools_used.append(ToolUsedInfo(
                    name=tool_call.name,
                    success=result.success,
                    duration_ms=tool_duration_ms
                ))
                diagnostics.thoughts.append(
                    f"Tool '{tool_call.name}' returned success={result.success}"
                )
                
                # Adjust confidence based on tool success
                if result.success:
                    diagnostics.confidence_score = min(1.0, diagnostics.confidence_score + 0.1)
                else:
                    diagnostics.confidence_score = max(0.0, diagnostics.confidence_score - 0.2)
                
                tool_results.append({
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                    "result": result.content,
                    "success": result.success,
                    "duration_ms": tool_duration_ms,
                })
                
                # Add tool response to conversation
                tool_msg = ChatMessage(
                    role="tool",
                    content=result.content,
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                )
                messages.append(tool_msg)
                
                # Persist tool message to database
                if self._analytics_storage:
                    from analytics.models import ChatMessage as DBChatMessage
                    self._analytics_storage.save_message(
                        DBChatMessage(
                            session_id=conv_id,
                            role="tool",
                            content=result.content,
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                        )
                    )
        else:
            # Max iterations reached - get final response without tool forcing
            diagnostics.thoughts.append(f"Reached max iterations ({max_tool_rounds})")
            response = await self._llm_router.chat(
                messages=messages,
                tools=tools,
                temperature=0.3,
                tool_choice="none",
            )
        
        # Add assistant response to conversation
        messages.append(response.message)
        diagnostics.thoughts.append(
            f"Response generated: {len(response.content) if response.content else 0} chars"
        )
        
        # Persist assistant message to database
        if self._analytics_storage and response.content:
            from analytics.models import ChatMessage as DBChatMessage
            self._analytics_storage.save_message(
                DBChatMessage(
                    session_id=conv_id,
                    role="assistant",
                    content=response.content,
                )
            )
        
        return ChatServiceResponse(
            content=response.content,
            tool_calls=tool_results if tool_results else None,
            session_id=conv_id,
            diagnostics=diagnostics,
        )
    
    async def chat_stream(
        self,
        session_id: str | None,
        user_message: str,
        on_chunk: Callable[[StreamChunk], None],
        max_tool_rounds: int | None = None,
    ) -> None:
        """
        Process a chat message with streaming callbacks.
        
        Instead of returning a final response, this method calls the
        on_chunk callback for each piece of the response as it arrives.
        This enables real-time UI updates.
        
        Args:
            session_id: The conversation session ID
            user_message: The user's input message
            on_chunk: Callback function invoked for each chunk
            max_tool_rounds: Maximum tool execution iterations
        
        Chunk types sent to callback:
            - {"type": "content", "data": {"text": "..."}}
            - {"type": "tool_call", "data": {"name": "...", "arguments": {...}}}
            - {"type": "tool_result", "data": {"tool": "...", "success": bool, "content": "..."}}
            - {"type": "done", "data": {"final": "..."}}
            - {"type": "error", "data": {"message": "..."}}
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # For now, use non-streaming and emit chunks
            # A full streaming implementation would require LLM streaming support
            response = await self.chat(session_id, user_message, max_tool_rounds)
            
            # Emit tool results
            if response.tool_calls:
                for tc in response.tool_calls:
                    on_chunk(StreamChunk(
                        type="tool_call",
                        data={"name": tc["name"], "arguments": tc.get("arguments", {})},
                    ))
                    on_chunk(StreamChunk(
                        type="tool_result",
                        data={
                            "tool": tc["name"],
                            "success": tc.get("success", True),
                            "content": tc.get("result", ""),
                        },
                    ))
            
            # Emit content
            if response.content:
                on_chunk(StreamChunk(
                    type="content",
                    data={"text": response.content},
                ))
            
            # Done
            on_chunk(StreamChunk(
                type="done",
                data={"final": response.content},
            ))
            
        except Exception as e:
            logger.exception(f"Stream error for session {session_id}")
            on_chunk(StreamChunk(
                type="error",
                data={"message": str(e)},
            ))
    
    def list_sessions(self) -> list[dict]:
        """
        Get a summary of all active in-memory sessions.
        
        Note: For persisted sessions, use analytics_storage.get_sessions()
        """
        summaries = []
        for conv_id, messages in self._conversations.items():
            # Get last user message for preview
            last_user_msg = ""
            for msg in reversed(messages):
                if msg.role == "user":
                    last_user_msg = (msg.content or "")[:100]
                    break
            
            summaries.append({
                "id": conv_id,
                "message_count": len(messages),
                "last_message": last_user_msg,
            })
        
        return summaries
    
    def get_session_messages(self, session_id: str) -> list[dict]:
        """
        Get all messages for a specific session.
        
        Args:
            session_id: The session to retrieve
        
        Returns:
            List of message dictionaries with role and content
        """
        messages = self._conversations.get(session_id, [])
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": [
                    {"name": tc.name, "arguments": tc.arguments}
                    for tc in msg.tool_calls
                ] if msg.tool_calls else None,
            }
            for msg in messages
            if msg.role != "system"  # Skip system messages
        ]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory."""
        if session_id in self._conversations:
            del self._conversations[session_id]
            if session_id in self._session_map:
                del self._session_map[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._llm_router:
            await self._llm_router.close()

