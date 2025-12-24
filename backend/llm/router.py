"""LLM router for managing multiple backends."""

import logging
import time
from typing import TYPE_CHECKING, Literal

from ..config import Settings, get_settings
from ..tools.schemas import ToolDefinition
from .base import BaseLLMClient, ChatMessage, ChatResponse
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient

if TYPE_CHECKING:
    from analytics import AnalyticsCollector

logger = logging.getLogger("techtime.llm.router")


class LLMRouter:
    """Router for managing LLM backends with fallback support."""

    def __init__(
        self,
        settings: Settings | None = None,
        prefer: Literal["ollama", "openai"] | None = None,
        analytics_collector: "AnalyticsCollector | None" = None,
    ):
        """
        Initialize LLM router.

        Args:
            settings: Application settings (uses global if not provided)
            prefer: Preferred backend (overrides settings)
            analytics_collector: Optional analytics collector for tracking
        """
        self.settings = settings or get_settings()
        self.preferred = prefer or self.settings.llm_backend
        self._analytics = analytics_collector

        self._ollama: OllamaClient | None = None
        self._openai: OpenAIClient | None = None
        self._active: BaseLLMClient | None = None
        self._had_fallback: bool = False
        self._fallback_from: str | None = None

    @property
    def ollama(self) -> OllamaClient:
        """Get or create Ollama client."""
        if self._ollama is None:
            self._ollama = OllamaClient(
                host=self.settings.ollama_host,
                model=self.settings.ollama_model,
            )
        return self._ollama

    @property
    def openai(self) -> OpenAIClient | None:
        """Get or create OpenAI client (if API key is set)."""
        if self._openai is None and self.settings.openai_api_key:
            self._openai = OpenAIClient(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_model,
            )
        return self._openai

    def set_analytics(self, collector: "AnalyticsCollector") -> None:
        """Set the analytics collector."""
        self._analytics = collector

    async def get_client(self) -> BaseLLMClient:
        """
        Get the best available LLM client.

        Tries preferred backend first, then falls back to alternative.

        Returns:
            Available LLM client

        Raises:
            RuntimeError: If no LLM backend is available
        """
        if self._active is not None:
            return self._active

        # Try preferred backend first
        if self.preferred == "ollama":
            logger.debug("Checking Ollama availability...")
            if await self.ollama.is_available():
                logger.info(f"Using Ollama backend with model: {self.ollama.model_name}")
                self._active = self.ollama
                return self._active

            # Fallback to OpenAI
            logger.warning("Ollama not available, trying OpenAI fallback...")
            if self.openai and await self.openai.is_available():
                self._had_fallback = True
                self._fallback_from = "ollama"
                self._active = self.openai
                logger.info(f"Fell back to OpenAI with model: {self.openai.model_name}")
                # Record fallback in analytics
                if self._analytics:
                    self._analytics.record_fallback(
                        from_backend="ollama",
                        to_backend="openai",
                        reason="Ollama not available",
                    )
                return self._active

        else:  # Prefer OpenAI
            if self.openai and await self.openai.is_available():
                self._active = self.openai
                return self._active

            # Fallback to Ollama
            if await self.ollama.is_available():
                self._had_fallback = True
                self._fallback_from = "openai"
                self._active = self.ollama
                # Record fallback in analytics
                if self._analytics:
                    self._analytics.record_fallback(
                        from_backend="openai",
                        to_backend="ollama",
                        reason="OpenAI not available",
                    )
                return self._active

        raise RuntimeError(
            "No LLM backend available. Please ensure Ollama is running "
            "or set OPENAI_API_KEY in your environment."
        )

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        tool_choice: str | dict | None = "auto",
    ) -> ChatResponse:
        """
        Send chat completion request to best available backend.

        Args:
            messages: Conversation history
            tools: Available tools for function calling
            temperature: Sampling temperature
            tool_choice: Tool calling behavior ("auto", "required", "none", or specific tool)

        Returns:
            ChatResponse from LLM
        """
        client = await self.get_client()
        
        # Track timing for analytics
        start_time = time.perf_counter()
        logger.debug(f"Sending chat request with {len(messages)} messages, {len(tools) if tools else 0} tools")
        
        # #region debug
        from ..logging_config import debug_log
        debug_log("LLMRouter", "Sending chat request", {
            "message_count": len(messages),
            "tool_count": len(tools) if tools else 0,
            "tool_choice": str(tool_choice),
            "backend": self.active_backend,
            "model": self.active_model,
        })
        # #endregion
        
        try:
            response = await client.chat(messages, tools, temperature, tool_choice=tool_choice)
        except Exception as e:
            logger.error(f"LLM chat failed: {e}")
            raise
            
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"LLM response received in {duration_ms}ms, has_tool_calls={response.has_tool_calls}")
        
        # #region debug
        debug_log("LLMRouter", "Response received", {
            "has_tool_calls": response.has_tool_calls,
            "tool_call_count": len(response.message.tool_calls) if response.message.tool_calls else 0,
            "content_length": len(response.content) if response.content else 0,
            "duration_ms": duration_ms,
            "finish_reason": response.finish_reason,
        })
        # #endregion
        
        # Record in analytics if available
        if self._analytics:
            prompt_tokens = 0
            completion_tokens = 0
            if response.usage:
                prompt_tokens = response.usage.get("prompt_tokens", 0)
                completion_tokens = response.usage.get("completion_tokens", 0)
            
            self._analytics.record_llm_call(
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_name=client.model_name,
            )
        
        return response

    async def is_available(self) -> dict[str, bool]:
        """Check availability of all backends."""
        ollama_available = await self.ollama.is_available()
        openai_available = (
            await self.openai.is_available() if self.openai else False
        )

        return {
            "ollama": ollama_available,
            "openai": openai_available,
        }

    @property
    def active_model(self) -> str | None:
        """Get the name of the active model."""
        if self._active:
            return self._active.model_name
        return None

    @property
    def active_backend(self) -> str | None:
        """Get the name of the active backend."""
        if self._active is None:
            return None
        if self._active == self._ollama:
            return "ollama"
        if self._active == self._openai:
            return "openai"
        return None

    @property
    def had_fallback(self) -> bool:
        """Check if a fallback occurred."""
        return self._had_fallback

    async def close(self):
        """Close all clients."""
        if self._ollama:
            await self._ollama.close()
        if self._openai:
            await self._openai.close()

