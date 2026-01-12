"""Tests for GlueLLM wrapper and adapters."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.config import Settings
from backend.llm.gluellm_wrapper import GlueLLMWrapper
from backend.llm.tool_adapter import registry_to_callables, _wrap_tool, _build_docstring
from backend.llm.result_adapter import (
    to_chat_service_response,
    extract_diagnostics,
    calculate_confidence,
    extract_token_usage,
)
from backend.tools.schemas import ToolDefinition, ToolParameter


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.provider_priority = ["openai", "anthropic", "ollama"]
    settings.openai_api_key = "test-openai-key"
    settings.openai_model = "gpt-4o"
    settings.anthropic_api_key = None
    settings.anthropic_model = "claude-3-5-sonnet-20241022"
    settings.xai_api_key = None
    settings.xai_model = "grok-2"
    settings.google_api_key = None
    settings.google_model = "gemini-1.5-pro"
    settings.ollama_host = "http://localhost:11434"
    settings.ollama_model = "ministral-3:3b"
    settings.connectivity_check_url = "https://api.openai.com"
    settings.connectivity_timeout_ms = 3000
    settings.gluellm_max_tool_iterations = 10
    return settings


@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry."""
    registry = MagicMock()
    registry.get_all_definitions.return_value = [
        ToolDefinition(
            name="test_tool",
            description="A test tool for testing",
            parameters=[
                ToolParameter(
                    name="arg1",
                    type="string",
                    description="First argument",
                    required=True,
                )
            ],
        )
    ]
    
    async def mock_tool(**kwargs):
        return "Tool executed successfully"
    
    registry.get_tool.return_value = mock_tool
    return registry


@pytest.fixture
def mock_execution_result():
    """Create mock GlueLLM ExecutionResult."""
    result = MagicMock()
    result.final_response = "This is the response from the LLM"
    result.model = "openai:gpt-4o"
    result.tool_calls_made = 2
    result.tokens_used = {
        "prompt": 100,
        "completion": 50,
        "total": 150,
    }
    result.estimated_cost_usd = 0.001
    result.tool_execution_history = [
        {
            "tool_name": "get_ip_config",
            "arguments": {},
            "result": "IP: 192.168.1.100",
            "error": False,
        },
        {
            "tool_name": "ping_dns",
            "arguments": {"server": "8.8.8.8"},
            "result": "Ping successful",
            "error": False,
        },
    ]
    return result


# =============================================================================
# Provider Selection Tests
# =============================================================================

class TestProviderSelection:
    """Test provider selection logic."""
    
    def test_selects_openai_when_online_with_key(self, mock_settings):
        """Should select OpenAI when online and API key is set."""
        wrapper = GlueLLMWrapper(settings=mock_settings)
        
        provider, model = wrapper._select_provider(is_online=True)
        
        assert provider == "openai"
        assert model == "openai:gpt-4o"
    
    def test_selects_ollama_when_offline(self, mock_settings):
        """Should select Ollama when offline."""
        wrapper = GlueLLMWrapper(settings=mock_settings)
        
        provider, model = wrapper._select_provider(is_online=False)
        
        assert provider == "ollama"
        assert model == "ollama:ministral-3:3b"
    
    def test_selects_ollama_when_no_cloud_keys(self, mock_settings):
        """Should fall back to Ollama when no cloud API keys."""
        mock_settings.openai_api_key = None
        wrapper = GlueLLMWrapper(settings=mock_settings)
        
        provider, model = wrapper._select_provider(is_online=True)
        
        assert provider == "ollama"
        assert wrapper._had_fallback is True
    
    def test_follows_priority_order(self, mock_settings):
        """Should check providers in priority order."""
        mock_settings.provider_priority = ["anthropic", "openai", "ollama"]
        mock_settings.anthropic_api_key = "test-anthropic-key"
        wrapper = GlueLLMWrapper(settings=mock_settings)
        
        provider, model = wrapper._select_provider(is_online=True)
        
        assert provider == "anthropic"
        assert model == "anthropic:claude-3-5-sonnet-20241022"


