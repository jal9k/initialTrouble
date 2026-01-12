"""FastAPI entry point for TechTime API."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import get_settings
from .llm import ChatMessage, LLMRouter
from .tools import ToolRegistry, get_registry
from .tools.api import create_tools_router
from .prompts import AgentType, load_prompt

# Import analytics
from analytics import AnalyticsCollector, AnalyticsStorage
from analytics.api import create_analytics_router, create_feedback_router
from analytics.models import ChatMessage as DBChatMessage


# Request/Response models
class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(description="User's message")
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation ID for context",
    )


class ToolUsedInfo(BaseModel):
    """Information about a tool that was used."""
    
    name: str = Field(description="Tool name")
    success: bool = Field(description="Whether the tool executed successfully")
    duration_ms: int | None = Field(default=None, description="Execution duration in milliseconds")


class ResponseDiagnosticsModel(BaseModel):
    """Diagnostics information about the response."""
    
    confidence_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0"
    )
    thoughts: list[str] = Field(
        default_factory=list,
        description="Reasoning observations during processing"
    )
    tools_used: list[ToolUsedInfo] = Field(
        default_factory=list,
        description="Tools that were executed"
    )


class VerificationResultModel(BaseModel):
    """Result of verification after action tools."""
    
    passed: bool = Field(description="Whether verification passed")
    message: str | None = Field(default=None, description="Verification result message")


class ChatResponseModel(BaseModel):
    """Response from chat endpoint."""

    response: str = Field(description="Assistant's response")
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        description="Tools that were called",
    )
    conversation_id: str = Field(description="Conversation ID")
    session_id: str | None = Field(
        default=None,
        description="Analytics session ID",
    )
    diagnostics: ResponseDiagnosticsModel | None = Field(
        default=None,
        description="Response diagnostics including confidence and reasoning"
    )
    verification: VerificationResultModel | None = Field(
        default=None,
        description="Verification result after action tools"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    llm_backends: dict[str, bool]
    tools_available: int


class SessionListItemResponse(BaseModel):
    """Session list item for frontend sidebar."""
    
    id: str = Field(description="Session ID")
    startTime: str = Field(description="ISO timestamp of session start")
    outcome: str = Field(description="Session outcome: resolved, unresolved, abandoned, in_progress")
    issueCategory: str | None = Field(default=None, description="Issue category")
    preview: str = Field(description="Preview text (first user message)")


class SessionListResponse(BaseModel):
    """Response for session list endpoint."""
    
    items: list[SessionListItemResponse]
    total: int
    page: int
    pageSize: int
    hasMore: bool


# Application state
class AppState:
    """Application state container."""

    def __init__(self):
        self.llm_router: LLMRouter | None = None
        self.tool_registry: ToolRegistry | None = None
        self.conversations: dict[str, list[ChatMessage]] = {}
        self.analytics_storage: AnalyticsStorage | None = None
        self.analytics_collector: AnalyticsCollector | None = None
        # Map conversation_id to analytics session_id
        self.session_map: dict[str, str] = {}


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    
    # Initialize analytics with settings-based path
    db_path = settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    state.analytics_storage = AnalyticsStorage(db_path)
    state.analytics_collector = AnalyticsCollector(storage=state.analytics_storage)
    
    # Initialize LLM router with analytics
    state.llm_router = LLMRouter(settings, analytics_collector=state.analytics_collector)
    state.tool_registry = get_registry()
    
    # Connect analytics to tool registry
    state.tool_registry.set_analytics(state.analytics_collector)

    # Register diagnostic tools
    from .diagnostics import register_all_diagnostics

    register_all_diagnostics(state.tool_registry)
    
    # Register analytics API routes
    app.include_router(create_analytics_router(state.analytics_storage))
    app.include_router(create_feedback_router(state.analytics_storage))
    
    # Register tools API routes
    app.include_router(create_tools_router(state.tool_registry))

    yield

    # Shutdown
    if state.llm_router:
        await state.llm_router.close()


# Create FastAPI app
app = FastAPI(
    title="TechTime API",
    description="AI-powered L1 desktop support API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health and backend availability."""
    llm_status = {}
    if state.llm_router:
        llm_status = await state.llm_router.is_available()

    tools_count = len(state.tool_registry) if state.tool_registry else 0

    return HealthResponse(
        status="healthy",
        llm_backends=llm_status,
        tools_available=tools_count,
    )


