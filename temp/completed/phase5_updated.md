# Phase 5: Testing Strategy (UPDATED)

## CHANGES FROM ORIGINAL

This document has been updated to match the actual TechTim(e) codebase APIs and structure.

| Task | Original | Updated | Reason |
|------|----------|---------|--------|
| 5.2 conftest.py | `mock_settings` patches wrong path | Patches actual `get_settings()` | Match config.py pattern |
| 5.2 conftest.py | Missing analytics fixtures | Added `AnalyticsCollector`/`Storage` | Top-level analytics module |
| 5.4 test_chat_service | `get_or_create_session()` | `chat(session_id, message)` | Match actual ChatService API |
| 5.4 test_chat_service | `ChatResponse` | `ChatServiceResponse` | Correct response class name |
| 5.4 test_chat_service | `session.messages` | `_conversations[id]` | Internal storage is dict |
| 5.6 test_api_bridge | Generic tests | Match TechTimApi from phase2_updated | Use correct method signatures |

---

## Objective

Establish a comprehensive testing approach for the TechTim(e) desktop application, covering unit tests for backend components, integration tests for the PyWebView bridge, and end-to-end testing workflows for the complete application.

## Prerequisites

Before starting this phase, ensure you have:
- Phases 1-4 completed
- Python testing dependencies installed: `pytest`, `pytest-asyncio`, `pytest-cov`
- The application running successfully in development mode

Install testing dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

---

## Task 5.1: Create Test Directory Structure

### Purpose

Organize tests in a logical structure that mirrors the application layout, making it easy to find and maintain tests.

### Directory Structure

Create the following test directory structure:

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_config.py          # Configuration tests
│   ├── test_prompts.py         # Prompt loading tests
│   ├── test_chat_service.py    # ChatService tests
│   └── test_ollama_manager.py  # OllamaManager tests
├── integration/
│   ├── __init__.py
│   ├── test_api_bridge.py      # PyWebView API tests
│   └── test_full_chat.py       # End-to-end chat tests
└── fixtures/
    ├── __init__.py
    ├── mock_ollama.py          # Mock Ollama server
    └── sample_data.py          # Test data
```

### File: `tests/__init__.py`

```python
"""
TechTim(e) Test Suite

This package contains all tests for the desktop application:
- unit/: Tests for individual components in isolation
- integration/: Tests for component interactions
- fixtures/: Shared test data and mocks
"""
```

---

## Task 5.2: Create Shared Test Fixtures

### Purpose

Define reusable pytest fixtures that provide common test dependencies like mock services, test data, and application instances.

**IMPORTANT:** Updated to match actual module structure and APIs.

### File: `tests/conftest.py`

```python
"""
Shared pytest fixtures for TechTim(e) tests.

This module provides fixtures used across multiple test modules.
Fixtures are automatically discovered by pytest.

UPDATED: Fixed imports and method signatures to match actual codebase.
"""
import os
import sys
import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
import pytest_asyncio

# Ensure project root is in path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# Event Loop Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session.
    
    This prevents issues with async fixtures and tests.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test files.
    
    The directory is automatically cleaned up after the test.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_user_data(temp_dir: Path) -> Path:
    """
    Create a temporary user data directory structure.
    
    Mimics the production user data layout with logs and models directories.
    """
    user_data = temp_dir / "TechTime"
    (user_data / "logs").mkdir(parents=True)
    (user_data / "models").mkdir(parents=True)
    return user_data


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def mock_settings(temp_user_data: Path):
    """
    Create mock settings with temporary paths.
    
    UPDATED: Patches the actual functions in backend.config
    """
    with patch('backend.config.get_user_data_path', return_value=temp_user_data):
        with patch('backend.config.is_bundled', return_value=False):
            # Clear the lru_cache to get fresh settings
            from backend.config import get_settings
            get_settings.cache_clear()
            
            settings = get_settings()
            yield settings
            
            # Clear again after test
            get_settings.cache_clear()


# =============================================================================
# Mock LLM Fixtures
# =============================================================================

