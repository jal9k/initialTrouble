"""LLM router for managing multiple backends."""

from typing import Literal

from ..config import Settings, get_settings
from ..tools.schemas import ToolDefinition
from .base import BaseLLMClient, ChatMessage, ChatResponse
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient


class LLMRouter:
    """Router for managing LLM backends with fallback support."""

    def __init__(
        self,
        settings: Settings | None = None,
        prefer: Literal["ollama", "openai"] | None = None,
    ):
        """
        Initialize LLM router.

        Args:
            settings: Application settings (uses global if not provided)
            prefer: Preferred backend (overrides settings)
        """
        self.settings = settings or get_settings()
        self.preferred = prefer or self.settings.llm_backend

        self._ollama: OllamaClient | None = None
        self._openai: OpenAIClient | None = None
        self._active: BaseLLMClient | None = None

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
            if await self.ollama.is_available():
                self._active = self.ollama
                return self._active

            # Fallback to OpenAI
            if self.openai and await self.openai.is_available():
                self._active = self.openai
                return self._active

        else:  # Prefer OpenAI
            if self.openai and await self.openai.is_available():
                self._active = self.openai
                return self._active

            # Fallback to Ollama
            if await self.ollama.is_available():
                self._active = self.ollama
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
    ) -> ChatResponse:
        """
        Send chat completion request to best available backend.

        Args:
            messages: Conversation history
            tools: Available tools for function calling
            temperature: Sampling temperature

        Returns:
            ChatResponse from LLM
        """
        client = await self.get_client()
        return await client.chat(messages, tools, temperature)

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

    async def close(self):
        """Close all clients."""
        if self._ollama:
            await self._ollama.close()
        if self._openai:
            await self._openai.close()