# =============================================================================
# Connectivity Tests
# =============================================================================

class TestConnectivity:
    """Test connectivity checking."""
    
    @pytest.mark.asyncio
    async def test_connectivity_check_success(self, mock_settings):
        """Should return True when connectivity check succeeds."""
        wrapper = GlueLLMWrapper(settings=mock_settings)
        
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            
            is_online = await wrapper.check_connectivity()
            
            assert is_online is True
    
    @pytest.mark.asyncio
    async def test_connectivity_check_failure(self, mock_settings):
        """Should return False when connectivity check fails."""
        wrapper = GlueLLMWrapper(settings=mock_settings)
        
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            
            is_online = await wrapper.check_connectivity()
            
            assert is_online is False


# =============================================================================
# Tool Adapter Tests
# =============================================================================

class TestToolAdapter:
    """Test tool adapter functionality."""
    
    def test_registry_to_callables(self, mock_tool_registry):
        """Should convert registry tools to callables."""
        callables = registry_to_callables(mock_tool_registry)
        
        assert len(callables) == 1
        assert callables[0].__name__ == "test_tool"
    
    def test_wrap_tool_sets_docstring(self, mock_tool_registry):
        """Should set docstring for GlueLLM schema generation."""
        definition = mock_tool_registry.get_all_definitions()[0]
        tool_func = mock_tool_registry.get_tool("test_tool")
        
        wrapped = _wrap_tool(definition, tool_func, None)
        
        assert "A test tool for testing" in wrapped.__doc__
        assert "arg1" in wrapped.__doc__
    
    @pytest.mark.asyncio
    async def test_wrap_tool_timing_callback(self):
        """Should call timing callback after execution."""
        timings = []
        
        def timing_callback(name, duration_ms, success):
            timings.append((name, duration_ms, success))
        
        async def test_tool(**kwargs):
            return "result"
        
        definition = ToolDefinition(
            name="timing_test",
            description="Test timing",
            parameters=[],
        )
        
        wrapped = _wrap_tool(definition, test_tool, timing_callback)
        result = await wrapped()
        
        assert result == "result"
        assert len(timings) == 1
        assert timings[0][0] == "timing_test"
        assert timings[0][2] is True  # success
    
    def test_build_docstring_with_parameters(self):
        """Should build docstring with parameter docs."""
        definition = ToolDefinition(
            name="test_tool",
            description="Test description",
            parameters=[
                ToolParameter(
                    name="param1",
                    type="string",
                    description="First param",
                    required=True,
                ),
                ToolParameter(
                    name="param2",
                    type="number",
                    description="Second param",
                    required=False,
                    default=10,
                ),
            ],
        )
        
        docstring = _build_docstring(definition)
        
        assert "Test description" in docstring
        assert "param1" in docstring
        assert "(required)" in docstring
        assert "param2" in docstring
        assert "(optional)" in docstring


# =============================================================================
# Result Adapter Tests
# =============================================================================