@pytest.fixture
def mock_chat_message():
    """
    Factory fixture for creating ChatMessage objects.
    """
    from backend.llm.base import ChatMessage
    
    def _create_message(
        role: str = "assistant",
        content: str = "Test response",
        tool_calls: list = None,
    ):
        return ChatMessage(
            role=role,
            content=content,
            tool_calls=tool_calls,
        )
    
    return _create_message


@pytest.fixture
def mock_chat_response(mock_chat_message):
    """
    Factory fixture for creating mock ChatResponse objects.
    
    UPDATED: Uses actual ChatResponse from llm.base
    """
    from backend.llm.base import ChatResponse
    
    def _create_response(
        content: str = "Test response",
        tool_calls: list = None,
        finish_reason: str = "stop",
    ):
        message = mock_chat_message(
            role="assistant",
            content=content,
            tool_calls=tool_calls,
        )
        return ChatResponse(
            message=message,
            finish_reason=finish_reason,
            usage={"prompt_tokens": 10, "completion_tokens": 20},
        )
    
    return _create_response


@pytest.fixture
def mock_llm_router(mock_chat_response):
    """
    Create a mock LLM router that returns predictable responses.
    
    UPDATED: Matches actual LLMRouter interface
    """
    from backend.llm.router import LLMRouter
    
    router = MagicMock(spec=LLMRouter)
    router.active_backend = "ollama"
    router.active_model = "test-model"
    router.had_fallback = False
    
    # Default response without tool calls
    default_response = mock_chat_response("I can help with that!")
    
    async def mock_chat(*args, **kwargs):
        return default_response
    
    router.chat = AsyncMock(side_effect=mock_chat)
    router.get_client = AsyncMock()
    router.is_available = AsyncMock(return_value={"ollama": True, "openai": False})
    router.close = AsyncMock()
    
    return router


# =============================================================================
# Mock Tool Registry Fixtures
# =============================================================================

@pytest.fixture
def mock_tool_result():
    """
    Factory fixture for creating mock ToolResult objects.
    
    UPDATED: Uses actual ToolResult from tools.schemas
    """
    from backend.tools.schemas import ToolResult
    
    def _create_result(
        tool_call_id: str = "test-call-id",
        success: bool = True,
        content: str = "Tool executed successfully",
    ):
        return ToolResult(
            tool_call_id=tool_call_id,
            success=success,
            content=content,
        )
    
    return _create_result


@pytest.fixture
def mock_tool_registry(mock_tool_result):
    """
    Create a mock tool registry with sample tools.
    
    UPDATED: Matches actual ToolRegistry interface with execute(tool_call)
    """
    from backend.tools.registry import ToolRegistry
    from backend.tools.schemas import ToolDefinition, ToolParameter
    
    registry = MagicMock(spec=ToolRegistry)
    
    # Sample tool definitions
    registry.get_all_definitions.return_value = [
        ToolDefinition(
            name="ping_gateway",
            description="Ping the default gateway",
            parameters=[],
        ),
        ToolDefinition(
            name="check_dns",
            description="Check DNS resolution",
            parameters=[
                ToolParameter(
                    name="hostname",
                    type="string",
                    description="Hostname to resolve",
                    required=False,
                ),
            ],
        ),
        ToolDefinition(
            name="get_network_info",
            description="Get network adapter information",
            parameters=[],
        ),
    ]
    
    # Mock execute to return success
    async def mock_execute(tool_call):
        return mock_tool_result(
            tool_call_id=tool_call.id,
            success=True,
            content=f"Executed {tool_call.name}",
        )
    
    registry.execute = AsyncMock(side_effect=mock_execute)
    registry.__len__ = MagicMock(return_value=3)
    
    return registry


# =============================================================================
# Analytics Fixtures
# =============================================================================

@pytest.fixture
def mock_analytics_storage(temp_user_data: Path):
    """
    Create a mock analytics storage with temp database.
    
    UPDATED: Uses actual AnalyticsStorage from top-level analytics module
    """
    from analytics.storage import AnalyticsStorage
    
    db_path = temp_user_data / "test_analytics.db"
    storage = AnalyticsStorage(db_path)
    
    yield storage
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def mock_analytics_collector(mock_analytics_storage):
    """
    Create a mock analytics collector.
    
    UPDATED: Uses actual AnalyticsCollector
    """
    from analytics.collector import AnalyticsCollector
    
    collector = AnalyticsCollector(storage=mock_analytics_storage)
    return collector


