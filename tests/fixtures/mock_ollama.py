"""
Mock Ollama server responses for testing.

This module provides predefined Ollama API responses that can be used
in tests without requiring a real Ollama instance.
"""
from typing import Any


class MockOllamaResponses:
    """Container for predefined Ollama API response data."""
    
    TAGS_RESPONSE: dict[str, Any] = {
        "models": [
            {
                "name": "mistral:7b-instruct",
                "size": 4_000_000_000,
                "modified_at": "2024-01-15T10:30:00Z",
                "digest": "abc123def456",
            },
            {
                "name": "llama2:7b",
                "size": 3_800_000_000,
                "modified_at": "2024-01-10T08:00:00Z",
                "digest": "def456abc123",
            },
        ]
    }
    
    PULL_PROGRESS_RESPONSES: list[dict[str, Any]] = [
        {"status": "pulling manifest"},
        {"status": "downloading", "completed": 1000, "total": 4000},
        {"status": "downloading", "completed": 2000, "total": 4000},
        {"status": "downloading", "completed": 4000, "total": 4000},
        {"status": "success"},
    ]
    
    CHAT_RESPONSE: dict[str, Any] = {
        "model": "mistral:7b-instruct",
        "created_at": "2024-01-15T10:30:00Z",
        "message": {
            "role": "assistant",
            "content": "I can help you diagnose that network issue.",
        },
        "done": True,
        "total_duration": 1_500_000_000,
        "prompt_eval_count": 50,
        "eval_count": 30,
    }
    
    CHAT_RESPONSE_WITH_TOOLS: dict[str, Any] = {
        "model": "mistral:7b-instruct",
        "created_at": "2024-01-15T10:30:00Z",
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "ping_gateway",
                        "arguments": "{}",
                    },
                },
            ],
        },
        "done": True,
    }
    
    HEALTH_OK: dict[str, str] = {"status": "ok"}
    
    VERSION_RESPONSE: dict[str, str] = {"version": "0.5.4"}

