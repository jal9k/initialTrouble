"""
Core chat service for TechTim(e).

This module contains the ChatService class which orchestrates conversations
with the LLM. It is designed to be called either from:
- FastAPI routes (HTTP/WebSocket mode)
- PyWebView API bridge (desktop mode)

The service is stateful and maintains conversation history per session.

NOTE: Tool execution is now handled automatically by GlueLLM via the
GlueLLMWrapper class. This service focuses on session management,
analytics persistence, and response formatting.
"""
import uuid
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Any
from datetime import datetime

from .config import get_settings
from .llm import ChatMessage, GlueLLMWrapper
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
    Orchestrates chat interactions with LLM via GlueLLM.
    
    This service manages:
    1. Session/conversation state
    2. Analytics persistence
    3. Response formatting
    
    Tool execution is handled automatically by GlueLLM through the
    GlueLLMWrapper class.
    
    Example:
        service = ChatService()
        await service.initialize()
        response = await service.chat("session-123", "My WiFi isn't working")
        print(response.content)
    """
    
    def __init__(
        self,
        gluellm_wrapper: GlueLLMWrapper | None = None,
        tool_registry: ToolRegistry | None = None,
        analytics_collector: "AnalyticsCollector | None" = None,
        analytics_storage: "AnalyticsStorage | None" = None,
    ):
        """
        Initialize the chat service.
        
        Args:
            gluellm_wrapper: GlueLLM wrapper. If None, creates on initialize().
            tool_registry: Tool registry. If None, uses the global registry.
            analytics_collector: Analytics collector for tracking.
            analytics_storage: Analytics storage for persistence.
        """
        self._settings = get_settings()
        self._gluellm_wrapper = gluellm_wrapper
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
        
        This sets up the GlueLLM wrapper, tool registry, and analytics.
        """
        if self._initialized:
            return
        
        # Initialize tool registry first (GlueLLM wrapper needs it)
        if self._tool_registry is None:
            self._tool_registry = get_registry()
        
        # Register diagnostic tools
        from .diagnostics import register_all_diagnostics
        register_all_diagnostics(self._tool_registry)
        
        # Initialize GlueLLM wrapper with tool registry and analytics
        if self._gluellm_wrapper is None:
            self._gluellm_wrapper = GlueLLMWrapper(
                settings=self._settings,
                tool_registry=self._tool_registry,
                analytics_collector=self._analytics_collector,
            )
        
        self._initialized = True
        logger.info(
            f"ChatService initialized with {len(self._tool_registry)} tools (GlueLLM)"
        )
    
    def set_analytics(
        self,
        collector: "AnalyticsCollector",
        storage: "AnalyticsStorage",
    ) -> None:
        """Set analytics collector and storage after initialization."""
        self._analytics_collector = collector
        self._analytics_storage = storage
        
        if self._gluellm_wrapper:
            self._gluellm_wrapper.set_analytics(collector)
    
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
        
        Tool execution is handled automatically by GlueLLM through the
        GlueLLMWrapper. This method manages session state and analytics.
        
        Args:
            session_id: The conversation session ID (creates new if None)
            user_message: The user's input message
            max_tool_rounds: Maximum tool execution iterations (unused, kept for API compat)
        
        Returns:
            ChatServiceResponse with the assistant's reply and any tool results
        """
        if not self._initialized:
            await self.initialize()
        
        conv_id, messages, is_new = self._get_or_create_conversation(session_id)
        
        # Record user message in analytics
        if self._analytics_collector:
            self._analytics_collector.record_user_message(user_message)
        
        # Add user message to conversation history
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
        
        # Get system prompt
        system_prompt = load_prompt(AgentType.DIAGNOSTIC)
        
        # Convert messages to dict format for GlueLLM
        messages_for_llm = [
            {"role": msg.role, "content": msg.content or ""}
            for msg in messages
            if msg.role != "system"  # System prompt passed separately
        ]
        
        # Call GlueLLM wrapper (handles tool loop internally)
        response = await self._gluellm_wrapper.chat(
            messages=messages_for_llm,
            system_prompt=system_prompt,
        )
        
        # Update session backend info
        if is_new and self._analytics_collector:
            self._analytics_collector.set_session_backend(
                backend=self._gluellm_wrapper.active_provider or "unknown",
                model_name=self._gluellm_wrapper.active_model or "unknown",
                had_fallback=self._gluellm_wrapper.had_fallback,
            )
        
        # Add assistant response to conversation history
        if response.content:
            assistant_msg = ChatMessage(role="assistant", content=response.content)
            messages.append(assistant_msg)
        
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
        
        # Persist tool messages to database
        if self._analytics_storage and response.tool_calls:
            from analytics.models import ChatMessage as DBChatMessage
            for tc in response.tool_calls:
                self._analytics_storage.save_message(
                    DBChatMessage(
                        session_id=conv_id,
                        role="tool",
                        content=tc.get("result", ""),
                        name=tc.get("name"),
                    )
                )
        
        # Update response with session ID
        response.session_id = conv_id
        
        # Add processing info to diagnostics
        if response.diagnostics:
            response.diagnostics.thoughts.insert(
                0, f"Processing user message: {len(user_message)} chars"
            )
            response.diagnostics.thoughts.append(
                f"Response generated: {len(response.content)} chars"
            )
        
        return response
    
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
        # GlueLLM wrapper doesn't need explicit cleanup
        pass