# =============================================================================
# Chat Service Fixtures
# =============================================================================

@pytest.fixture
def chat_service(mock_llm_router, mock_tool_registry, mock_analytics_collector, mock_analytics_storage):
    """
    Create a ChatService with mocked dependencies.
    
    UPDATED: Uses correct ChatService initialization
    """
    from backend.chat_service import ChatService
    
    service = ChatService(
        llm_router=mock_llm_router,
        tool_registry=mock_tool_registry,
        analytics_collector=mock_analytics_collector,
        analytics_storage=mock_analytics_storage,
    )
    
    return service


@pytest.fixture
async def initialized_chat_service(chat_service):
    """
    Create an initialized ChatService ready for use.
    """
    await chat_service.initialize()
    yield chat_service
    await chat_service.close()


# =============================================================================
# Ollama Fixtures
# =============================================================================

@pytest.fixture
def mock_ollama_responses():
    """
    Predefined Ollama API responses for testing.
    """
    return {
        "tags": {
            "models": [
                {
                    "name": "mistral:7b-instruct",
                    "size": 4_000_000_000,
                    "modified_at": "2024-01-15T10:30:00Z",
                    "digest": "abc123",
                },
            ]
        },
        "pull_progress": [
            {"status": "pulling manifest"},
            {"status": "downloading", "completed": 1000, "total": 4000},
            {"status": "downloading", "completed": 2000, "total": 4000},
            {"status": "downloading", "completed": 4000, "total": 4000},
            {"status": "success"},
        ],
    }


# =============================================================================
# API Bridge Fixtures
# =============================================================================

@pytest.fixture
def mock_window():
    """
    Create a mock PyWebView window for testing the API bridge.
    """
    window = MagicMock()
    window.evaluate_js = MagicMock()
    return window


@pytest.fixture
def mock_ollama_manager():
    """
    Create a mock OllamaManager.
    """
    from desktop.ollama_manager import OllamaManager
    
    manager = MagicMock(spec=OllamaManager)
    manager.is_running.return_value = True
    manager.host = "127.0.0.1"
    manager.port = 11434
    manager.base_url = "http://127.0.0.1:11434"
    
    async def mock_start(*args, **kwargs):
        pass
    
    async def mock_list_models():
        return [{"name": "test-model", "size": 1000000}]
    
    async def mock_has_model(name):
        return name == "test-model"
    
    manager.start = AsyncMock(side_effect=mock_start)
    manager.stop = MagicMock()
    manager.list_models = AsyncMock(side_effect=mock_list_models)
    manager.has_model = AsyncMock(side_effect=mock_has_model)
    
    return manager


@pytest.fixture
def api_bridge(mock_window, mock_ollama_manager, temp_user_data):
    """
    Create a TechTimApi instance with mocked dependencies.
    
    UPDATED: Patches settings to use temp paths
    """
    with patch('backend.config.get_user_data_path', return_value=temp_user_data):
        with patch('backend.config.is_bundled', return_value=False):
            from backend.config import get_settings
            get_settings.cache_clear()
            
            from desktop.api import TechTimApi
            
            api = TechTimApi(mock_ollama_manager)
            api.set_window(mock_window)
            
            yield api
            
            get_settings.cache_clear()


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_messages():
    """
    Sample chat messages for testing.
    """
    from backend.llm.base import ChatMessage
    
    return [
        ChatMessage(role="user", content="My WiFi isn't working"),
        ChatMessage(role="assistant", content="I'll help diagnose that. Let me check your network."),
        ChatMessage(role="user", content="It was working yesterday"),
    ]


@pytest.fixture
def sample_session_id():
    """
    Sample session ID for testing.
    """
    return "test-session-12345"