class TestResultAdapter:
    """Test result adapter functionality."""
    
    def test_to_chat_service_response(self, mock_execution_result):
        """Should convert ExecutionResult to ChatServiceResponse."""
        response = to_chat_service_response(
            mock_execution_result,
            session_id="test-session-123",
        )
        
        assert response.content == "This is the response from the LLM"
        assert response.session_id == "test-session-123"
        assert len(response.tool_calls) == 2
        assert response.tool_calls[0]["name"] == "get_ip_config"
    
    def test_extract_diagnostics(self, mock_execution_result):
        """Should extract diagnostics from ExecutionResult."""
        diagnostics = extract_diagnostics(mock_execution_result)
        
        assert "Model: openai:gpt-4o" in diagnostics.thoughts
        assert "Tool calls made: 2" in diagnostics.thoughts
        assert len(diagnostics.tools_used) == 2
    
    def test_calculate_confidence_all_success(self):
        """Should calculate high confidence when all tools succeed."""
        history = [
            {"tool_name": "tool1", "error": False},
            {"tool_name": "tool2", "error": False},
        ]
        
        confidence = calculate_confidence(history)
        
        assert confidence == 0.9  # 0.5 base + 0.4 bonus
    
    def test_calculate_confidence_mixed_results(self):
        """Should calculate medium confidence with mixed results."""
        history = [
            {"tool_name": "tool1", "error": False},
            {"tool_name": "tool2", "error": True},
        ]
        
        confidence = calculate_confidence(history)
        
        assert confidence == 0.7  # 0.5 base + 0.2 (50% success)
    
    def test_calculate_confidence_empty_history(self):
        """Should return base confidence when no tools executed."""
        confidence = calculate_confidence(None)
        
        assert confidence == 0.5
    
    def test_extract_token_usage(self, mock_execution_result):
        """Should extract token usage in standardized format."""
        usage = extract_token_usage(mock_execution_result)
        
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 150
    
    def test_extract_token_usage_empty(self):
        """Should return zeros when no token usage."""
        result = MagicMock()
        result.tokens_used = None
        
        usage = extract_token_usage(result)
        
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0
        assert usage["total_tokens"] == 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestGlueLLMWrapperIntegration:
    """Integration tests for GlueLLM wrapper."""
    
    @pytest.mark.asyncio
    async def test_chat_flow(self, mock_settings, mock_tool_registry, mock_execution_result):
        """Should complete full chat flow."""
        wrapper = GlueLLMWrapper(
            settings=mock_settings,
            tool_registry=mock_tool_registry,
        )
        
        with patch.object(wrapper, "check_connectivity", return_value=True):
            with patch("backend.llm.gluellm_wrapper.complete", return_value=mock_execution_result):
                response = await wrapper.chat(
                    messages=[{"role": "user", "content": "Help with network"}],
                    system_prompt="You are a helpful assistant",
                )
        
        assert response.content == "This is the response from the LLM"
        assert wrapper.active_provider == "openai"
        assert wrapper.is_offline is False
    
    @pytest.mark.asyncio
    async def test_offline_fallback(self, mock_settings, mock_tool_registry, mock_execution_result):
        """Should fall back to Ollama when offline."""
        wrapper = GlueLLMWrapper(
            settings=mock_settings,
            tool_registry=mock_tool_registry,
        )
        
        with patch.object(wrapper, "check_connectivity", return_value=False):
            with patch("backend.llm.gluellm_wrapper.complete", return_value=mock_execution_result):
                response = await wrapper.chat(
                    messages=[{"role": "user", "content": "Help with network"}],
                )
        
        assert wrapper.active_provider == "ollama"
        assert wrapper.is_offline is True
    
    @pytest.mark.asyncio
    async def test_analytics_recording(self, mock_settings, mock_tool_registry, mock_execution_result):
        """Should record analytics when collector is provided."""
        mock_analytics = MagicMock()
        mock_analytics.record_llm_call = MagicMock()
        mock_analytics.record_tool_call = MagicMock()
        
        wrapper = GlueLLMWrapper(
            settings=mock_settings,
            tool_registry=mock_tool_registry,
            analytics_collector=mock_analytics,
        )
        
        with patch.object(wrapper, "check_connectivity", return_value=True):
            with patch("backend.llm.gluellm_wrapper.complete", return_value=mock_execution_result):
                await wrapper.chat(
                    messages=[{"role": "user", "content": "Test"}],
                )
        
        mock_analytics.record_llm_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_provider_availability(self, mock_settings):
        """Should report provider availability correctly."""
        wrapper = GlueLLMWrapper(settings=mock_settings)
        
        with patch.object(wrapper, "check_connectivity", return_value=True):
            availability = await wrapper.is_available()
        
        assert availability["online"] is True
        assert availability["openai"] is True  # has API key
        assert availability["anthropic"] is False  # no API key
        assert availability["ollama"] is True  # always available
