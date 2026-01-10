# Phase 1: Backend Modifications (UPDATED)

## CHANGES FROM ORIGINAL

This document has been updated to preserve existing complex patterns in the TechTim(e) codebase.

| Task | Original Approach | Updated Approach | Reason |
|------|-------------------|------------------|--------|
| 1.1 Config | Replace entire file with global `settings` | Add bundled mode to existing, keep `get_settings()` | Preserve `@lru_cache` pattern, existing settings |
| 1.2 Prompts | Replace with simple `load_prompt()` | Minimal changes, preserve `AgentType` enum | Keep `get_prompt_for_context()`, 10 agent types |
| 1.3 ChatService | Create from scratch | Extract from existing `main.py` | Preserve analytics integration, tool_choice patterns |
| 1.4 Analytics Path | Update `backend/analytics/storage.py` | Update `main.py` line 143 | Analytics is at `analytics/` (top-level module) |
| 1.5 Logging | Replace with simple setup | Add to existing, preserve `ResponseDiagnostics` | Keep `debug_log()` function |
| 1.6 Imports | Generic check | Specific files identified | More precise guidance |

---

## Objective

Prepare the existing Python backend for bundled desktop deployment by updating configuration management, extracting the chat orchestration logic into a reusable service, and ensuring all file paths work correctly when running inside a PyInstaller bundle.

## Prerequisites

Before starting this phase, ensure you have:
- The existing TechTim(e) backend codebase in `backend/`
- Python 3.11+ installed
- All existing backend tests passing

---

## Task 1.1: Update Configuration for Bundled Mode

### Purpose

When PyInstaller bundles the application, it extracts files to a temporary directory stored in `sys._MEIPASS`. The configuration system needs to detect this and adjust paths accordingly. User data (database, logs, downloaded models) must persist in a platform-appropriate location outside the bundle.

### File: `backend/config.py`

**IMPORTANT:** This is an ADDITIVE update. Preserve existing patterns.

Update the existing configuration by adding bundled mode functions and path properties. Keep:
- `SettingsConfigDict` pattern
- `get_settings()` with `@lru_cache`
- Existing settings like `command_timeout`, `dns_servers`