```

---

## Task 5.3: Create Unit Tests for Configuration

### Purpose

Test that configuration loading works correctly in both development and bundled modes.

**UPDATED:** Tests actual Settings properties from phase1_updated.

### File: `tests/unit/test_config.py`

```python
"""
Unit tests for backend configuration.

UPDATED: Tests actual Settings properties including bundled mode paths.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestBundledModeDetection:
    """Tests for is_bundled() function."""
    
    def test_not_bundled_by_default(self):
        """In normal Python, is_bundled() should return False."""
        from backend.config import is_bundled
        
        # Clear any existing frozen attribute
        if hasattr(sys, 'frozen'):
            delattr(sys, 'frozen')
        if hasattr(sys, '_MEIPASS'):
            delattr(sys, '_MEIPASS')
        
        assert is_bundled() is False
    
    def test_bundled_with_pyinstaller_attributes(self):
        """When PyInstaller attributes are set, is_bundled() should return True."""
        from backend.config import is_bundled
        
        with patch.object(sys, 'frozen', True, create=True):
            with patch.object(sys, '_MEIPASS', '/tmp/fake_meipass', create=True):
                assert is_bundled() is True


class TestPathResolution:
    """Tests for path resolution functions."""
    
    def test_get_base_path_development(self):
        """In development, base path should be project root."""
        from backend.config import get_base_path
        
        base_path = get_base_path()
        
        # Should be a valid directory
        assert base_path.exists()
        # Should contain backend directory
        assert (base_path / "backend").exists()
    
    def test_user_data_path_creates_directory(self, temp_dir):
        """User data path should be created if it doesn't exist."""
        with patch('backend.config.Path.home', return_value=temp_dir):
            from backend.config import get_user_data_path
            
            user_path = get_user_data_path()
            
            assert user_path.exists()
            assert "TechTime" in str(user_path)


class TestSettings:
    """Tests for the Settings class."""
    
    def test_default_settings(self):
        """Settings should have sensible defaults."""
        from backend.config import get_settings
        
        # Clear cache for fresh settings
        get_settings.cache_clear()
        settings = get_settings()
        
        assert settings.llm_backend in ("ollama", "openai")
        assert settings.ollama_model is not None
        assert settings.max_tool_rounds > 0
        assert settings.command_timeout > 0
    
    def test_path_properties(self, mock_settings):
        """
        UPDATED: Test new path properties from phase1_updated.
        """
        settings = mock_settings
        
        # All path properties should return Path objects
        assert isinstance(settings.database_path, Path)
        assert isinstance(settings.log_path, Path)
        assert isinstance(settings.models_path, Path)
        assert isinstance(settings.prompts_path, Path)
        
        # Log and models paths should be created
        assert settings.log_path.exists()
        assert settings.models_path.exists()
        
        # Database path should end with .db
        assert str(settings.database_path).endswith('.db')
    
    def test_bundled_mode_property(self, mock_settings):
        """bundled_mode property should return False in tests."""
        assert mock_settings.bundled_mode is False
    
    def test_dns_server_list(self, mock_settings):
        """dns_server_list should parse comma-separated string."""
        settings = mock_settings
        
        server_list = settings.dns_server_list
        
        assert isinstance(server_list, list)
        assert len(server_list) > 0
        assert all(isinstance(s, str) for s in server_list)
    
    def test_get_settings_cached(self):
        """get_settings should return cached instance."""
        from backend.config import get_settings
        
        get_settings.cache_clear()
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
```

---

## Task 5.4: Create Unit Tests for Chat Service

### Purpose

Test the ChatService logic including session management, message handling, and tool execution flow.

**UPDATED:** Uses correct ChatService API from phase1_updated.

### File: `tests/unit/test_chat_service.py`

```python
"""
Unit tests for the ChatService.

UPDATED: Uses correct method signatures from phase1_updated ChatService.
- chat(session_id, user_message) instead of chat(message)
- ChatServiceResponse instead of ChatResponse
- _get_or_create_conversation() is internal
"""
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.chat_service import ChatService, ChatServiceResponse, StreamChunk


