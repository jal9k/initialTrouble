"""Ollama LLM client implementation."""

import json
import time
from typing import Any

import httpx

from ..tools.schemas import ToolCall, ToolDefinition
from .base import BaseLLMClient, ChatMessage, ChatResponse

# #region agent log
def _ollama_dbg(loc: str, msg: str, data: dict, hyp: str = "OLLAMA"):
    with open("/Users/tyurgal/Documents/python/diag/network-diag/.cursor/debug.log", "a") as f:
        f.write(json.dumps({"location": loc, "message": msg, "data": data, "timestamp": int(time.time()*1000), "sessionId": "debug-session", "hypothesisId": hyp}) + "\n")
# #endregion


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
        tool_choice: str | dict | None = "auto",
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
            
            # #region agent log - H-A: Log full schema for ping_gateway
            for t in tools:
                if t.name == "ping_gateway":
                    schema = t.to_ollama_schema()
                    _ollama_dbg("ollama:ping_gateway_schema", "ping_gateway schema being sent", {"full_schema": schema, "parameters": [p.name for p in t.parameters]}, "H-A")
            # #endregion
            
            # #region debug
            # Workaround: Ollama doesn't fully support tool_choice, so inject instruction
            if tool_choice == "required":
                self._inject_force_tool_instruction(ollama_messages)
                # Update payload with modified messages
                payload["messages"] = ollama_messages
            elif isinstance(tool_choice, dict) and tool_choice.get("type") == "function":
                tool_name = tool_choice.get("function", {}).get("name")
                if tool_name:
                    self._inject_specific_tool_instruction(ollama_messages, tool_name)
                    payload["messages"] = ollama_messages
            # #endregion

        # #region agent log
        _ollama_dbg("ollama:chat:request", "Sending to Ollama", {"model": self.model, "msg_count": len(ollama_messages), "has_tools": tools is not None, "tool_count": len(tools) if tools else 0, "tool_names": [t.name for t in tools] if tools else [], "tool_choice": str(tool_choice)}, "H-OLLAMA")
        # #endregion

        # Make request
        response = await self._client.post(
            f"{self.host}/api/chat",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        message_data = data.get("message", {})
        # #region agent log
        _ollama_dbg("ollama:chat:response", "Ollama response received", {"has_tool_calls": "tool_calls" in message_data, "content_len": len(message_data.get("content", "")) if message_data.get("content") else 0, "done_reason": data.get("done_reason")}, "H-OLLAMA")
        if "tool_calls" in message_data:
            _ollama_dbg("ollama:chat:tool_calls", "Tool calls in response", {"tool_calls": message_data["tool_calls"]}, "H-OLLAMA")
        # #endregion

        # Parse tool calls if present
        tool_calls = None
        if "tool_calls" in message_data:
            tool_calls = []
            for tc in message_data["tool_calls"]:
                func = tc.get("function", {})
                args = func.get("arguments", "{}")
                if isinstance(args, str):
                    args = json.loads(args)

                # #region agent log - H-B: Log raw tool call from LLM for ping_gateway
                if func.get("name") == "ping_gateway":
                    _ollama_dbg("ollama:ping_gateway_call", "ping_gateway called by LLM", {"raw_args": args, "arg_keys": list(args.keys()) if isinstance(args, dict) else "not_dict"}, "H-B")
                # #endregion

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

    # #region debug
    def _inject_force_tool_instruction(self, messages: list[dict]) -> None:
        """
        Inject instruction to force tool calling (Ollama workaround).
        
        Ollama doesn't fully support tool_choice="required", so we append
        an instruction to the last user message to encourage tool usage.
        """
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                original = messages[i].get("content", "")
                messages[i]["content"] = (
                    f"{original}\n\n"
                    "[INSTRUCTION: You MUST respond with a tool call. "
                    "Do not write any text explanation. Only output a tool call.]"
                )
                break

    def _inject_specific_tool_instruction(self, messages: list[dict], tool_name: str) -> None:
        """
        Inject instruction to call a specific tool.
        
        Used when tool_choice specifies a particular function.
        """
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                original = messages[i].get("content", "")
                messages[i]["content"] = (
                    f"{original}\n\n"
                    f"[INSTRUCTION: You MUST call the {tool_name} tool. "
                    "Do not write any text. Only output the tool call.]"
                )
                break
    # #endregion

