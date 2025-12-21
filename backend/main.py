"""FastAPI entry point for Network Diagnostics API."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import get_settings
from .llm import ChatMessage, LLMRouter
from .tools import ToolRegistry, get_registry


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


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    state.llm_router = LLMRouter(settings)
    state.tool_registry = get_registry()

    # Register diagnostic tools
    from .diagnostics import register_all_diagnostics

    register_all_diagnostics(state.tool_registry)

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

    # Get or create conversation
    conv_id = request.conversation_id or str(uuid.uuid4())
    if conv_id not in state.conversations:
        state.conversations[conv_id] = [
            ChatMessage(
                role="system",
                content=SYSTEM_PROMPT,
            )
        ]

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


# System prompt for the diagnostic assistant
SYSTEM_PROMPT = """You are a network diagnostics assistant. Your job is to help users troubleshoot network connectivity issues.

You have access to diagnostic tools that can check various aspects of network connectivity:
- check_adapter_status: Check if network adapters are enabled
- get_ip_config: Get IP configuration including DHCP status
- ping_gateway: Test connectivity to the default gateway
- ping_dns: Test connectivity to external DNS servers
- test_dns_resolution: Test DNS name resolution

When a user describes a network problem:
1. Start with the most likely issue based on their description
2. Use the diagnostic tools to gather information
3. Interpret the results and explain what they mean
4. Suggest specific fixes based on findings
5. If needed, run additional diagnostics to narrow down the issue

Follow the OSI model diagnostic ladder when systematic troubleshooting is needed:
1. Physical/Link layer (adapter status)
2. Network layer local (IP config)
3. Network layer gateway (ping gateway)
4. Network layer external (ping DNS servers)
5. Application layer (DNS resolution)

Be concise but thorough. Explain technical concepts in simple terms when possible."""