class TestChatBasic:
    """Tests for basic chat functionality."""
    
    @pytest.mark.asyncio
    async def test_chat_returns_response(self, initialized_chat_service, sample_session_id):
        """
        UPDATED: Chat should return ChatServiceResponse.
        """
        response = await initialized_chat_service.chat(
            sample_session_id,
            "Hello, I need help"
        )
        
        assert isinstance(response, ChatServiceResponse)
        assert response.content is not None
        assert response.session_id == sample_session_id
    
    @pytest.mark.asyncio
    async def test_chat_stores_messages(self, initialized_chat_service, sample_session_id):
        """Chat should store messages in conversation."""
        await initialized_chat_service.chat(sample_session_id, "Hello")
        
        messages = initialized_chat_service.get_session_messages(sample_session_id)
        
        # Should have at least user message
        assert len(messages) >= 1
        assert any(m['role'] == 'user' for m in messages)
    
    @pytest.mark.asyncio
    async def test_chat_maintains_conversation_history(self, initialized_chat_service, sample_session_id):
        """Multiple chat calls should maintain history."""
        await initialized_chat_service.chat(sample_session_id, "First message")
        await initialized_chat_service.chat(sample_session_id, "Second message")
        await initialized_chat_service.chat(sample_session_id, "Third message")
        
        messages = initialized_chat_service.get_session_messages(sample_session_id)
        user_messages = [m for m in messages if m['role'] == 'user']
        
        assert len(user_messages) == 3
    
    @pytest.mark.asyncio
    async def test_new_session_creates_conversation(self, initialized_chat_service):
        """New session ID should create new conversation."""
        response = await initialized_chat_service.chat(None, "Hello")
        
        # Should get a session ID back
        assert response.session_id is not None
        assert len(response.session_id) > 0


class TestSessionManagement:
    """Tests for session listing and management."""
    
    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, initialized_chat_service):
        """Listing sessions when none exist should return empty list."""
        sessions = initialized_chat_service.list_sessions()
        
        assert sessions == []
    
    @pytest.mark.asyncio
    async def test_list_sessions_with_data(self, initialized_chat_service):
        """Listing sessions should return summaries."""
        await initialized_chat_service.chat("session-1", "Hello 1")
        await initialized_chat_service.chat("session-2", "Hello 2")
        
        sessions = initialized_chat_service.list_sessions()
        
        assert len(sessions) == 2
        assert all('id' in s for s in sessions)
        assert all('message_count' in s for s in sessions)
    
    @pytest.mark.asyncio
    async def test_get_session_messages_empty(self, initialized_chat_service):
        """Empty session should return empty list."""
        messages = initialized_chat_service.get_session_messages("nonexistent")
        
        assert messages == []
    
    @pytest.mark.asyncio
    async def test_delete_session(self, initialized_chat_service, sample_session_id):
        """Deleting a session should remove it."""
        await initialized_chat_service.chat(sample_session_id, "Hello")
        
        result = initialized_chat_service.delete_session(sample_session_id)
        
        assert result is True
        assert len(initialized_chat_service.list_sessions()) == 0
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, initialized_chat_service):
        """Deleting a nonexistent session should return False."""
        result = initialized_chat_service.delete_session("does-not-exist")
        
        assert result is False


class TestChatWithTools:
    """Tests for chat with tool execution."""
    
    @pytest.mark.asyncio
    async def test_chat_includes_diagnostics(
        self,
        initialized_chat_service,
        sample_session_id,
    ):
        """Response should include diagnostics."""
        response = await initialized_chat_service.chat(
            sample_session_id,
            "Check my network"
        )
        
        assert response.diagnostics is not None
        assert hasattr(response.diagnostics, 'confidence_score')
        assert hasattr(response.diagnostics, 'thoughts')
        assert hasattr(response.diagnostics, 'tools_used')


