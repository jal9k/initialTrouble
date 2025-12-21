"""Ollama LLM client implementation."""

import json
from typing import Any

import httpx

from ..tools.schemas import ToolCall, ToolDefinition
from .base import BaseLLMClient, ChatMessage, ChatResponse


class OllamaClient(BaseLLMClient):
    """Client for Ollama local LLM."""

    def __init__(self, host: str = "http://localhost:11434", model: str = "ministral:latest"):
        """Initialize Ollama client."""
        self.host = host.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=120.0)

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
    ) -> ChatResponse:
        """Send chat completion request to Ollama."""
        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            ollama_msg: dict[str, Any] = {
                "role": msg.role,
                "content": msg.content or "",
            }

            # Handle tool calls from assistant
            if msg.tool_calls:
                ollama_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,  # Ollama expects object, not JSON string
                        },
                    }
                    for tc in msg.tool_calls
                ]

            # Handle tool response
            if msg.role == "tool" and msg.tool_call_id:
                ollama_msg["tool_call_id"] = msg.tool_call_id

            ollama_messages.append(ollama_msg)

        # Build request payload
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        # Add tools if provided
        if tools:
            payload["tools"] = [t.to_ollama_schema() for t in tools]

        # Make request
        response = await self._client.post(
            f"{self.host}/api/chat",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        message_data = data.get("message", {})

        # Parse tool calls if present
        tool_calls = None
        if "tool_calls" in message_data:
            tool_calls = []
            for tc in message_data["tool_calls"]:
                func = tc.get("function", {})
                args = func.get("arguments", "{}")
                if isinstance(args, str):
                    args = json.loads(args)

                tool_calls.append(
                    ToolCall(
                        id=tc.get("id", f"call_{len(tool_calls)}"),
                        name=func.get("name", ""),
                        arguments=args,
                    )
                )

        return ChatResponse(
            message=ChatMessage(
                role=message_data.get("role", "assistant"),
                content=message_data.get("content"),
                tool_calls=tool_calls,
            ),
            finish_reason=data.get("done_reason"),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
        )

    async def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            response = await self._client.get(f"{self.host}/api/tags")
            if response.status_code != 200:
                return False

            # Check if our model is available
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return any(self.model in m or m in self.model for m in models)

        except Exception:
            return False

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.model

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