@app.get("/api/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = 1,
    page_size: int = 20,
    outcome: str | None = None,
    category: str | None = None,
) -> SessionListResponse:
    """List sessions for the frontend sidebar."""
    if not state.analytics_storage:
        return SessionListResponse(items=[], total=0, page=page, pageSize=page_size, hasMore=False)
    
    # Convert page to offset
    offset = (page - 1) * page_size
    
    # Get sessions from storage
    from analytics.models import SessionOutcome as AnalyticsOutcome, IssueCategory
    outcome_filter = None
    if outcome:
        try:
            outcome_filter = AnalyticsOutcome(outcome)
        except ValueError:
            pass
    
    category_filter = None
    if category:
        try:
            category_filter = IssueCategory(category)
        except ValueError:
            pass
    
    sessions = state.analytics_storage.get_sessions(
        outcome=outcome_filter,
        category=category_filter,
        limit=page_size + 1,  # Get one extra to check if there are more
        offset=offset,
    )
    
    has_more = len(sessions) > page_size
    if has_more:
        sessions = sessions[:page_size]
    
    # Convert to frontend format
    items = []
    for session in sessions:
        items.append(SessionListItemResponse(
            id=session.session_id,
            startTime=session.started_at.isoformat(),
            outcome=session.outcome.value,
            issueCategory=session.issue_category.value if session.issue_category.value != "unknown" else None,
            preview=session.preview or "New conversation...",
        ))
    
    # Get total count
    summary = state.analytics_storage.get_session_summary()
    total = summary.total_sessions
    
    return SessionListResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
        hasMore=has_more,
    )


@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str) -> list[dict[str, Any]]:
    """Get messages for a specific session from the database."""
    if not state.analytics_storage:
        return []
    
    # Read persisted messages from database
    db_messages = state.analytics_storage.get_messages(session_id)
    
    messages = []
    for msg in db_messages:
        if msg.role == "system":
            continue  # Skip system messages
        messages.append({
            "id": msg.message_id,
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        })
    return messages


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, bool]:
    """Delete a session and all related data."""
    if not state.analytics_storage:
        raise HTTPException(status_code=500, detail="Analytics storage not initialized")
    
    # Delete from analytics storage
    deleted = state.analytics_storage.delete_session(session_id)
    
    # Also clean up in-memory conversation data
    if session_id in state.conversations:
        del state.conversations[session_id]
    if session_id in state.session_map:
        del state.session_map[session_id]
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True}


class UpdateSessionRequest(BaseModel):
    """Request model for updating a session."""
    preview: str | None = None
    outcome: str | None = None


class UpdateSessionResponse(BaseModel):
    """Response model for session updates."""
    success: bool
    preview_updated: bool | None = None
    outcome_updated: bool | None = None


@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, request: UpdateSessionRequest) -> UpdateSessionResponse:
    """Update a session's preview or outcome."""
    if not state.analytics_storage:
        raise HTTPException(status_code=500, detail="Analytics storage not initialized")
    
    # Check if session exists first
    session = state.analytics_storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    preview_updated = None
    outcome_updated = None
    
    if request.preview is not None:
        preview_updated = state.analytics_storage.update_session_preview(session_id, request.preview)
    
    if request.outcome is not None:
        from analytics.models import SessionOutcome as AnalyticsOutcome
        try:
            outcome = AnalyticsOutcome(request.outcome)
            outcome_updated = state.analytics_storage.update_session_outcome(session_id, outcome)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid outcome: {request.outcome}")
    
    # Report what was actually updated
    any_updated = (preview_updated is True) or (outcome_updated is True)
    
    return UpdateSessionResponse(
        success=any_updated,
        preview_updated=preview_updated,
        outcome_updated=outcome_updated
    )


