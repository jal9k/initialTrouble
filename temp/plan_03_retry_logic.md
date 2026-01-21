# Plan: Implement Retry Logic with Exponential Backoff

**Priority**: High  
**Effort**: Low  
**Status**: Not Started

---

## Problem

Current LLM calls have no retry logic:
- Single point of failure on API errors
- No recovery from transient network issues
- No graceful degradation to Ollama when cloud fails

```python
# Current: No retry, no fallback on error
result = await complete(...)  # If this fails, the whole request fails
```

## Goal

Implement retry logic with exponential backoff using `tenacity`, with graceful fallback to Ollama when cloud providers fail after retries.

---

## Implementation Steps

### Step 1: Add Dependency

**Modify: `pyproject.toml`**

```toml
[project]
dependencies = [
    # ... existing deps ...
    "tenacity>=8.2.0",
]
```

### Step 2: Implement Retry Logic in GlueLLMWrapper

**Modify: `backend/llm/gluellm_wrapper.py`**

```python
"""GlueLLM wrapper with cloud-first provider selection, retry logic, and analytics."""

import logging
import os
from typing import TYPE_CHECKING, Any

import httpx
from gluellm import complete
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

from ..config import Settings, get_settings
from ..tools import ToolRegistry, get_registry
from .tool_adapter import registry_to_callables
from .result_adapter import to_chat_service_response, extract_token_usage

if TYPE_CHECKING:
    from analytics import AnalyticsCollector
    from ..chat_service import ChatServiceResponse

logger = logging.getLogger("techtime.llm.gluellm_wrapper")


# Exceptions worth retrying
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
    ConnectionError,
    TimeoutError,
)


class GlueLLMWrapper:
    """
    Wrapper for GlueLLM with cloud-first provider selection and retry logic.
    
    Features:
    - Provider selection based on connectivity and API keys
    - Retry with exponential backoff on transient failures
    - Graceful fallback to Ollama when cloud providers fail
    - Analytics integration for tracking
    """
    
    def __init__(
        self,
        settings: Settings | None = None,
        tool_registry: ToolRegistry | None = None,
        analytics_collector: "AnalyticsCollector | None" = None,
    ):
        self._settings = settings or get_settings()
        self._tool_registry = tool_registry or get_registry()
        self._analytics = analytics_collector
        
        # State tracking
        self._current_provider: str | None = None
        self._current_model: str | None = None
        self._is_offline: bool = False
        self._tool_timings: list[tuple[str, int, bool]] = []
        self._had_fallback: bool = False
        self._retry_count: int = 0
        
        # Configure GlueLLM environment
        self._configure_gluellm_env()
    
    # ... existing methods ...
    
    def _create_retry_decorator(self):
        """
        Create a retry decorator with exponential backoff.
        
        Configuration:
        - 3 attempts maximum
        - Exponential backoff: 1s, 2s, 4s
        - Only retry on network/timeout errors
        """
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
    
    async def _call_with_retry(
        self,
        user_message: str,
        model: str,
        system_prompt: str | None,
        tools: list | None,
    ) -> Any:
        """
        Make LLM call with retry logic.
        
        Retries up to 3 times with exponential backoff on transient failures.
        """
        @self._create_retry_decorator()
        async def _do_call():
            return await complete(
                user_message=user_message,
                model=model,
                system_prompt=system_prompt,
                tools=tools,
                execute_tools=True,
                max_tool_iterations=self._settings.gluellm_max_tool_iterations,
            )
        
        return await _do_call()
    
    async def _fallback_to_ollama(
        self,
        user_message: str,
        system_prompt: str | None,
        tools: list | None,
    ) -> Any:
        """
        Fallback to Ollama when cloud providers fail.
        
        This is called after all retry attempts on cloud providers have failed.
        """
        logger.warning("Cloud providers failed, falling back to Ollama")
        self._had_fallback = True
        self._current_provider = "ollama"
        self._current_model = f"ollama:{self._settings.ollama_model}"
        
        # Try Ollama (local, more reliable)
        return await complete(
            user_message=user_message,
            model=self._current_model,
            system_prompt=system_prompt,
            tools=tools,
            execute_tools=True,
            max_tool_iterations=self._settings.gluellm_max_tool_iterations,
        )
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> "ChatServiceResponse":
        """
        Send chat request through GlueLLM with retry and fallback.
        
        Behavior:
        1. Select cloud provider based on connectivity and API keys
        2. Attempt call with up to 3 retries on transient failures
        3. If cloud fails after retries, fall back to Ollama
        """
        # Reset state for this request
        self._tool_timings = []
        self._had_fallback = False
        self._retry_count = 0
        
        # Check connectivity and select provider
        is_online = await self.check_connectivity()
        self._is_offline = not is_online
        provider, model = self._select_provider(is_online)
        self._current_provider = provider
        self._current_model = model
        
        logger.info(
            f"Processing chat - provider: {provider}, model: {model}, "
            f"offline: {self._is_offline}"
        )
        
        # Convert tools to callables
        tools = registry_to_callables(
            self._tool_registry,
            timing_callback=self._record_tool_timing,
        )
        
        # Extract user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            logger.warning("No user message found in messages list")
        
        # Call with retry logic
        result = None
        try:
            logger.debug(f"Calling GlueLLM with {len(tools)} tools (with retry)")
            result = await self._call_with_retry(
                user_message=user_message,
                model=model,
                system_prompt=system_prompt,
                tools=tools if tools else None,
            )
        except RetryError as e:
            logger.error(f"All retry attempts failed: {e}")
            # If we were using a cloud provider, try Ollama
            if provider != "ollama":
                try:
                    result = await self._fallback_to_ollama(
                        user_message=user_message,
                        system_prompt=system_prompt,
                        tools=tools if tools else None,
                    )
                except Exception as fallback_error:
                    logger.exception(f"Ollama fallback also failed: {fallback_error}")
                    raise RuntimeError(
                        f"All LLM providers failed. Cloud error: {e}. "
                        f"Ollama error: {fallback_error}"
                    ) from e
            else:
                raise
        except Exception as e:
            logger.exception(f"Unexpected error during LLM call: {e}")
            # Try Ollama as last resort if not already using it
            if provider != "ollama":
                try:
                    result = await self._fallback_to_ollama(
                        user_message=user_message,
                        system_prompt=system_prompt,
                        tools=tools if tools else None,
                    )
                except Exception as fallback_error:
                    logger.exception(f"Ollama fallback also failed: {fallback_error}")
                    raise
            else:
                raise
        
        logger.info(
            f"GlueLLM response: {result.tool_calls_made} tool calls, "
            f"{len(result.final_response or '')} chars, "
            f"fallback={self._had_fallback}"
        )
        
        # Record analytics
        self._record_analytics(result, self._current_model)
        
        # Convert to ChatServiceResponse
        return to_chat_service_response(
            result,
            session_id="",
            tool_timings=self._tool_timings,
        )
    
    # ... rest of existing methods ...
```