```python
"""Configuration management for TechTime.

This module handles settings and path resolution for both development
and bundled (PyInstaller) deployment modes. Key concepts:

- Base path: Where application code and bundled resources live.
  In development, this is the project root. When bundled, PyInstaller
  extracts files to a temp directory (sys._MEIPASS).

- User data path: Where user-specific data is stored (database, logs,
  downloaded models). This persists across app restarts and is located
  in the platform's standard application data directory.
"""

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# Bundled Mode Detection Functions
# =============================================================================

def is_bundled() -> bool:
    """
    Check if running inside a PyInstaller bundle.
    
    PyInstaller sets sys.frozen to True and adds sys._MEIPASS
    pointing to the temp extraction directory.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_base_path() -> Path:
    """
    Get the base path for application resources.
    
    When bundled, PyInstaller extracts files to sys._MEIPASS.
    When running from source, use the directory containing this file's parent.
    
    Returns:
        Path to the application base directory
    """
    if is_bundled():
        # PyInstaller extracts to a temp directory
        return Path(sys._MEIPASS)
    # Development: backend/ is inside project root
    return Path(__file__).parent.parent


def get_user_data_path() -> Path:
    """
    Get the path for persistent user data.
    
    This directory stores:
    - SQLite database (analytics.db)
    - Log files
    - Downloaded Ollama models
    
    The location follows platform conventions:
    - macOS: ~/Library/Application Support/TechTime/
    - Windows: %APPDATA%/TechTime/
    - Linux: ~/.local/share/TechTime/
    
    Returns:
        Path to user data directory (created if it doesn't exist)
    """
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    elif sys.platform == 'win32':
        # Use APPDATA if available, fall back to home directory
        appdata = os.environ.get('APPDATA')
        base = Path(appdata) if appdata else Path.home() / 'AppData' / 'Roaming'
    else:
        # Linux and other Unix-like systems
        xdg_data = os.environ.get('XDG_DATA_HOME')
        base = Path(xdg_data) if xdg_data else Path.home() / '.local' / 'share'
    
    path = base / 'TechTime'
    path.mkdir(parents=True, exist_ok=True)
    return path


# =============================================================================
# Settings Class
# =============================================================================

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================================================================
    # LLM Configuration (EXISTING)
    # =========================================================================
    
    llm_backend: Literal["ollama", "openai"] = "ollama"
    
    # Ollama Configuration
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "ministral-3:3b"
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # =========================================================================
    # Server Configuration (EXISTING)
    # =========================================================================
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # =========================================================================
    # Diagnostic Configuration (EXISTING)
    # =========================================================================
    
    command_timeout: int = 10
    dns_servers: str = "8.8.8.8,1.1.1.1"
    dns_test_hosts: str = "google.com,cloudflare.com"
    
    # =========================================================================
    # NEW: Desktop/Bundled Mode Configuration
    # =========================================================================
    
    max_tool_rounds: int = Field(
        default=10,
        description="Maximum number of tool execution rounds per chat turn"
    )

    # =========================================================================
    # EXISTING: Property Methods
    # =========================================================================
    
    @property
    def dns_server_list(self) -> list[str]:
        """Parse DNS servers string into list."""
        return [s.strip() for s in self.dns_servers.split(",")]

    @property
    def dns_test_host_list(self) -> list[str]:
        """Parse DNS test hosts string into list."""
        return [h.strip() for h in self.dns_test_hosts.split(",")]

    # =========================================================================
    # NEW: Bundled Mode Properties
    # =========================================================================
    
    @property
    def bundled_mode(self) -> bool:
        """True when running inside PyInstaller bundle."""
        return is_bundled()
    
    @property
    def base_path(self) -> Path:
        """Base path for application resources."""
        return get_base_path()
    
    @property
    def user_data_path(self) -> Path:
        """Path for persistent user data."""
        return get_user_data_path()
    
    @property
    def database_path(self) -> Path:
        """Path to the SQLite analytics database."""
        if self.bundled_mode:
            return self.user_data_path / "analytics.db"
        # Development mode: use existing data/ directory
        path = Path(__file__).parent.parent / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path / "analytics.db"
    
    @property
    def log_path(self) -> Path:
        """Directory for log files."""
        if self.bundled_mode:
            path = self.user_data_path / "logs"
        else:
            path = Path(__file__).parent.parent / "data" / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def models_path(self) -> Path:
        """Directory where Ollama stores downloaded models."""
        path = self.user_data_path / "models"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def prompts_path(self) -> Path:
        """Directory containing agent prompt templates."""
        if self.bundled_mode:
            return self.base_path / "prompts"
        return Path(__file__).parent.parent / "prompts"


# =============================================================================
# Global Settings Accessor (PRESERVED PATTERN)
# =============================================================================

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### Verification Steps

After implementing this file, create a simple test script to verify path resolution:

```python
# test_config.py (temporary, delete after verification)
from backend.config import get_settings, is_bundled

settings = get_settings()

print(f"Bundled mode: {is_bundled()}")
print(f"Base path: {settings.base_path}")
print(f"User data path: {settings.user_data_path}")
print(f"Database path: {settings.database_path}")
print(f"Log path: {settings.log_path}")
print(f"Prompts path: {settings.prompts_path}")
print(f"LLM backend: {settings.llm_backend}")
print(f"Ollama model: {settings.ollama_model}")
print(f"Command timeout: {settings.command_timeout}")  # Verify existing settings preserved
```

Run from project root with `python test_config.py`. Expected output should show `Bundled mode: False` and valid paths.

---

## Task 1.2: Update Prompt Loading

### Purpose

The `prompts.py` module loads text files containing agent prompts. It must use the new settings paths to find prompts whether running in development or bundled mode.

### File: `backend/prompts.py`

**IMPORTANT:** This is a MINIMAL update. Preserve the existing `AgentType` enum and all functions.

Only update the `PROMPTS_DIR` definition to use settings with a fallback:

```python
"""Prompt loading and management for different agent types."""

from enum import Enum
from pathlib import Path
from functools import lru_cache


