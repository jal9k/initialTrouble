"""OpenAI LLM client implementation."""

import json
from typing import Any

from openai import AsyncOpenAI

from ..tools.schemas import ToolCall, ToolDefinition
from .base import BaseLLMClient, ChatMessage, ChatResponse


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize OpenAI client."""
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        """Send chat completion request to OpenAI."""
        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_msg: dict[str, Any] = {
                "role": msg.role,
            }

            if msg.content is not None:
                openai_msg["content"] = msg.content

            # Handle tool calls from assistant
            if msg.tool_calls:
                openai_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]

            # Handle tool response
            if msg.role == "tool":
                openai_msg["tool_call_id"] = msg.tool_call_id
                openai_msg["name"] = msg.name

            openai_messages.append(openai_msg)

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature,
        }

        # Add tools if provided
        if tools:
            kwargs["tools"] = [t.to_openai_schema() for t in tools]
            kwargs["tool_choice"] = "auto"

        # Make request
        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        # Parse tool calls if present
        tool_calls = None
        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args) if args else {}

                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args,
                    )
                )

        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=message.content,
                tool_calls=tool_calls,
            ),
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    async def is_available(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            # Simple models list check
            models = await self._client.models.list()
            return True
        except Exception:
            return False

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.model

    async def close(self):
        """Close the client."""
        await self._client.close()

