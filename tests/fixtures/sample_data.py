"""
Sample test data for TechTim(e) tests.

This module provides factory functions for creating test data objects.
"""
from typing import Any


def create_sample_user_messages() -> list[str]:
    """Get a list of sample user messages for testing."""
    return [
        "My WiFi isn't working",
        "I can't connect to the internet",
        "DNS resolution is failing",
        "My network adapter is disabled",
        "VPN connection keeps dropping",
    ]


def create_sample_tool_definitions() -> list[dict[str, Any]]:
    """Get sample tool definitions for testing."""
    return [
        {
            "name": "ping_gateway",
            "description": "Ping the default gateway to check connectivity",
            "parameters": [],
        },
        {
            "name": "check_dns",
            "description": "Check DNS resolution",
            "parameters": [
                {
                    "name": "hostname",
                    "type": "string",
                    "description": "Hostname to resolve",
                    "required": False,
                },
            ],
        },
        {
            "name": "get_network_info",
            "description": "Get network adapter information",
            "parameters": [],
        },
        {
            "name": "check_wifi_status",
            "description": "Check WiFi adapter status",
            "parameters": [],
        },
        {
            "name": "restart_adapter",
            "description": "Restart a network adapter",
            "parameters": [
                {
                    "name": "adapter_name",
                    "type": "string",
                    "description": "Name of the adapter to restart",
                    "required": True,
                },
            ],
        },
    ]


def create_sample_session_id() -> str:
    """Get a sample session ID for testing."""
    return "test-session-12345"


def create_sample_tool_results() -> list[dict[str, Any]]:
    """Get sample tool execution results for testing."""
    return [
        {
            "tool_call_id": "call_001",
            "name": "ping_gateway",
            "success": True,
            "content": "Gateway 192.168.1.1 is reachable (latency: 2ms)",
        },
        {
            "tool_call_id": "call_002",
            "name": "check_dns",
            "success": True,
            "content": "DNS resolution successful: google.com -> 142.250.80.46",
        },
        {
            "tool_call_id": "call_003",
            "name": "restart_adapter",
            "success": False,
            "content": "Error: Adapter 'WiFi' not found",
        },
    ]


def create_sample_analytics_session() -> dict[str, Any]:
    """Get sample analytics session data for testing."""
    return {
        "session_id": "analytics-session-001",
        "start_time": "2024-01-15T10:00:00Z",
        "end_time": "2024-01-15T10:15:00Z",
        "message_count": 5,
        "tool_calls": 3,
        "resolved": True,
        "backend": "ollama",
        "model": "mistral:7b-instruct",
    }

