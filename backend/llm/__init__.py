"""LLM client implementations.

Primary interface (Phase 8+):
- GlueLLMWrapper: Unified LLM interface with automatic tool execution
- registry_to_callables: Convert ToolRegistry to GlueLLM callables
- to_chat_service_response: Convert GlueLLM results to ChatServiceResponse

Deprecated (kept for rollback):
- BaseLLMClient, OllamaClient, OpenAIClient, LLMRouter
"""

from .base import BaseLLMClient, ChatMessage, ChatResponse
from .gluellm_wrapper import GlueLLMWrapper
from .tool_adapter import registry_to_callables
from .result_adapter import to_chat_service_response

# Deprecated - kept for rollback capability
from .ollama_client import OllamaClient
from .openai_client import OpenAIClient
from .router import LLMRouter

__all__ = [
    # Primary interface (Phase 8+)
    "ChatMessage",
    "ChatResponse",
    "GlueLLMWrapper",
    "registry_to_callables",
    "to_chat_service_response",
    # Deprecated (kept for rollback)
    "BaseLLMClient",
    "OllamaClient",
    "OpenAIClient",
    "LLMRouter",
]