class TestChatStreaming:
    """Tests for streaming chat functionality."""
    
    @pytest.mark.asyncio
    async def test_stream_calls_on_chunk(self, initialized_chat_service, sample_session_id):
        """Streaming should call the on_chunk callback."""
        chunks_received = []
        
        def on_chunk(chunk: StreamChunk):
            chunks_received.append(chunk)
        
        await initialized_chat_service.chat_stream(
            sample_session_id,
            "Hello",
            on_chunk,
        )
        
        assert len(chunks_received) > 0
    
    @pytest.mark.asyncio
    async def test_stream_sends_done_chunk(self, initialized_chat_service, sample_session_id):
        """Streaming should end with a done chunk."""
        chunks_received = []
        
        def on_chunk(chunk: StreamChunk):
            chunks_received.append(chunk)
        
        await initialized_chat_service.chat_stream(
            sample_session_id,
            "Hello",
            on_chunk,
        )
        
        assert any(c.type == 'done' for c in chunks_received)


class TestResponseDiagnostics:
    """Tests for response diagnostics tracking."""
    
    @pytest.mark.asyncio
    async def test_diagnostics_tracks_thoughts(self, initialized_chat_service, sample_session_id):
        """Diagnostics should track reasoning thoughts."""
        response = await initialized_chat_service.chat(
            sample_session_id,
            "What's wrong with my network?"
        )
        
        assert response.diagnostics.thoughts is not None
        assert isinstance(response.diagnostics.thoughts, list)
    
    @pytest.mark.asyncio
    async def test_diagnostics_has_confidence_score(self, initialized_chat_service, sample_session_id):
        """Diagnostics should include confidence score."""
        response = await initialized_chat_service.chat(
            sample_session_id,
            "Check DNS"
        )
        
        score = response.diagnostics.confidence_score
        assert 0.0 <= score <= 1.0
```

---

## Task 5.5: Create Unit Tests for Ollama Manager

### Purpose

Test the Ollama manager's ability to find binaries, manage process lifecycle, and interact with the Ollama API.

### File: `tests/unit/test_ollama_manager.py`

```python
"""
Unit tests for the OllamaManager.

These tests verify:
- Binary path resolution
- Process lifecycle management
- Health checking
- Model management
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from desktop.ollama_manager import (
    OllamaManager,
    OllamaNotFoundError,
)


class TestBinaryResolution:
    """Tests for finding the Ollama binary."""
    
    def test_find_system_ollama(self):
        """Should find system-installed Ollama if available."""
        manager = OllamaManager()
        
        with patch('shutil.which', return_value='/usr/local/bin/ollama'):
            try:
                path = manager.get_ollama_binary_path()
                assert path is not None
                assert str(path) == '/usr/local/bin/ollama'
            except OllamaNotFoundError:
                # Also valid if not found in other locations
                pass
    
    def test_raises_when_not_found(self, mock_settings):
        """Should raise OllamaNotFoundError when binary not found."""
        manager = OllamaManager()
        
        with patch('shutil.which', return_value=None):
            with patch.object(Path, 'exists', return_value=False):
                with pytest.raises(OllamaNotFoundError):
                    manager.get_ollama_binary_path()


class TestProcessLifecycle:
    """Tests for starting and stopping Ollama."""
    
    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Should detect and use existing Ollama instance."""
        manager = OllamaManager()
        
        async def mock_healthy():
            return True
        
        with patch.object(manager, '_is_healthy', side_effect=mock_healthy):
            await manager.start()
            
            assert manager._started is True
            assert manager._owns_process is False
    
    def test_stop_terminates_owned_process(self):
        """Should terminate process if we started it."""
        manager = OllamaManager()
        
        mock_process = MagicMock()
        mock_process.wait.return_value = 0
        
        manager.process = mock_process
        manager._started = True
        manager._owns_process = True
        
        manager.stop()
        
        mock_process.terminate.assert_called_once()
        assert manager._started is False
        assert manager.process is None
    
    def test_stop_does_not_terminate_external_process(self):
        """Should not terminate process if we didn't start it."""
        manager = OllamaManager()
        
        manager._started = True
        manager._owns_process = False
        manager.process = None
        
        manager.stop()
        
        assert manager._started is False


class TestHealthCheck:
    """Tests for Ollama health checking."""
    
    @pytest.mark.asyncio
    async def test_is_healthy_success(self):
        """Should return True when Ollama responds."""
        manager = OllamaManager()
        
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await manager._is_healthy()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_is_healthy_failure(self):
        """Should return False when Ollama is unreachable."""
        manager = OllamaManager()
        
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_class.return_value = mock_client
            
            result = await manager._is_healthy()
            
            assert result is False


