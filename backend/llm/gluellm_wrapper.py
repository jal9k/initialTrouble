"""GlueLLM wrapper with cloud-first provider selection and analytics.

This module provides a unified interface to multiple LLM providers through
GlueLLM, with automatic fallback from cloud providers to local Ollama when
offline.

Provider Priority (when online):
    1. OpenAI (if OPENAI_API_KEY set)
    2. Anthropic (if ANTHROPIC_API_KEY set)
    3. xAI/Grok (if XAI_API_KEY set)
    4. Google/Gemini (if GOOGLE_API_KEY set)

Fallback (when offline):
    - Ollama sidecar (always running)
"""

import logging
import os
from typing import TYPE_CHECKING, Any

import httpx
from gluellm import complete

from ..config import Settings, get_settings
from ..tools import ToolRegistry, get_registry
from .tool_adapter import registry_to_callables
from .result_adapter import to_chat_service_response, extract_token_usage

if TYPE_CHECKING:
    from analytics import AnalyticsCollector
    from ..chat_service import ChatServiceResponse

logger = logging.getLogger("techtime.llm.gluellm_wrapper")


class GlueLLMWrapper:
    """
    Wrapper for GlueLLM with cloud-first provider selection.
    
    This class manages:
    - Provider selection based on connectivity and API keys
    - Tool conversion from ToolRegistry to GlueLLM callables
    - Analytics integration for token and tool tracking
    - Timing callbacks for performance monitoring
    
    Example:
        wrapper = GlueLLMWrapper()
        response = await wrapper.chat(
            messages=[{"role": "user", "content": "My WiFi isn't working"}],
            system_prompt="You are a helpful IT support assistant."
        )
    """
    
    def __init__(
        self,
        settings: Settings | None = None,
        tool_registry: ToolRegistry | None = None,
        analytics_collector: "AnalyticsCollector | None" = None,
    ):
        """
        Initialize the GlueLLM wrapper.
        
        Args:
            settings: Application settings (uses global if not provided)
            tool_registry: Tool registry (uses global if not provided)
            analytics_collector: Optional analytics collector for tracking
        """
        self._settings = settings or get_settings()
        self._tool_registry = tool_registry or get_registry()
        self._analytics = analytics_collector
        
        # State tracking
        self._current_provider: str | None = None
        self._current_model: str | None = None
        self._is_offline: bool = False
        self._tool_timings: list[tuple[str, int, bool]] = []
        self._had_fallback: bool = False
        
        # Configure GlueLLM environment based on settings
        self._configure_gluellm_env()
    
    def _configure_gluellm_env(self) -> None:
        """
        Configure GlueLLM via environment variables.
        
        GlueLLM reads API keys from environment, so we ensure
        our settings are propagated.
        """
        if self._settings.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", self._settings.openai_api_key)
        if self._settings.anthropic_api_key:
            os.environ.setdefault("ANTHROPIC_API_KEY", self._settings.anthropic_api_key)
        if self._settings.xai_api_key:
            os.environ.setdefault("XAI_API_KEY", self._settings.xai_api_key)
        if self._settings.google_api_key:
            os.environ.setdefault("GOOGLE_API_KEY", self._settings.google_api_key)
    
    def set_analytics(self, collector: "AnalyticsCollector") -> None:
        """Set the analytics collector."""
        self._analytics = collector
    
    async def check_connectivity(self) -> bool:
        """
        Check if internet is available.
        
        Performs a lightweight HTTP request to the configured
        connectivity check URL.
        
        Returns:
            True if online, False if offline
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._settings.connectivity_check_url,
                    timeout=self._settings.connectivity_timeout_ms / 1000,
                )
                is_online = response.status_code < 500
                logger.debug(f"Connectivity check: {'online' if is_online else 'offline'}")
                return is_online
        except Exception as e:
            logger.debug(f"Connectivity check failed: {e}")
            return False
    
    def _select_provider(self, is_online: bool) -> tuple[str, str]:
        """
        Select provider and model based on connectivity and API keys.
        
        When online, checks providers in priority order (from settings).
        When offline, falls back to Ollama.
        
        Args:
            is_online: Whether internet is available
        
        Returns:
            Tuple of (provider_name, model_string)
            Model string is in format "provider:model" for GlueLLM
        """
        if is_online:
            # Map provider names to (api_key, model) from settings
            providers = {
                "openai": (self._settings.openai_api_key, self._settings.openai_model),
                "anthropic": (self._settings.anthropic_api_key, self._settings.anthropic_model),
                "xai": (self._settings.xai_api_key, self._settings.xai_model),
                "google": (self._settings.google_api_key, self._settings.google_model),
            }
            
            # Check providers in priority order
            for provider in self._settings.provider_priority:
                if provider == "ollama":
                    # Skip ollama in online mode unless it's the only option
                    continue
                if provider in providers:
                    api_key, model = providers[provider]
                    if api_key:
                        logger.info(f"Selected cloud provider: {provider} ({model})")
                        return provider, f"{provider}:{model}"
            
            # No cloud provider available, fall back to Ollama even when online
            logger.warning("No cloud API keys configured, falling back to Ollama")
            self._had_fallback = True
        
        # Fallback to Ollama (offline or no cloud keys)
        logger.info(f"Using Ollama fallback: {self._settings.ollama_model}")
        return "ollama", f"ollama:{self._settings.ollama_model}"
    
    def _record_tool_timing(self, name: str, duration_ms: int, success: bool) -> None:
        """
        Callback for tool timing tracking.
        
        Called by the tool adapter after each tool execution.
        
        Args:
            name: Tool name
            duration_ms: Execution duration in milliseconds
            success: Whether the tool succeeded
        """
        self._tool_timings.append((name, duration_ms, success))
        logger.debug(f"Tool '{name}' completed in {duration_ms}ms, success={success}")
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> "ChatServiceResponse":
        """
        Send chat request through GlueLLM.
        
        Automatically selects cloud or Ollama based on connectivity.
        Tools are converted from the ToolRegistry and executed automatically
        by GlueLLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system_prompt: Optional system prompt to use
        
        Returns:
            ChatServiceResponse with the assistant's reply
        """
        # Reset state for this request
        self._tool_timings = []
        self._had_fallback = False
        
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
        
        # Convert tools to callables with timing callback
        tools = registry_to_callables(
            self._tool_registry,
            timing_callback=self._record_tool_timing,
        )
        
        # Extract user message (last user message in the list)
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            logger.warning("No user message found in messages list")
        
        # Call GlueLLM
        logger.debug(f"Calling GlueLLM with {len(tools)} tools")
        result = await complete(
            user_message=user_message,
            model=model,
            system_prompt=system_prompt,
            tools=tools if tools else None,
            execute_tools=True,
            max_tool_iterations=self._settings.gluellm_max_tool_iterations,
        )
        
        logger.info(
            f"GlueLLM response: {result.tool_calls_made} tool calls, "
            f"{len(result.final_response or '')} chars"
        )
        
        # Record analytics
        self._record_analytics(result, model)
        
        # Convert to ChatServiceResponse
        return to_chat_service_response(
            result,
            session_id="",  # Will be set by ChatService
            tool_timings=self._tool_timings,
        )
    
    def _record_analytics(self, result: Any, model: str) -> None:
        """
        Record analytics for the LLM call.
        
        Tracks:
        - LLM call with token usage
        - Individual tool calls with timing
        
        Args:
            result: GlueLLM ExecutionResult
            model: Model string used
        """
        if not self._analytics:
            return
        
        # Record LLM call
        token_usage = extract_token_usage(result)
        self._analytics.record_llm_call(
            duration_ms=0,  # GlueLLM doesn't expose total duration
            prompt_tokens=token_usage["prompt_tokens"],
            completion_tokens=token_usage["completion_tokens"],
            model_name=model,
        )
        
        # Record tool calls from our timing callback
        for name, duration_ms, success in self._tool_timings:
            self._analytics.record_tool_call(
                tool_name=name,
                duration_ms=duration_ms,
                success=success,
            )
    
    async def is_available(self) -> dict[str, bool]:
        """
        Check availability of all providers.
        
        Returns:
            Dict mapping provider names to availability status
        """
        is_online = await self.check_connectivity()
        
        return {
            "online": is_online,
            "openai": is_online and bool(self._settings.openai_api_key),
            "anthropic": is_online and bool(self._settings.anthropic_api_key),
            "xai": is_online and bool(self._settings.xai_api_key),
            "google": is_online and bool(self._settings.google_api_key),
            "ollama": True,  # Always running as sidecar
        }
    
    @property
    def active_provider(self) -> str | None:
        """Get the name of the currently active provider."""
        return self._current_provider
    
    @property
    def active_model(self) -> str | None:
        """Get the model string of the currently active model."""
        return self._current_model
    
    @property
    def is_offline(self) -> bool:
        """Check if currently operating in offline mode."""
        return self._is_offline
    
    @property
    def had_fallback(self) -> bool:
        """Check if a fallback to Ollama occurred."""
        return self._had_fallback or self._is_offline