class AgentType(Enum):
    """Available agent types with specialized prompts."""
    
    # Original agent types
    DEFAULT = "default"      # General-purpose diagnostician
    TRIAGE = "triage"        # Quick issue categorization
    DIAGNOSTIC = "diagnostic"  # Systematic OSI-layer troubleshooting
    REMEDIATION = "remediation"  # Fix suggestions
    QUICK_CHECK = "quick_check"  # Fast health check
    
    # Multi-OS agent types
    MANAGER = "manager"      # Triage coordinator for OS routing
    MACOS = "macos"          # macOS specialist
    WINDOWS = "windows"      # Windows specialist
    LINUX = "linux"          # Linux specialist


def _get_prompts_dir() -> Path:
    """
    Get the prompts directory, supporting both development and bundled modes.
    
    Returns:
        Path to the prompts directory
    """
    # Try using settings first (handles bundled mode)
    try:
        from .config import get_settings
        settings = get_settings()
        if settings.prompts_path.exists():
            return settings.prompts_path
    except Exception:
        pass
    
    # Fallback to relative path (development)
    return Path(__file__).parent.parent / "prompts"


# Prompt directory - computed at module load
PROMPTS_DIR = _get_prompts_dir()


@lru_cache(maxsize=10)
def load_prompt(agent_type: AgentType | str) -> str:
    """
    Load a system prompt for the specified agent type.
    
    Args:
        agent_type: AgentType enum or string name
        
    Returns:
        System prompt content as string
        
    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    if isinstance(agent_type, str):
        agent_type = AgentType(agent_type)
    
    prompt_file = PROMPTS_DIR / f"{agent_type.value}_agent.md"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_file}")
    
    return prompt_file.read_text()


def get_prompt_for_context(user_message: str) -> tuple[AgentType, str]:
    """
    Automatically select the best prompt based on user message.
    
    Args:
        user_message: The user's input message
        
    Returns:
        Tuple of (AgentType, prompt_content)
    """
    message_lower = user_message.lower()
    
    # Quick check keywords
    if any(kw in message_lower for kw in ["quick check", "health check", "is it working", "status"]):
        return AgentType.QUICK_CHECK, load_prompt(AgentType.QUICK_CHECK)
    
    # Fix/remediation keywords  
    if any(kw in message_lower for kw in ["how to fix", "how do i fix", "fix it", "solve", "repair"]):
        return AgentType.REMEDIATION, load_prompt(AgentType.REMEDIATION)
    
    # Default to diagnostic agent for troubleshooting
    return AgentType.DIAGNOSTIC, load_prompt(AgentType.DIAGNOSTIC)


def list_available_prompts() -> list[dict]:
    """List all available prompt files with metadata."""
    prompts = []
    
    for agent_type in AgentType:
        prompt_file = PROMPTS_DIR / f"{agent_type.value}_agent.md"
        prompts.append({
            "agent_type": agent_type.value,
            "file": str(prompt_file),
            "exists": prompt_file.exists(),
            "size": prompt_file.stat().st_size if prompt_file.exists() else 0,
        })
    
    return prompts


def clear_prompt_cache() -> None:
    """
    Clear the prompt cache.
    
    Call this if prompts are modified during runtime (development only).
    """
    load_prompt.cache_clear()
```

### Verification Steps

1. Ensure your `prompts/` directory exists with agent prompt files
2. Test the loading:

```python
from backend.prompts import load_prompt, AgentType, get_prompt_for_context, list_available_prompts

# Test direct loading
print(load_prompt(AgentType.DIAGNOSTIC)[:200])

# Test context-aware selection
agent_type, prompt = get_prompt_for_context("quick check my network")
print(f"Selected: {agent_type.value}")

# List all prompts
for p in list_available_prompts():
    print(f"{p['agent_type']}: exists={p['exists']}")
```

---

## Task 1.3: Create the Chat Service

### Purpose

Extract the chat orchestration logic from FastAPI routes into a standalone service class. This service will be called directly by PyWebView's API bridge, eliminating the need for HTTP in desktop mode while keeping the logic testable and reusable.

### File: `backend/chat_service.py` (NEW FILE)

**IMPORTANT:** This extracts and adapts the existing logic from `main.py` lines 425-564. Preserve:
- `tool_choice="required"` on first iteration pattern
- Analytics integration with `AnalyticsCollector` and `AnalyticsStorage`
- Confidence scoring and diagnostics tracking
- Debug logging patterns

```python
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
from typing import TYPE_CHECKING, Callable, Optional, Any
from datetime import datetime

from .config import get_settings
from .llm import LLMRouter, ChatMessage
from .llm.base import ChatResponse as LLMChatResponse
from .tools import ToolRegistry, get_registry
from .tools.schemas import ToolCall, ToolResult
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
```

### Verification Steps

1. Ensure your `backend/llm/__init__.py` exports `LLMRouter` and `ChatMessage`
2. Ensure your `backend/tools/__init__.py` exports `ToolRegistry` and `get_registry`
3. Create a test script:

```python
# test_chat_service.py
import asyncio
from backend.chat_service import ChatService

async def test():
    service = ChatService()
    await service.initialize()
    
    # Test session listing
    sessions = service.list_sessions()
    print(f"Sessions: {sessions}")
    
    # Test a simple chat (requires Ollama running)
    # response = await service.chat(None, "Check if my network adapter is working")
    # print(f"Response: {response.content[:200]}...")

asyncio.run(test())
```

---

## Task 1.4: Update Analytics Storage Path

### Purpose

The analytics module stores data in SQLite. Update `main.py` to use the new settings paths.

### File: `backend/main.py`

**IMPORTANT:** The analytics module is at `analytics/` (top-level, not `backend/analytics/`).

Find line 143 (approximately) in `main.py`:

```python
# OLD - hardcoded path
db_path = Path("data/analytics.db")
```

Replace with:

```python
# NEW - use settings
from .config import get_settings

settings = get_settings()
db_path = settings.database_path
```

The full updated section in the lifespan manager:

```python
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
    
    # ... rest of initialization
```

---

## Task 1.5: Update Logging Configuration

### Purpose

Ensure logs are written to the user data directory in bundled mode.

### File: `backend/logging_config.py`

**IMPORTANT:** Preserve the existing `ResponseDiagnostics` class and `debug_log()` function.

Update only the `setup_logging()` function to use settings:

```python
"""Logging configuration for TechTime."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_dir: Path | None = None,
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to also log to a file
        log_dir: Directory for log files (default: from settings)

    Returns:
        Configured root logger
    """
    # Create logger
    logger = logging.getLogger("techtime")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stderr to not interfere with Rich output)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)  # Only warnings+ to console
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        # Use provided log_dir, or get from settings, or fallback
        if log_dir is None:
            try:
                from .config import get_settings
                log_dir = get_settings().log_path
            except Exception:
                log_dir = Path("data/logs")
        
        log_dir.mkdir(parents=True, exist_ok=True)

        # Daily log file
        log_file = log_dir / f"techtime_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # All levels to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to file: {log_file}")

    return logger


def get_logger(name: str = "techtime") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


# =============================================================================
# Debug Logging (PRESERVED)
# =============================================================================

def debug_log(prefix: str, message: str, data: Any = None) -> None:
    """Structured debug logging with timestamp and prefix.
    
    Usage:
        debug_log("AgentExecutor", "Processing user query", {"query": user_input})
        debug_log("ToolRegistry", "Executing tool", {"name": tool_name})
    
    To remove all debug logging, search for '#region debug' and delete to '#endregion'.
    """
    logger = get_logger("techtime.debug")
    ts = datetime.now().strftime("%H:%M:%S")
    
    if data is not None:
        data_str = json.dumps(data, default=str)
        if len(data_str) > 300:
            data_str = data_str[:300] + "..."
        logger.info(f"[{ts}] [{prefix}] {message}: {data_str}")
    else:
        logger.info(f"[{ts}] [{prefix}] {message}")


def format_tool_output(tool_name: str, result: dict) -> str:
    """Format tool output for display panel."""
    return f"• {tool_name} Output:\n\n```json\n{json.dumps(result, indent=2)}\n```"


# =============================================================================
# Response Diagnostics (PRESERVED)
# =============================================================================

class ResponseDiagnostics:
    """Tracks response quality metrics for debug display.
    
    Collects confidence scores, thoughts, and tool results during
    a chat turn for display in a Response Diagnostics panel.
    """
    
    def __init__(self):
        self.confidence_score: float = 0.5
        self.thoughts: list[str] = []
        self.tools_used: list[dict] = []
    
    def add_thought(self, thought: str) -> None:
        """Add a reasoning observation."""
        self.thoughts.append(thought)
    
    def add_tool_result(self, name: str, result: dict) -> None:
        """Record tool execution result and adjust confidence."""
        self.tools_used.append({"name": name, "result": result})
        # Adjust confidence based on tool success
        if result.get("success", True):
            self.confidence_score = min(1.0, self.confidence_score + 0.1)
        else:
            self.confidence_score = max(0.0, self.confidence_score - 0.2)
    
    def set_confidence(self, score: float) -> None:
        """Manually set confidence score."""
        self.confidence_score = max(0.0, min(1.0, score))
    
    def to_panel_content(self) -> str:
        """Format diagnostics for Rich Panel display."""
        lines = [
            f"Confidence Score: {self.confidence_score:.2f}",
            "",
            "Thoughts:",
        ]
        for thought in self.thoughts:
            lines.append(f" • {thought}")
        
        if self.tools_used:
            lines.extend(["", "Tools Used:"])
            for tool in self.tools_used:
                result_preview = str(tool.get("result", {}))[:50]
                lines.append(f" • {tool['name']}: {result_preview}")
        
        return "\n".join(lines)
```

---

## Task 1.6: Verify Imports Throughout Backend

### Purpose

Ensure all modules that need the updated config are importing it correctly.

### Files to Check

The following files use config and may need verification:

| File | Current Import | Action |
|------|---------------|--------|
| `backend/llm/router.py` | `from ..config import Settings, get_settings` | ✅ Already correct |
| `backend/main.py` | `from .config import get_settings` | ✅ Already correct |
| `backend/diagnostics/platform.py` | May use settings | Check for hardcoded paths |
| `backend/cli.py` | Uses settings | Verify import pattern |

Run this command to verify imports:

```bash
# Run this in your terminal to find files that might need updates
grep -r "from .config import" backend/
grep -r "from backend.config import" backend/
grep -r "import config" backend/
grep -r "Path(\"data" backend/
```

All files should import using one of these patterns:

```python
# Within backend package:
from .config import get_settings
settings = get_settings()

# From outside backend:
from backend.config import get_settings
settings = get_settings()
```

---

## Acceptance Criteria

Phase 1 is complete when:

1. **Configuration works in both modes**: Running `python -c "from backend.config import get_settings; print(get_settings().bundled_mode)"` returns `False` in development and would return `True` in a PyInstaller bundle.

2. **Paths resolve correctly**: All path properties (`database_path`, `log_path`, `models_path`, `prompts_path`) return valid paths that exist or can be created.

3. **ChatService functions independently**: The `ChatService` class can be instantiated and used without FastAPI:
   ```python
   import asyncio
   from backend.chat_service import ChatService
   
   async def test():
       service = ChatService()
       await service.initialize()
       sessions = service.list_sessions()  # Should return []
   
   asyncio.run(test())
   ```

4. **Prompts load correctly**: `from backend.prompts import load_prompt, AgentType; print(load_prompt(AgentType.DIAGNOSTIC)[:100])` succeeds.

5. **Existing patterns preserved**: `AgentType` enum, `get_prompt_for_context()`, `ResponseDiagnostics`, and `debug_log()` still work.

6. **No hardcoded paths remain**: Search the codebase for hardcoded paths like `"data/analytics.db"` or `Path("data/logs")` that should use settings instead.

7. **Existing tests still pass**: If you have existing tests, they should continue to work.

---

## Files Modified/Created Summary

| File | Action | Description |
|------|--------|-------------|
| `backend/config.py` | Modified | Added bundled mode detection and path properties (preserving existing) |
| `backend/prompts.py` | Modified | Updated PROMPTS_DIR to use settings (preserving AgentType, all functions) |
| `backend/chat_service.py` | Created | Extracted chat logic from main.py with analytics integration |
| `backend/main.py` | Modified | Updated database path to use settings |
| `backend/logging_config.py` | Modified | Updated log path (preserving ResponseDiagnostics, debug_log) |

---

## Next Phase

After completing Phase 1, proceed to **Phase 2: Desktop Application Layer**, which creates the Ollama sidecar manager and PyWebView API bridge.