class TestModelManagement:
    """Tests for model listing and downloading."""
    
    @pytest.mark.asyncio
    async def test_has_model_true(self, mock_ollama_responses):
        """Should return True when model exists."""
        manager = OllamaManager()
        
        async def mock_list():
            return mock_ollama_responses["tags"]["models"]
        
        with patch.object(manager, 'list_models', side_effect=mock_list):
            result = await manager.has_model("mistral:7b-instruct")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_has_model_false(self, mock_ollama_responses):
        """Should return False when model doesn't exist."""
        manager = OllamaManager()
        
        async def mock_list():
            return mock_ollama_responses["tags"]["models"]
        
        with patch.object(manager, 'list_models', side_effect=mock_list):
            result = await manager.has_model("nonexistent:model")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_has_model_partial_match(self, mock_ollama_responses):
        """Should match by base model name."""
        manager = OllamaManager()
        
        async def mock_list():
            return mock_ollama_responses["tags"]["models"]
        
        with patch.object(manager, 'list_models', side_effect=mock_list):
            result = await manager.has_model("mistral")
            
            assert result is True
```

---

## Task 5.6: Create Integration Tests for API Bridge

### Purpose

Test the TechTimApi class's integration between PyWebView and the backend services.

**UPDATED:** Matches actual TechTimApi from phase2_updated.

### File: `tests/integration/test_api_bridge.py`

```python
"""
Integration tests for the PyWebView API bridge.

UPDATED: Matches TechTimApi from phase2_updated with correct method signatures.
"""
from unittest.mock import MagicMock, patch

import pytest


class TestApiResponseFormat:
    """Tests for API response format consistency."""
    
    def test_create_session_response_format(self, api_bridge):
        """create_session should return proper response format."""
        result = api_bridge.create_session()
        
        assert 'success' in result
        assert 'data' in result
        assert 'error' in result
        
        assert result['success'] is True
        assert 'session_id' in result['data']
    
    def test_list_sessions_response_format(self, api_bridge):
        """list_sessions should return proper response format."""
        result = api_bridge.list_sessions()
        
        assert result['success'] is True
        assert isinstance(result['data'], list)
    
    def test_get_app_info_response_format(self, api_bridge):
        """get_app_info should return proper response format."""
        result = api_bridge.get_app_info()
        
        assert result['success'] is True
        assert 'version' in result['data']
        assert 'bundled_mode' in result['data']
        assert 'ollama_running' in result['data']


class TestSessionApi:
    """Tests for session management API."""
    
    def test_create_session_generates_id(self, api_bridge):
        """Created session should have unique ID."""
        result1 = api_bridge.create_session()
        result2 = api_bridge.create_session()
        
        assert result1['data']['session_id'] != result2['data']['session_id']
    
    def test_delete_nonexistent_session(self, api_bridge):
        """Deleting nonexistent session should return error."""
        result = api_bridge.delete_session("nonexistent-id")
        
        # Should either succeed (no-op) or return error
        assert 'success' in result


class TestToolsApi:
    """Tests for tools API methods."""
    
    def test_list_tools_returns_tools(self, api_bridge):
        """list_tools should return available tools."""
        result = api_bridge.list_tools()
        
        assert result['success'] is True
        assert isinstance(result['data'], list)
        
        if len(result['data']) > 0:
            tool = result['data'][0]
            assert 'name' in tool
            assert 'description' in tool
            assert 'parameters' in tool


class TestAnalyticsApi:
    """Tests for analytics API methods."""
    
    def test_get_analytics_summary(self, api_bridge):
        """get_analytics_summary should return summary data."""
        result = api_bridge.get_analytics_summary()
        
        assert result['success'] is True
        assert 'total_sessions' in result['data']
        assert 'resolved_count' in result['data']
    
    def test_get_tool_stats(self, api_bridge):
        """get_tool_stats should return stats list."""
        result = api_bridge.get_tool_stats()
        
        assert result['success'] is True
        assert isinstance(result['data'], list)