### Step 3: Add Retry Configuration to Settings

**Modify: `backend/config.py`**

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Retry Configuration
    llm_retry_attempts: int = 3
    llm_retry_min_wait: int = 1  # seconds
    llm_retry_max_wait: int = 10  # seconds
    llm_retry_multiplier: float = 1.0
```

### Step 4: Update Wrapper to Use Configurable Retry

```python
def _create_retry_decorator(self):
    return retry(
        stop=stop_after_attempt(self._settings.llm_retry_attempts),
        wait=wait_exponential(
            multiplier=self._settings.llm_retry_multiplier,
            min=self._settings.llm_retry_min_wait,
            max=self._settings.llm_retry_max_wait,
        ),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
```

### Step 5: Add Tests

**File: `backend/tests/test_retry_logic.py`**

```python
"""Tests for LLM retry logic and fallback behavior."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from backend.llm.gluellm_wrapper import GlueLLMWrapper, RETRYABLE_EXCEPTIONS


class TestRetryLogic:
    """Test suite for retry and fallback behavior."""
    
    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.openai_api_key = "test-key"
        settings.openai_model = "gpt-4"
        settings.ollama_model = "ministral-3:3b"
        settings.ollama_host = "http://localhost:11434"
        settings.provider_priority = ["openai", "ollama"]
        settings.gluellm_max_tool_iterations = 10
        settings.llm_retry_attempts = 3
        settings.llm_retry_min_wait = 0.1
        settings.llm_retry_max_wait = 0.5
        settings.llm_retry_multiplier = 1.0
        settings.connectivity_check_url = "https://api.openai.com"
        settings.connectivity_timeout_ms = 3000
        return settings
    
    @pytest.fixture
    def wrapper(self, mock_settings):
        with patch('backend.llm.gluellm_wrapper.get_settings', return_value=mock_settings):
            return GlueLLMWrapper(settings=mock_settings)
    
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self, wrapper):
        """Should succeed without retry if first call works."""
        mock_result = MagicMock()
        mock_result.final_response = "Success"
        mock_result.tool_calls_made = 0
        
        with patch('backend.llm.gluellm_wrapper.complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_result
            
            result = await wrapper._call_with_retry(
                user_message="test",
                model="openai:gpt-4",
                system_prompt=None,
                tools=None,
            )
            
            assert mock_complete.call_count == 1
            assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, wrapper):
        """Should retry on timeout and succeed."""
        mock_result = MagicMock()
        mock_result.final_response = "Success"
        mock_result.tool_calls_made = 0
        
        with patch('backend.llm.gluellm_wrapper.complete', new_callable=AsyncMock) as mock_complete:
            # Fail twice, then succeed
            mock_complete.side_effect = [
                httpx.TimeoutException("Timeout 1"),
                httpx.TimeoutException("Timeout 2"),
                mock_result,
            ]
            
            result = await wrapper._call_with_retry(
                user_message="test",
                model="openai:gpt-4",
                system_prompt=None,
                tools=None,
            )
            
            assert mock_complete.call_count == 3
            assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_retry_exhausted_raises(self, wrapper):
        """Should raise after all retries exhausted."""
        with patch('backend.llm.gluellm_wrapper.complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.side_effect = httpx.TimeoutException("Always timeout")
            
            with pytest.raises(Exception):  # RetryError or wrapped
                await wrapper._call_with_retry(
                    user_message="test",
                    model="openai:gpt-4",
                    system_prompt=None,
                    tools=None,
                )
            
            # Should have tried 3 times
            assert mock_complete.call_count == 3
    
    @pytest.mark.asyncio
    async def test_fallback_to_ollama_on_cloud_failure(self, wrapper):
        """Should fallback to Ollama when cloud fails after retries."""
        mock_ollama_result = MagicMock()
        mock_ollama_result.final_response = "Ollama response"
        mock_ollama_result.tool_calls_made = 0
        
        with patch.object(wrapper, 'check_connectivity', new_callable=AsyncMock) as mock_conn:
            mock_conn.return_value = True  # Online
            
            with patch('backend.llm.gluellm_wrapper.complete', new_callable=AsyncMock) as mock_complete:
                # Cloud fails, Ollama succeeds
                mock_complete.side_effect = [
                    httpx.TimeoutException("Cloud 1"),
                    httpx.TimeoutException("Cloud 2"),
                    httpx.TimeoutException("Cloud 3"),
                    mock_ollama_result,  # Ollama success
                ]
                
                with patch.object(wrapper, '_record_analytics'):
                    result = await wrapper.chat(
                        messages=[{"role": "user", "content": "test"}],
                        system_prompt=None,
                    )
                
                assert wrapper._had_fallback
                assert wrapper._current_provider == "ollama"
    
    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self, wrapper):
        """Should not retry on authentication errors (non-retryable)."""
        with patch('backend.llm.gluellm_wrapper.complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.side_effect = ValueError("Invalid API key")
            
            with pytest.raises(ValueError):
                await wrapper._call_with_retry(
                    user_message="test",
                    model="openai:gpt-4",
                    system_prompt=None,
                    tools=None,
                )
            
            # Should only try once (no retry on non-retryable errors)
            assert mock_complete.call_count == 1
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | Modify | Add tenacity dependency |
| `backend/llm/gluellm_wrapper.py` | Modify | Add retry logic and fallback |
| `backend/config.py` | Modify | Add retry configuration |
| `backend/tests/test_retry_logic.py` | Create | Unit tests for retry behavior |

---

## Testing Plan

1. **Unit Tests**
   - Success on first attempt
   - Retry on timeout/network errors
   - Retry exhaustion raises exception
   - Fallback to Ollama on cloud failure
   - No retry on non-retryable errors (auth, rate limit)

2. **Integration Tests**
   - End-to-end with simulated network failures
   - Verify fallback preserves conversation context

3. **Manual Testing**
   - Disconnect network during cloud call → should fallback
   - Slow network → should retry with backoff

---

## Success Criteria

- [ ] Retries up to 3 times on transient failures
- [ ] Exponential backoff between retries
- [ ] Falls back to Ollama when cloud fails
- [ ] No retry on non-retryable errors
- [ ] Configurable via env vars
- [ ] Logging shows retry attempts
- [ ] All tests pass