@app.post("/chat", response_model=ChatResponseModel)
async def chat(request: ChatRequest) -> ChatResponseModel:
    """Send a message and get AI-powered diagnostics response."""
    import uuid
    import json
    import time

    if not state.llm_router or not state.tool_registry:
        raise RuntimeError("Application not initialized")
    
    if not state.analytics_collector:
        raise RuntimeError("Analytics not initialized")

    # Initialize diagnostics tracking
    diagnostics = ResponseDiagnosticsModel()
    diagnostics.thoughts.append(f"Processing user message: {len(request.message)} chars")

    # Get or create conversation
    conv_id = request.conversation_id or str(uuid.uuid4())
    is_new_conversation = conv_id not in state.conversations
    
    if is_new_conversation:
        # Use diagnostic agent prompt (follows OSI ladder properly)
        system_prompt = load_prompt(AgentType.DIAGNOSTIC)
        state.conversations[conv_id] = [
            ChatMessage(
                role="system",
                content=system_prompt,
            )
        ]
        
        # Start new analytics session
        session = state.analytics_collector.start_session(session_id=conv_id)
        state.session_map[conv_id] = session.session_id
        diagnostics.thoughts.append("Started new conversation")

    # Record user message in analytics
    state.analytics_collector.record_user_message(request.message)

    # Add user message
    user_msg = ChatMessage(role="user", content=request.message)
    state.conversations[conv_id].append(user_msg)
    
    # Persist user message to database
    if state.analytics_storage:
        state.analytics_storage.save_message(
            DBChatMessage(
                session_id=conv_id,
                role="user",
                content=request.message,
            )
        )

    # Get LLM response with tools using multi-turn tool loop
    tools = state.tool_registry.get_all_definitions()
    diagnostics.thoughts.append(f"Available tools: {len(tools)}")
    
    # Multi-turn tool execution loop (like CLI's execute_tool_loop)
    MAX_TOOL_ITERATIONS = 7
    tool_results = []
    
    for iteration in range(MAX_TOOL_ITERATIONS):
        # Force tool call on first iteration, allow auto on subsequent
        tool_choice = "required" if iteration == 0 else "auto"
        diagnostics.thoughts.append(f"Tool loop iteration {iteration + 1}, tool_choice={tool_choice}")
        
        response = await state.llm_router.chat(
            messages=state.conversations[conv_id],
            tools=tools,
            temperature=0.3,
            tool_choice=tool_choice,
        )
        
        # Update session with backend info after first LLM call
        if iteration == 0 and is_new_conversation and state.llm_router.active_backend:
            state.analytics_collector.set_session_backend(
                backend=state.llm_router.active_backend,
                model_name=state.llm_router.active_model or "unknown",
                had_fallback=state.llm_router.had_fallback,
            )
        
        # If no tool calls, we're done with the loop
        if not response.has_tool_calls or not response.message.tool_calls:
            diagnostics.thoughts.append(f"No tool calls in iteration {iteration + 1}, ending loop")
            break
        
        # Add assistant message with tool_calls to conversation
        state.conversations[conv_id].append(response.message)
        diagnostics.thoughts.append(f"LLM requested {len(response.message.tool_calls)} tool call(s)")
        
        # Execute each tool call
        for tool_call in response.message.tool_calls:
            tool_start_time = time.perf_counter()
            result = await state.tool_registry.execute(tool_call)
            tool_duration_ms = int((time.perf_counter() - tool_start_time) * 1000)
            
            # Track tool in diagnostics
            diagnostics.tools_used.append(ToolUsedInfo(
                name=tool_call.name,
                success=result.success,
                duration_ms=tool_duration_ms
            ))
            diagnostics.thoughts.append(f"Tool '{tool_call.name}' returned success={result.success}")
            
            # Adjust confidence based on tool success
            if result.success:
                diagnostics.confidence_score = min(1.0, diagnostics.confidence_score + 0.1)
            else:
                diagnostics.confidence_score = max(0.0, diagnostics.confidence_score - 0.2)
            
            tool_results.append(
                {
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                    "result": result.content,
                    "success": result.success,
                    "duration_ms": tool_duration_ms,
                }
            )

            # Add tool response to conversation
            tool_msg = ChatMessage(
                role="tool",
                content=result.content,
                tool_call_id=tool_call.id,
                name=tool_call.name,
            )
            state.conversations[conv_id].append(tool_msg)
            
            # Persist tool message to database
            if state.analytics_storage:
                state.analytics_storage.save_message(
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
        diagnostics.thoughts.append(f"Reached max iterations ({MAX_TOOL_ITERATIONS})")
        response = await state.llm_router.chat(
            messages=state.conversations[conv_id],
            tools=tools,
            temperature=0.3,
            tool_choice="none",
        )

    # Add assistant response to conversation
    state.conversations[conv_id].append(response.message)
    diagnostics.thoughts.append(f"Response generated: {len(response.content) if response.content else 0} chars")
    
    # Persist assistant message to database
    if state.analytics_storage and response.content:
        state.analytics_storage.save_message(
            DBChatMessage(
                session_id=conv_id,
                role="assistant",
                content=response.content,
            )
        )

    return ChatResponseModel(
        response=response.content,
        tool_calls=tool_results if tool_results else None,
        conversation_id=conv_id,
        session_id=state.session_map.get(conv_id),
        diagnostics=diagnostics,
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    import json
    import time
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            # Create request and get response
            request = ChatRequest(
                message=message,
                conversation_id=data.get("conversation_id"),
            )
            response = await chat(request)

            await websocket.send_json(response.model_dump())

    except WebSocketDisconnect:
        pass