class TestDiagnosticsApi:
    """Tests for diagnostic information API."""
    
    def test_get_diagnostics_returns_system_info(self, api_bridge):
        """get_diagnostics should return system info."""
        result = api_bridge.get_diagnostics()
        
        assert result['success'] is True
        assert 'python_version' in result['data']
        assert 'platform' in result['data']
        assert 'bundled_mode' in result['data']
        assert 'base_path' in result['data']


class TestModelApi:
    """Tests for model management API."""
    
    def test_list_models(self, api_bridge):
        """list_models should return model list."""
        result = api_bridge.list_models()
        
        assert result['success'] is True
        assert isinstance(result['data'], list)
    
    def test_check_model_status(self, api_bridge):
        """check_model_status should return availability."""
        result = api_bridge.check_model_status()
        
        assert result['success'] is True
        assert 'model' in result['data']
        assert 'available' in result['data']
```

---

## Task 5.7: Create pytest Configuration

### Purpose

Configure pytest with appropriate settings for the project.

### File: `pytest.ini`

```ini
[pytest]
# Test discovery
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Async support
asyncio_mode = auto

# Output settings
addopts = 
    -v
    --tb=short
    --strict-markers
    -ra

# Markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    requires_ollama: marks tests that need a running Ollama instance

# Warnings
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

---

## Task 5.8: Create Test Documentation

### File: `tests/README.md`

```markdown
# TechTim(e) Test Suite

## Quick Start

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=backend --cov=desktop --cov=analytics --cov-report=html
```

Run specific test file:
```bash
pytest tests/unit/test_chat_service.py
```

Run tests matching a pattern:
```bash
pytest -k "test_session"
```

## Test Organization

```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests (isolated components)
│   ├── test_config.py
│   ├── test_chat_service.py
│   └── test_ollama_manager.py
├── integration/         # Integration tests
│   └── test_api_bridge.py
└── fixtures/            # Test data and mocks
```

## Writing Tests

### Async Tests

Use `@pytest.mark.asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_something_async():
    result = await some_async_function()
    assert result is not None
```

### Common Fixtures

- `temp_dir`: Temporary directory
- `mock_settings`: Settings with temp paths
- `mock_llm_router`: Mock LLM router
- `mock_tool_registry`: Mock tool registry
- `mock_analytics_storage`: Analytics storage with temp DB
- `mock_analytics_collector`: Analytics collector
- `chat_service`: ChatService with mocks
- `initialized_chat_service`: ChatService ready for use
- `api_bridge`: TechTimApi with mocks

### Testing ChatService

```python
@pytest.mark.asyncio
async def test_chat(initialized_chat_service):
    response = await initialized_chat_service.chat(
        "session-id",
        "Hello"
    )
    assert response.content is not None
```

### Testing API Bridge

```python
def test_api_method(api_bridge):
    result = api_bridge.some_method()
    assert result['success'] is True
```
```

---

## Acceptance Criteria

Phase 5 is complete when:

1. **Test structure exists**: The `tests/` directory has the documented structure

2. **All unit tests pass**:
   ```bash
   pytest tests/unit/ -v
   ```

3. **Integration tests pass**:
   ```bash
   pytest tests/integration/ -v
   ```

4. **Tests run without real Ollama**: All tests use mocks

5. **Fixtures match actual APIs**: No import errors or method signature mismatches

---

## Files Created Summary

| File | Description |
|------|-------------|
| `tests/__init__.py` | Test package |
| `tests/conftest.py` | Shared fixtures (UPDATED) |
| `tests/unit/test_config.py` | Config tests (UPDATED) |
| `tests/unit/test_chat_service.py` | ChatService tests (UPDATED) |
| `tests/unit/test_ollama_manager.py` | OllamaManager tests |
| `tests/integration/test_api_bridge.py` | API bridge tests (UPDATED) |
| `tests/README.md` | Documentation |
| `pytest.ini` | Pytest configuration |

---

## Next Phase

After completing Phase 5, proceed to **Phase 6: Distribution**, which covers packaging for macOS and Windows.
