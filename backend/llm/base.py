"""Abstract base class for LLM clients."""

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..tools.schemas import ToolCall, ToolDefinition


class ChatMessage(BaseModel):
    """A message in a chat conversation."""

    role: Literal["system", "user", "assistant", "tool"] = Field(
        description="Role of the message sender"
    )
    content: str | None = Field(
        default=None,
        description="Message content",
    )
    tool_calls: list[ToolCall] | None = Field(
        default=None,
        description="Tool calls made by assistant",
    )
    tool_call_id: str | None = Field(
        default=None,
        description="ID of tool call this message responds to (for tool role)",
    )
    name: str | None = Field(
        default=None,
        description="Name of the tool (for tool role)",
    )


class ChatResponse(BaseModel):
    """Response from LLM chat completion."""

    message: ChatMessage = Field(description="Response message")
    finish_reason: str | None = Field(
        default=None,
        description="Why generation stopped",
    )
    usage: dict[str, int] | None = Field(
        default=None,
        description="Token usage statistics",
    )

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return bool(self.message.tool_calls)

    @property
    def content(self) -> str:
        """Get message content."""
        return self.message.content or ""


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        """
        Send a chat completion request.

        Args:
            messages: Conversation history
            tools: Available tools for function calling
            temperature: Sampling temperature

        Returns:
            ChatResponse with LLM's response
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM backend is available."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name being used."""
        pass

