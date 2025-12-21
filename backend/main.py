"""FastAPI entry point for Network Diagnostics API."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import get_settings
from .llm import ChatMessage, LLMRouter
from .tools import ToolRegistry, get_registry
from .prompts import AgentType, load_prompt

# Import analytics
from analytics import AnalyticsCollector, AnalyticsStorage
from analytics.api import create_analytics_router, create_feedback_router


# Request/Response models
class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(description="User's message")
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation ID for context",
    )


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


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    llm_backends: dict[str, bool]
    tools_available: int


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
    
    # Initialize analytics
    db_path = Path("data/analytics.db")
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

    yield

    # Shutdown
    if state.llm_router:
        await state.llm_router.close()


# Create FastAPI app
app = FastAPI(
    title="Network Diagnostics API",
    description="AI-powered network troubleshooting API",
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


@app.post("/chat", response_model=ChatResponseModel)
async def chat(request: ChatRequest) -> ChatResponseModel:
    """Send a message and get AI-powered diagnostics response."""
    import uuid

    if not state.llm_router or not state.tool_registry:
        raise RuntimeError("Application not initialized")
    
    if not state.analytics_collector:
        raise RuntimeError("Analytics not initialized")

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

    # Record user message in analytics
    state.analytics_collector.record_user_message(request.message)

    # Add user message
    state.conversations[conv_id].append(
        ChatMessage(role="user", content=request.message)
    )

    # Get LLM response with tools
    tools = state.tool_registry.get_all_definitions()
    response = await state.llm_router.chat(
        messages=state.conversations[conv_id],
        tools=tools,
        temperature=0.3,
    )
    
    # Update session with backend info after first LLM call
    if is_new_conversation and state.llm_router.active_backend:
        state.analytics_collector.set_session_backend(
            backend=state.llm_router.active_backend,
            model_name=state.llm_router.active_model or "unknown",
            had_fallback=state.llm_router.had_fallback,
        )

    # Handle tool calls
    tool_results = []
    if response.has_tool_calls and response.message.tool_calls:
        # Add assistant message with tool_calls to conversation first
        state.conversations[conv_id].append(response.message)
        
        for tool_call in response.message.tool_calls:
            result = await state.tool_registry.execute(tool_call)
            tool_results.append(
                {
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                    "result": result.content,
                }
            )

            # Add tool response to conversation
            state.conversations[conv_id].append(
                ChatMessage(
                    role="tool",
                    content=result.content,
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                )
            )

        # Get final response after tool calls
        response = await state.llm_router.chat(
            messages=state.conversations[conv_id],
            tools=tools,
            temperature=0.3,
        )

    # Add assistant response to conversation
    state.conversations[conv_id].append(response.message)

    return ChatResponseModel(
        response=response.content,
        tool_calls=tool_results if tool_results else None,
        conversation_id=conv_id,
        session_id=state.session_map.get(conv_id),
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
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




