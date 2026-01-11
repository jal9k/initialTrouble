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
    router.set_analytics = MagicMock()
    
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
        name: str = "test_tool",
        success: bool = True,
        content: str = "Tool executed successfully",
    ):
        return ToolResult(
            tool_call_id=tool_call_id,
            name=name,
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
            name=tool_call.name,
            success=True,
            content=f"Executed {tool_call.name}",
        )
    
    registry.execute = AsyncMock(side_effect=mock_execute)
    registry.__len__ = MagicMock(return_value=3)
    registry.set_analytics = MagicMock()
    
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

