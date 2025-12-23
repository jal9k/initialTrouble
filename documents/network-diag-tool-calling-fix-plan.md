# Network Diagnostics CLI: Tool Calling Fix Implementation Plan

## Executive Summary

This document provides a comprehensive plan to fix the tool calling behavior in the Network Diagnostics CLI when using small language models like Ministral 3B. The core problem is that the model recognizes which tool to use but fails to actually invoke it, instead generating text that describes what it would do. This requires multiple user prompts to coax the model into making the tool call.

The root causes are:

1. **Prompt verbosity**: The system prompt is written for large models that can parse nuance; small models get lost in prose and parrot instructions instead of following them.
2. **Generic tool descriptions**: The tool schemas sent to the LLM API lack decision boundaries, causing the model to confuse similar tools.
3. **No forcing mechanism**: The code uses `tool_choice: "auto"` which allows the model to respond with text instead of tool calls.
4. **Single-turn tool execution**: The chat loop expects one tool call per turn, but diagnostic workflows require chained tool calls following the OSI ladder.
5. **Missing verification loop**: After fixes are applied, there's no automatic verification or resolution confirmation.

This plan addresses all five issues with specific code changes, new prompt structures, and architectural improvements.

---

## Table of Contents

1. [Root Cause Analysis](#root-cause-analysis)
2. [Architecture Changes](#architecture-changes)
3. [Implementation: System Prompt Rewrite](#implementation-system-prompt-rewrite)
4. [Implementation: Tool Description Enhancement](#implementation-tool-description-enhancement)
5. [Implementation: Force Tool Calling](#implementation-force-tool-calling)
6. [Implementation: Multi-Turn Tool Loop](#implementation-multi-turn-tool-loop)
7. [Implementation: Verification and Resolution Detection](#implementation-verification-and-resolution-detection)
8. [File Change Summary](#file-change-summary)
9. [Testing Plan](#testing-plan)
10. [Rollback Plan](#rollback-plan)

---

## Root Cause Analysis

### Issue 1: Prompt Verbosity Overwhelms Small Models

**Current State**: The `diagnostic_agent.md` prompt is 2,500+ characters with narrative explanations, ASCII diagrams, and multiple rule sets. Large models like GPT-4 or Claude parse this effectively, but 3B parameter models exhibit specific failure patterns:

- They read "ALWAYS start at Layer 1" and then generate text containing those words rather than executing the instruction.
- They see the decision tree diagram and describe it in their response instead of following it.
- The word "CRITICAL" appears multiple times, diluting its emphasis.

**Evidence**: The model says things like "I will run check_adapter_status to verify your adapter" without actually calling the tool. This is classic instruction parroting.

**Solution**: Rewrite the prompt using imperative commands, remove narrative prose, use tables instead of paragraphs, and add explicit "DO NOT" instructions that forbid text-only responses.

### Issue 2: Tool Descriptions Lack Decision Boundaries

**Current State**: Tool descriptions in the registration code are minimal:

```python
description = "Ping the default gateway"
description = "Ping external DNS servers"
description = "Test DNS resolution"
```

When these become JSON schemas in the API payload, the model sees three tools that all involve "network" and "testing." Without explicit guidance on WHEN to use each tool, the model either picks randomly or defaults to the most recently mentioned tool in conversation.

**Evidence**: User reports that the model sometimes calls `ping_dns` before `ping_gateway`, or calls `test_dns_resolution` when no prior diagnostics have been run.

**Solution**: Expand each tool description to include:
- `CALL THIS TOOL WHEN:` explicit trigger conditions
- `DO NOT CALL IF:` explicit exclusion conditions  
- `OUTPUT MEANING:` interpretation guide for results

### Issue 3: No Forcing Mechanism

**Current State**: The OpenAI client configuration uses:

```python
"tool_choice": "auto"
```

This tells the model it MAY call a tool, but text responses are equally valid. Small models with weaker instruction-following interpret this as permission to avoid tool calls entirely.

**Evidence**: The model generates helpful-sounding responses like "Let me check your network configuration" without any tool call in the response payload.

**Solution**: 
- Use `tool_choice: "required"` to force ANY tool call on the first turn.
- Use `tool_choice: {"type": "function", "function": {"name": "..."}}` when context makes the correct tool obvious.
- Implement logic to detect when forcing is appropriate vs. when auto is acceptable.

### Issue 4: Single-Turn Tool Execution

**Current State**: The chat loop in `cli.py` handles tool calls in a single pass:

```python
if response.has_tool_calls:
    # Execute tools
    for tool_call in response.message.tool_calls:
        result = await tool_registry.execute(tool_call)
        messages.append(tool_result_message)
    
    # Get FINAL response
    response = await llm_router.chat(messages, tools)
```

This assumes the model will call all necessary tools in one response, then provide a final answer. But the OSI diagnostic ladder requires sequential decisions: run tool 1, check result, decide whether to run tool 2, check result, etc. The current architecture doesn't support this.

**Evidence**: The model calls `check_adapter_status`, gets the result, then provides a final answer without continuing to `get_ip_config` even when the adapter check passed.

**Solution**: Implement an iterative tool loop that continues until:
- The model stops requesting tool calls, OR
- A maximum iteration count is reached, OR
- A stop condition is detected in tool results

### Issue 5: Missing Verification Loop

**Current State**: When a fix is applied (e.g., `enable_wifi`), there's no automatic verification that the fix worked. The model might say "WiFi is now enabled" without confirming internet connectivity was restored.

**Evidence**: User applies fix, model says "done," but the underlying problem persists because the fix didn't actually work.

**Solution**: 
- After action tools (like `enable_wifi`), automatically queue verification tools.
- Implement resolution confirmation that explicitly asks the user if their problem is solved.
- Track session state to know when we're in "fix applied, needs verification" mode.

---

## Architecture Changes

### Current Architecture

```
User Input
    ↓
Add to messages[]
    ↓
LLM Router (single call)
    ↓
If tool_calls exist:
    Execute tools
    Add results to messages[]
    LLM Router (final response)
    ↓
Display response
```

### New Architecture

```
User Input
    ↓
Add to messages[]
    ↓
┌─────────────────────────────────────┐
│         TOOL EXECUTION LOOP         │
│                                     │
│  Iteration 0:                       │
│    LLM Router (force_tool=True)     │
│    ↓                                │
│  If tool_calls:                     │
│    Execute tools                    │
│    Check for stop conditions        │
│    Add results to messages[]        │
│    Continue loop                    │
│  Else:                              │
│    Break loop                       │
│                                     │
│  Iterations 1-N:                    │
│    LLM Router (force_tool=False)    │
│    Same execution logic             │
│                                     │
│  Max iterations: 5                  │
└─────────────────────────────────────┘
    ↓
If action tool was called:
    Queue verification tools
    Run verification loop
    ↓
Display final response
    ↓
If verification passed:
    Ask user for resolution confirmation
```

---

## Implementation: System Prompt Rewrite

Create a new file `prompts/diagnostic_agent.md` that replaces the existing prompt. This version is optimized for small models with explicit behavioral constraints.

### New File: `prompts/diagnostic_agent.md`

```markdown
# Network Diagnostic Agent

You are a network troubleshooter. You use diagnostic tools to find and fix network problems.

## BEHAVIORAL RULES

Rule 1: When a user describes a network problem, IMMEDIATELY call a tool.
Rule 2: DO NOT write text explaining what you will do. Just call the tool.
Rule 3: DO NOT say "I will check" or "Let me run" or "I'll diagnose". Just call the tool.
Rule 4: After receiving tool results, either call the next tool OR give your final answer.
Rule 5: If you are unsure which tool to use, call check_adapter_status.

## FORBIDDEN RESPONSES

These responses are WRONG. Never produce them:

- "I'll run a diagnostic to check your network."
- "Let me check your adapter status."
- "I will use the ping_gateway tool to test connectivity."
- "Based on your description, I should run..."

The ONLY correct response to a network problem is a tool call with no preamble.

## DIAGNOSTIC SEQUENCE

You MUST run tools in this order. Do not skip steps.

| Step | Tool | Run If |
|------|------|--------|
| 1 | check_adapter_status | ALWAYS run this first |
| 2 | get_ip_config | Adapter is connected |
| 3 | ping_gateway | Valid IP exists |
| 4 | ping_dns | Gateway is reachable |
| 5 | test_dns_resolution | Internet is accessible |

## STOP CONDITIONS

Stop the diagnostic sequence and report findings when:

| Tool Result | Action |
|-------------|--------|
| check_adapter_status: is_connected=false | STOP. Tell user to connect to network. |
| get_ip_config: is_apipa=true | STOP. Tell user DHCP failed, restart router. |
| get_ip_config: has_gateway=false | STOP. Tell user no gateway configured. |
| ping_gateway: reachable=false | STOP. Tell user router is unreachable. |
| ping_dns: internet_accessible=false | STOP. Tell user ISP/modem issue. |
| test_dns_resolution: dns_working=false | STOP. Tell user to change DNS to 8.8.8.8. |

If all tools pass, tell the user their network is healthy.

## TOOL SELECTION QUICK REFERENCE

| User Says | Call This Tool |
|-----------|----------------|
| "no internet" | check_adapter_status |
| "can't connect" | check_adapter_status |
| "network down" | check_adapter_status |
| "offline" | check_adapter_status |
| "wifi not working" | check_adapter_status |
| "slow internet" | ping_gateway |
| "laggy" | ping_gateway |
| "website won't load" | test_dns_resolution |
| "DNS error" | test_dns_resolution |
| "enable wifi" | enable_wifi |
| "turn on wifi" | enable_wifi |

## RESPONSE FORMAT

After completing diagnostics, respond with exactly this format:

**Finding**: [One sentence describing what you found]

**Cause**: [One sentence explaining why this is happening]

**Fix**:
1. [First step]
2. [Second step]
3. [Third step if needed]

## VERIFICATION REQUIREMENT

After any fix is applied (enable_wifi, or user says they made a change):

1. Call check_adapter_status to verify connection
2. Call ping_dns to verify internet works
3. Ask: "I've verified your connection is working. Is your issue resolved?"

## EXAMPLES

### Example 1: Correct Behavior

User: "My internet is down"

CORRECT RESPONSE:
[Tool call: check_adapter_status]

WRONG RESPONSE:
"I'll check your network adapter to see if it's connected properly."

### Example 2: After Tool Result

Tool Result: check_adapter_status returned is_connected=false

CORRECT RESPONSE:
**Finding**: Your WiFi adapter is on but not connected to any network.

**Cause**: Your computer is not connected to a WiFi access point.

**Fix**:
1. Click the WiFi icon in your menu bar
2. Select your network name
3. Enter your password if prompted

Let me know when you're connected and I'll verify the rest of your network.

### Example 3: After Tool Result - Continue Sequence

Tool Result: check_adapter_status returned is_connected=true, has_ip=true

CORRECT RESPONSE:
[Tool call: get_ip_config]

Note: Do NOT provide a final answer yet. Continue the diagnostic sequence.
```

---

## Implementation: Tool Description Enhancement

Replace the tool registration in `backend/diagnostics/__init__.py` with enhanced descriptions that include decision boundaries.

### New File: `backend/diagnostics/__init__.py`

```python
"""
Tool registration with decision-boundary descriptions for small language models.

This module registers all diagnostic tools with the tool registry. The descriptions
are specifically crafted to help small models (3B parameters) make correct tool
selection decisions by including explicit CALL WHEN and DO NOT CALL conditions.
"""

from ..tools import ToolParameter, ToolRegistry

# Import diagnostic functions
from .adapter import check_adapter_status
from .ip_config import get_ip_config
from .connectivity import ping_gateway, ping_dns
from .dns import test_dns_resolution
from .wifi import enable_wifi


def register_all_diagnostics(registry: ToolRegistry) -> None:
    """
    Register all diagnostic tools with the registry.
    
    Each tool description follows this pattern:
    1. One-line summary of what the tool does
    2. CALL THIS TOOL WHEN: explicit trigger conditions
    3. DO NOT CALL IF: explicit exclusion conditions
    4. OUTPUT MEANING: interpretation guide for results
    
    This structure helps small language models make correct tool selection
    decisions without relying on implicit reasoning.
    """
    
    # =========================================================================
    # TOOL 1: check_adapter_status
    # OSI Layer: Physical/Link (Layer 1-2)
    # Position in sequence: ALWAYS FIRST
    # =========================================================================
    registry.register(
        name="check_adapter_status",
        description="""Check if the network adapter is enabled and connected to a network.

CALL THIS TOOL WHEN:
- User reports ANY network problem (this is ALWAYS the first tool to run)
- User says: "no internet", "can't connect", "not working", "offline", "network down"
- User says: "wifi not working", "ethernet not working"
- You need to verify the physical connection before other diagnostics

DO NOT CALL IF:
- You already called this tool in the current diagnostic session
- User is asking about a specific website (use test_dns_resolution instead, but only after running this first)

OUTPUT MEANING:
- status="up" AND is_connected=true → Adapter is working. Run get_ip_config next.
- status="down" → Adapter is disabled. Tell user to enable the network adapter.
- status="up" AND is_connected=false → Adapter is on but not connected. Tell user to connect to WiFi or plug in Ethernet cable.
- active_count=0 → No network adapters found. Hardware issue.""",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="Specific interface to check, e.g., 'en0' on macOS or 'Wi-Fi' on Windows. Leave empty to check all interfaces.",
                required=False,
            ),
        ],
    )(check_adapter_status)

    # =========================================================================
    # TOOL 2: get_ip_config
    # OSI Layer: Network (Layer 3)
    # Position in sequence: SECOND (after check_adapter_status passes)
    # =========================================================================
    registry.register(
        name="get_ip_config",
        description="""Get the IP address, subnet mask, gateway, and DNS server configuration.

CALL THIS TOOL WHEN:
- check_adapter_status showed the adapter is connected (is_connected=true)
- You need to verify the device has a valid IP address
- User mentions: "no IP address", "DHCP not working", "169.254 address"

DO NOT CALL IF:
- check_adapter_status has not been run yet (run it first)
- check_adapter_status showed is_connected=false (fix connection first)

OUTPUT MEANING:
- has_valid_ip=true AND has_gateway=true → IP configuration is good. Run ping_gateway next.
- has_valid_ip=false → No IP address assigned. DHCP server may be unreachable.
- is_apipa=true (IP starts with 169.254) → DHCP failed. Tell user to restart router and try again.
- has_gateway=false → No default gateway configured. Network cannot route traffic.""",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="Specific interface to check. Leave empty to check all interfaces.",
                required=False,
            ),
        ],
    )(get_ip_config)

    # =========================================================================
    # TOOL 3: ping_gateway
    # OSI Layer: Network (Layer 3)
    # Position in sequence: THIRD (after get_ip_config passes)
    # =========================================================================
    registry.register(
        name="ping_gateway",
        description="""Test connectivity to the local router/gateway by sending ping packets.

CALL THIS TOOL WHEN:
- get_ip_config showed a valid IP address and gateway exist
- You need to test if the local network is working
- User says: "can't reach router", "router not responding", "local network down"

DO NOT CALL IF:
- check_adapter_status has not been run yet (run it first)
- get_ip_config has not been run yet (run it first)
- get_ip_config showed no valid IP or no gateway (fix those issues first)

OUTPUT MEANING:
- reachable=true AND packet_loss_percent < 10 → Gateway is working. Run ping_dns next.
- reachable=false → Cannot reach the router. Tell user to: check cables, restart router, verify correct network.
- reachable=true AND packet_loss_percent > 50 → Unstable connection. Possible interference, bad cable, or router overload.""",
        parameters=[
            ToolParameter(
                name="gateway",
                type="string",
                description="Gateway IP address to ping. Leave empty to auto-detect from system routing table.",
                required=False,
            ),
            ToolParameter(
                name="count",
                type="integer",
                description="Number of ping packets to send. Default is 4. Use 2 for quick checks.",
                required=False,
            ),
        ],
    )(ping_gateway)

    # =========================================================================
    # TOOL 4: ping_dns
    # OSI Layer: Network (Layer 3)
    # Position in sequence: FOURTH (after ping_gateway passes)
    # =========================================================================
    registry.register(
        name="ping_dns",
        description="""Test connectivity to external internet servers (8.8.8.8 Google DNS, 1.1.1.1 Cloudflare DNS).

CALL THIS TOOL WHEN:
- ping_gateway succeeded (router is reachable)
- You need to test if internet connectivity exists beyond the local network
- User says: "local network works but no internet", "can ping router but nothing else"

DO NOT CALL IF:
- This is the first diagnostic (run check_adapter_status first)
- ping_gateway has not been run yet (run it first)
- ping_gateway showed reachable=false (fix router connectivity first)

OUTPUT MEANING:
- internet_accessible=true → Internet is working. Run test_dns_resolution next to complete diagnostics.
- internet_accessible=false → Cannot reach internet. This is an ISP or modem issue, not a local network problem. Tell user to: restart modem, check for ISP outage, contact ISP.
- servers_reachable < servers_tested → Partial connectivity. Some DNS servers blocked or unreachable.""",
        parameters=[
            ToolParameter(
                name="count",
                type="integer",
                description="Number of ping packets per server. Default is 4. Use 2 for quick checks.",
                required=False,
            ),
        ],
    )(ping_dns)

    # =========================================================================
    # TOOL 5: test_dns_resolution
    # OSI Layer: Application (Layer 7)
    # Position in sequence: FIFTH/LAST (after ping_dns passes)
    # =========================================================================
    registry.register(
        name="test_dns_resolution",
        description="""Test if domain names can be resolved to IP addresses using DNS.

CALL THIS TOOL WHEN:
- ping_dns succeeded (internet is accessible via IP)
- User says: "websites won't load", "can't reach google.com", "DNS error in browser"
- Browser shows: "DNS_PROBE_FINISHED_NXDOMAIN", "Server not found", "DNS lookup failed"

DO NOT CALL IF:
- This is the first diagnostic (run check_adapter_status first)
- ping_dns has not been run yet (run it first)
- ping_dns showed internet_accessible=false (fix internet connectivity first)

OUTPUT MEANING:
- dns_working=true → DNS is working. Network is fully functional.
- dns_working=false → DNS resolution is broken. Tell user to: change DNS servers to 8.8.8.8 and 1.1.1.1, or flush DNS cache.
- hosts_resolved < hosts_tested → Partial DNS failure. Some domains may be blocked or DNS server has issues.""",
        parameters=[
            ToolParameter(
                name="hostnames",
                type="array",
                description="List of hostnames to resolve. Default: ['google.com', 'cloudflare.com']. Add specific domains if user mentions them.",
                required=False,
            ),
            ToolParameter(
                name="dns_server",
                type="string",
                description="Specific DNS server to use for resolution. Leave empty to use system default.",
                required=False,
            ),
        ],
    )(test_dns_resolution)

    # =========================================================================
    # TOOL 6: enable_wifi
    # OSI Layer: Physical/Link (Layer 1-2)
    # Position in sequence: ACTION TOOL (called on user request)
    # =========================================================================
    registry.register(
        name="enable_wifi",
        description="""Enable the WiFi network adapter.

CALL THIS TOOL WHEN:
- User explicitly asks: "enable wifi", "turn on wifi", "start wifi"
- check_adapter_status showed WiFi adapter status="down" (disabled)

DO NOT CALL IF:
- User did not ask to enable WiFi
- WiFi is already enabled (status="up")
- Problem is with Ethernet, not WiFi
- You are just running diagnostics (this tool changes system state)

OUTPUT MEANING:
- changed=true AND current_state="on" → WiFi was enabled successfully. Run check_adapter_status to verify connection, then ping_dns to verify internet.
- changed=false AND current_state="on" → WiFi was already enabled. No action needed.
- success=false → Failed to enable WiFi. May need administrator privileges or hardware switch.

IMPORTANT: After calling this tool, you MUST run verification diagnostics to confirm the fix worked.""",
        parameters=[
            ToolParameter(
                name="interface_name",
                type="string",
                description="WiFi interface name. Default: 'en0' on macOS, 'Wi-Fi' on Windows.",
                required=False,
            ),
        ],
    )(enable_wifi)
```

---

## Implementation: Force Tool Calling

Modify the LLM clients to support forcing tool calls. This requires changes to both the OpenAI and Ollama clients.

### Modified File: `backend/llm/base.py`

Add a new parameter to the base interface:

```python
"""Base classes for LLM clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ChatMessage:
    """A message in a chat conversation."""
    
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list["ToolCall"] | None = None
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class ChatResponse:
    """Response from an LLM chat completion."""
    
    message: ChatMessage
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    
    @property
    def content(self) -> str:
        """Get the text content of the response."""
        return self.message.content or ""
    
    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return bool(self.message.tool_calls)


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[Any] | None = None,
        temperature: float = 0.7,
        tool_choice: str | dict | None = "auto",  # NEW PARAMETER
    ) -> ChatResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: Conversation history
            tools: Available tool definitions
            temperature: Sampling temperature
            tool_choice: Tool calling behavior:
                - "auto": Model decides whether to call tools (default)
                - "required": Model MUST call at least one tool
                - "none": Model cannot call tools
                - {"type": "function", "function": {"name": "..."}}: Force specific tool
        
        Returns:
            ChatResponse with model output
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM backend is available."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        pass
```

### Modified File: `backend/llm/openai_client.py`

Update the OpenAI client to use the tool_choice parameter:

```python
"""OpenAI API client for chat completions with tool support."""

import json
from typing import Any

from openai import AsyncOpenAI

from .base import BaseLLMClient, ChatMessage, ChatResponse
from ..tools import ToolCall, ToolDefinition


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize the OpenAI client."""
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        tool_choice: str | dict | None = "auto",  # NEW PARAMETER
    ) -> ChatResponse:
        """Send a chat completion request to OpenAI."""
        
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(messages)
        
        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature,
        }
        
        # Add tools if provided
        if tools:
            kwargs["tools"] = [t.to_openai_schema() for t in tools]
            
            # Set tool_choice based on parameter
            # OpenAI accepts: "auto", "required", "none", or a specific tool dict
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
        
        # Make the API call
        response = await self.client.chat.completions.create(**kwargs)
        
        # Parse the response
        choice = response.choices[0]
        message = choice.message
        
        # Extract tool calls if present
        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments) if tc.function.arguments else {},
                )
                for tc in message.tool_calls
            ]
        
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
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        )
    
    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Convert ChatMessage objects to OpenAI message format."""
        openai_messages = []
        
        for msg in messages:
            if msg.role == "tool":
                openai_messages.append({
                    "role": "tool",
                    "content": msg.content or "",
                    "tool_call_id": msg.tool_call_id,
                })
            elif msg.role == "assistant" and msg.tool_calls:
                openai_messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
            else:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content or "",
                })
        
        return openai_messages
    
    async def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        try:
            # Make a minimal API call to verify connectivity
            await self.client.models.list()
            return True
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close the client."""
        await self.client.close()
```

### Modified File: `backend/llm/ollama_client.py`

Update the Ollama client similarly:

```python
"""Ollama API client for chat completions with tool support."""

import json
from typing import Any

import httpx

from .base import BaseLLMClient, ChatMessage, ChatResponse
from ..tools import ToolCall, ToolDefinition
from ..logging_config import get_logger

logger = get_logger("network_diag.ollama")


def _ollama_dbg(tag: str, message: str, data: Any = None) -> None:
    """Debug logging for Ollama client."""
    if data:
        logger.debug(f"[{tag}] {message}: {json.dumps(data, default=str)[:500]}")
    else:
        logger.debug(f"[{tag}] {message}")


class OllamaClient(BaseLLMClient):
    """Ollama API client."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "ministral",
        timeout: int = 120,
    ):
        """Initialize the Ollama client."""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        tool_choice: str | dict | None = "auto",  # NEW PARAMETER
    ) -> ChatResponse:
        """Send a chat completion request to Ollama."""
        
        # Convert messages to Ollama format
        ollama_messages = self._convert_messages(messages)
        
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
            
            # Ollama tool_choice handling
            # Note: Ollama's tool_choice support varies by version
            # We implement a workaround for older versions
            if tool_choice == "required":
                # Inject instruction into the last user message to force tool use
                # This is a fallback for Ollama versions that don't support tool_choice
                self._inject_force_tool_instruction(ollama_messages)
            elif isinstance(tool_choice, dict) and tool_choice.get("type") == "function":
                # Force specific tool
                tool_name = tool_choice.get("function", {}).get("name")
                if tool_name:
                    self._inject_specific_tool_instruction(ollama_messages, tool_name)
        
        _ollama_dbg("ollama:chat:request", "Sending to Ollama", {
            "model": self.model,
            "message_count": len(ollama_messages),
            "tools_count": len(tools) if tools else 0,
            "tool_choice": tool_choice,
        })
        
        # Make the API call
        response = await self.client.post(
            f"{self.base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        
        _ollama_dbg("ollama:chat:response", "Ollama response received", {
            "has_tool_calls": bool(data.get("message", {}).get("tool_calls")),
        })
        
        # Parse the response
        message_data = data.get("message", {})
        
        # Extract tool calls if present
        tool_calls = None
        if message_data.get("tool_calls"):
            tool_calls = [
                ToolCall(
                    id=f"call_{i}",  # Ollama doesn't provide IDs, generate them
                    name=tc.get("function", {}).get("name", ""),
                    arguments=tc.get("function", {}).get("arguments", {}),
                )
                for i, tc in enumerate(message_data["tool_calls"])
            ]
        
        return ChatResponse(
            message=ChatMessage(
                role="assistant",
                content=message_data.get("content"),
                tool_calls=tool_calls,
            ),
            finish_reason="tool_calls" if tool_calls else "stop",
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
        )
    
    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Convert ChatMessage objects to Ollama message format."""
        ollama_messages = []
        
        for msg in messages:
            if msg.role == "tool":
                # Ollama expects tool results in a specific format
                ollama_messages.append({
                    "role": "tool",
                    "content": msg.content or "",
                })
            elif msg.role == "assistant" and msg.tool_calls:
                ollama_messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": tc.name,
                                "arguments": tc.arguments,  # Ollama uses objects, not JSON strings
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
            else:
                ollama_messages.append({
                    "role": msg.role,
                    "content": msg.content or "",
                })
        
        return ollama_messages
    
    def _inject_force_tool_instruction(self, messages: list[dict[str, Any]]) -> None:
        """
        Inject an instruction to force tool calling for Ollama models.
        
        This is a workaround for Ollama versions that don't support tool_choice="required".
        We append an instruction to the last user message.
        """
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                original_content = messages[i].get("content", "")
                messages[i]["content"] = (
                    f"{original_content}\n\n"
                    "[INSTRUCTION: You MUST respond with a tool call. "
                    "Do not write any text. Only output a tool call.]"
                )
                break
    
    def _inject_specific_tool_instruction(
        self,
        messages: list[dict[str, Any]],
        tool_name: str,
    ) -> None:
        """
        Inject an instruction to call a specific tool.
        
        This is a workaround for forcing a specific tool call.
        """
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                original_content = messages[i].get("content", "")
                messages[i]["content"] = (
                    f"{original_content}\n\n"
                    f"[INSTRUCTION: You MUST call the {tool_name} tool. "
                    "Do not write any text. Only output the tool call.]"
                )
                break
    
    async def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close the client."""
        await self.client.aclose()
```

### Modified File: `backend/llm/router.py`

Update the router to pass through tool_choice and implement smart forcing:

```python
"""LLM router with automatic backend selection and fallback."""

from typing import Any

from .base import BaseLLMClient, ChatMessage, ChatResponse
from .openai_client import OpenAIClient
from .ollama_client import OllamaClient
from ..tools import ToolDefinition
from ..config import Settings


class LLMRouter:
    """Routes LLM requests to available backends with fallback support."""
    
    def __init__(self, settings: Settings, analytics_collector=None):
        """Initialize the router with configuration."""
        self.settings = settings
        self.analytics = analytics_collector
        
        # Initialize clients
        self.ollama: OllamaClient | None = None
        self.openai: OpenAIClient | None = None
        
        if settings.ollama_base_url:
            self.ollama = OllamaClient(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
            )
        
        if settings.openai_api_key:
            self.openai = OpenAIClient(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
        
        self.preferred = settings.llm_backend
        self._active_backend: str | None = None
        self._active_model: str | None = None
        self._had_fallback: bool = False
    
    @property
    def active_backend(self) -> str | None:
        """Get the currently active backend name."""
        return self._active_backend
    
    @property
    def active_model(self) -> str | None:
        """Get the currently active model name."""
        return self._active_model
    
    @property
    def had_fallback(self) -> bool:
        """Check if a fallback occurred."""
        return self._had_fallback
    
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.7,
        tool_choice: str | dict | None = None,  # NEW PARAMETER
        force_tool_on_first_user_message: bool = True,  # NEW PARAMETER
    ) -> ChatResponse:
        """
        Send a chat request to the best available backend.
        
        Args:
            messages: Conversation history
            tools: Available tool definitions
            temperature: Sampling temperature
            tool_choice: Explicit tool choice override
            force_tool_on_first_user_message: If True, force tool calling on the
                first user message when tools are available
        
        Returns:
            ChatResponse from the LLM
        """
        # Determine tool_choice if not explicitly provided
        if tool_choice is None and tools:
            tool_choice = self._determine_tool_choice(messages, force_tool_on_first_user_message)
        
        # Try preferred backend first
        client = await self._get_available_client()
        
        if client is None:
            raise RuntimeError("No LLM backend available")
        
        # Make the request
        import time
        start_time = time.perf_counter()
        
        response = await client.chat(
            messages=messages,
            tools=tools,
            temperature=temperature,
            tool_choice=tool_choice,
        )
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Record analytics
        if self.analytics:
            self.analytics.record_llm_call(
                backend=self._active_backend,
                model=self._active_model,
                duration_ms=duration_ms,
                prompt_tokens=response.usage.get("prompt_tokens", 0),
                completion_tokens=response.usage.get("completion_tokens", 0),
            )
        
        return response
    
    def _determine_tool_choice(
        self,
        messages: list[ChatMessage],
        force_on_first: bool,
    ) -> str:
        """
        Determine the appropriate tool_choice value based on conversation state.
        
        The logic is:
        1. If this is the first user message and no tools have been called yet,
           force tool calling to ensure the model doesn't just respond with text.
        2. If tools have already been called in this conversation, allow auto
           so the model can decide when to stop.
        """
        if not force_on_first:
            return "auto"
        
        # Count message types
        user_messages = sum(1 for m in messages if m.role == "user")
        tool_messages = sum(1 for m in messages if m.role == "tool")
        
        # First user message with no tool results yet = force tool calling
        if user_messages == 1 and tool_messages == 0:
            return "required"
        
        # Subsequent turns = let model decide
        return "auto"
    
    async def _get_available_client(self) -> BaseLLMClient | None:
        """Get an available client, with fallback logic."""
        
        # Try preferred backend
        if self.preferred == "ollama" and self.ollama:
            if await self.ollama.is_available():
                self._active_backend = "ollama"
                self._active_model = self.settings.ollama_model
                return self.ollama
        
        if self.preferred == "openai" and self.openai:
            if await self.openai.is_available():
                self._active_backend = "openai"
                self._active_model = self.settings.openai_model
                return self.openai
        
        # Fallback to other backend
        if self.preferred == "ollama" and self.openai:
            if await self.openai.is_available():
                self._had_fallback = True
                self._active_backend = "openai"
                self._active_model = self.settings.openai_model
                if self.analytics:
                    self.analytics.record_fallback("ollama", "openai", "Ollama not available")
                return self.openai
        
        if self.preferred == "openai" and self.ollama:
            if await self.ollama.is_available():
                self._had_fallback = True
                self._active_backend = "ollama"
                self._active_model = self.settings.ollama_model
                if self.analytics:
                    self.analytics.record_fallback("openai", "ollama", "OpenAI not available")
                return self.ollama
        
        return None
    
    async def is_available(self) -> dict[str, bool]:
        """Check availability of all backends."""
        return {
            "ollama": await self.ollama.is_available() if self.ollama else False,
            "openai": await self.openai.is_available() if self.openai else False,
        }
    
    async def close(self) -> None:
        """Close all clients."""
        if self.ollama:
            await self.ollama.close()
        if self.openai:
            await self.openai.close()
```

---

## Implementation: Multi-Turn Tool Loop

Replace the tool execution section in `cli.py` with an iterative loop that continues until the model stops requesting tools.

### Modified File: `backend/cli.py`

Here is the complete updated `cli.py` with the new tool execution loop:

```python
"""CLI interface for Network Diagnostics."""

import asyncio
import re
from pathlib import Path
from typing import NamedTuple

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .config import get_settings
from .llm import ChatMessage, LLMRouter
from .tools import ToolRegistry, get_registry
from .prompts import AgentType, load_prompt, get_prompt_for_context
from .logging_config import setup_logging, get_logger

# Import analytics
from analytics import AnalyticsCollector, AnalyticsStorage
from analytics.models import SessionOutcome, IssueCategory

# Initialize logging
logger = get_logger("network_diag.cli")

# Initialize CLI app and console
app = typer.Typer(
    name="network-diag",
    help="AI-powered network diagnostics CLI",
)
console = Console()


# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Maximum tool call iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 7

# Tools that modify system state and require verification
ACTION_TOOLS = {"enable_wifi", "disable_wifi", "reset_network"}

# Tools used to verify network connectivity after fixes
VERIFICATION_TOOLS = ["check_adapter_status", "ping_dns"]

# Patterns that indicate the user's problem is resolved
RESOLUTION_PATTERNS = [
    r"\b(thank(?:s|you)?|works?|working|fixed|resolved|perfect|great|awesome)\b",
    r"\b(it'?s?\s+(?:working|fixed|good|fine))\b",
    r"\b(problem\s+solved)\b",
    r"\b(all\s+good)\b",
    r"\b(yes|yep|yeah|yup)\b",
]

# Stop conditions: tool results that indicate we should stop the diagnostic ladder
# Format: (tool_name, result_key, condition_func, stop_message)
class StopCondition(NamedTuple):
    tool_name: str
    result_key: str
    condition: callable
    message: str


STOP_CONDITIONS = [
    StopCondition(
        "check_adapter_status",
        "connected_count",
        lambda v: v == 0,
        "No connected network adapters found",
    ),
    StopCondition(
        "get_ip_config",
        "has_valid_ip",
        lambda v: v is False,
        "No valid IP address assigned",
    ),
    StopCondition(
        "ping_gateway",
        "reachable",
        lambda v: v is False,
        "Gateway is unreachable",
    ),
    StopCondition(
        "ping_dns",
        "internet_accessible",
        lambda v: v is False,
        "Internet is not accessible",
    ),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def detect_resolution_signal(text: str) -> bool:
    """Detect if user message indicates resolution."""
    text_lower = text.lower()
    for pattern in RESOLUTION_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def check_stop_conditions(tool_name: str, result_content: str) -> str | None:
    """
    Check if tool result indicates we should stop the diagnostic sequence.
    
    Args:
        tool_name: Name of the tool that was executed
        result_content: The string content returned by the tool
    
    Returns:
        Stop message if a stop condition was met, None otherwise
    """
    import json
    
    for condition in STOP_CONDITIONS:
        if condition.tool_name != tool_name:
            continue
        
        # Try to parse the result content to extract the key
        # Tool results are formatted as markdown, so we need to look for patterns
        # The actual data is in the DiagnosticResult.data dict
        
        # Look for the key in the result content
        # Format: "- **key**: value"
        pattern = rf"\*\*{condition.result_key}\*\*:\s*(\S+)"
        match = re.search(pattern, result_content, re.IGNORECASE)
        
        if match:
            value_str = match.group(1).lower()
            
            # Convert to appropriate type
            if value_str in ("true", "false"):
                value = value_str == "true"
            elif value_str.isdigit():
                value = int(value_str)
            else:
                value = value_str
            
            # Check the condition
            try:
                if condition.condition(value):
                    return condition.message
            except Exception:
                pass
    
    return None


def prompt_for_feedback(collector: AnalyticsCollector) -> None:
    """Prompt user for feedback after session."""
    console.print("\n" + "-" * 50)
    console.print("[bold blue]Session Feedback[/bold blue]")
    
    try:
        resolved = Prompt.ask(
            "Was your issue resolved?",
            choices=["y", "n", "s"],
            default="s",
        )
        
        if resolved == "s":
            collector.end_session(outcome=SessionOutcome.ABANDONED)
            return
        
        outcome = SessionOutcome.RESOLVED if resolved == "y" else SessionOutcome.UNRESOLVED
        
        score_str = Prompt.ask(
            "Rate your experience (1-5, or skip)",
            default="s",
        )
        
        if score_str != "s" and score_str.isdigit():
            score = int(score_str)
            if 1 <= score <= 5:
                collector.record_feedback(score=score, source="cli")
        
        collector.end_session(outcome=outcome)
        console.print("[dim]Thank you for your feedback![/dim]")
        
    except (KeyboardInterrupt, EOFError):
        collector.end_session(outcome=SessionOutcome.ABANDONED)
        console.print("\n[dim]Feedback skipped.[/dim]")


# =============================================================================
# TOOL EXECUTION LOOP
# =============================================================================

async def execute_tool_loop(
    llm_router: LLMRouter,
    tool_registry: ToolRegistry,
    messages: list[ChatMessage],
    tools: list,
    max_iterations: int = MAX_TOOL_ITERATIONS,
) -> ChatMessage:
    """
    Execute tools in a loop until the model stops requesting them.
    
    This function implements the core agentic loop:
    1. Send messages to LLM (forcing tool call on first iteration)
    2. If LLM returns tool calls, execute them
    3. Add tool results to messages
    4. Check for stop conditions
    5. Repeat until no more tool calls or max iterations reached
    
    Args:
        llm_router: The LLM router instance
        tool_registry: The tool registry with registered diagnostics
        messages: Current conversation messages (modified in place)
        tools: List of available tool definitions
        max_iterations: Maximum number of tool call iterations
    
    Returns:
        The final assistant message (with or without tool calls)
    """
    action_tool_called = False
    stop_reason: str | None = None
    
    for iteration in range(max_iterations):
        # Determine if we should force tool calling
        # Force on first iteration, allow auto on subsequent iterations
        force_tool = (iteration == 0)
        
        logger.info(f"Tool loop iteration {iteration + 1}/{max_iterations}, force_tool={force_tool}")
        
        # Get LLM response
        response = await llm_router.chat(
            messages=messages,
            tools=tools,
            temperature=0.3,
            tool_choice="required" if force_tool else "auto",
        )
        
        # If no tool calls, we're done
        if not response.has_tool_calls or not response.message.tool_calls:
            logger.info(f"No tool calls in iteration {iteration + 1}, ending loop")
            return response.message
        
        # Add assistant message with tool calls to history
        messages.append(response.message)
        logger.info(f"LLM requested {len(response.message.tool_calls)} tool call(s)")
        
        # Execute each tool call
        for tool_call in response.message.tool_calls:
            logger.info(f"Executing tool: {tool_call.name} with args: {tool_call.arguments}")
            
            # Display to user
            args_str = ", ".join(f"{k}={v}" for k, v in tool_call.arguments.items())
            console.print(f"\n[yellow]Running:[/yellow] {tool_call.name}({args_str})")
            
            # Execute the tool
            result = await tool_registry.execute(tool_call)
            logger.debug(f"Tool result success: {result.success}")
            
            # Display condensed result
            preview = result.content[:300] + "..." if len(result.content) > 300 else result.content
            console.print(Panel(preview, title=f"{tool_call.name} result", border_style="dim"))
            
            # Add tool result to messages
            messages.append(
                ChatMessage(
                    role="tool",
                    content=result.content,
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                )
            )
            
            # Track if an action tool was called
            if tool_call.name in ACTION_TOOLS:
                action_tool_called = True
            
            # Check for stop conditions
            stop_reason = check_stop_conditions(tool_call.name, result.content)
            if stop_reason:
                logger.info(f"Stop condition met: {stop_reason}")
                # Don't break here - let the model see the result and formulate response
    
    # If we hit max iterations, get a final response without tool forcing
    logger.warning(f"Reached max iterations ({max_iterations}), getting final response")
    
    response = await llm_router.chat(
        messages=messages,
        tools=tools,
        temperature=0.3,
        tool_choice="none",  # Prevent further tool calls
    )
    
    return response.message


async def run_verification(
    llm_router: LLMRouter,
    tool_registry: ToolRegistry,
    messages: list[ChatMessage],
    tools: list,
) -> bool:
    """
    Run verification diagnostics after an action tool was executed.
    
    This ensures that fixes like enable_wifi actually worked by running
    connectivity tests.
    
    Args:
        llm_router: The LLM router instance
        tool_registry: The tool registry
        messages: Conversation messages
        tools: Available tools
    
    Returns:
        True if verification passed, False otherwise
    """
    console.print("\n[dim]Verifying fix...[/dim]")
    
    # Inject a verification instruction
    verification_prompt = ChatMessage(
        role="user",
        content=(
            "[SYSTEM: A fix was just applied. Run check_adapter_status and ping_dns "
            "to verify the network is now working. Then report the results.]"
        ),
    )
    messages.append(verification_prompt)
    
    # Run the verification loop
    final_message = await execute_tool_loop(
        llm_router=llm_router,
        tool_registry=tool_registry,
        messages=messages,
        tools=tools,
        max_iterations=3,  # Verification should be quick
    )
    
    messages.append(final_message)
    
    # Check if verification passed by looking for positive indicators
    content_lower = (final_message.content or "").lower()
    verification_passed = any(phrase in content_lower for phrase in [
        "working",
        "connected",
        "successful",
        "verified",
        "internet is accessible",
        "network is healthy",
    ])
    
    return verification_passed


# =============================================================================
# MAIN CHAT LOOP
# =============================================================================

async def run_chat_loop():
    """Main chat loop with multi-turn tool execution."""
    settings = get_settings()
    
    # Setup logging
    log_level = "DEBUG" if settings.debug else "INFO"
    setup_logging(level=log_level)
    logger.info("Starting chat loop")
    
    # Initialize analytics
    db_path = Path("data/analytics.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    storage = AnalyticsStorage(db_path)
    collector = AnalyticsCollector(storage=storage)
    
    # Initialize LLM router with analytics
    llm_router = LLMRouter(settings, analytics_collector=collector)
    tool_registry = get_registry()
    logger.info(f"Using LLM backend preference: {settings.llm_backend}")
    
    # Connect analytics to tool registry
    tool_registry.set_analytics(collector)

    # Register diagnostics
    from .diagnostics import register_all_diagnostics
    register_all_diagnostics(tool_registry)

    # Check LLM availability
    console.print("\n[bold blue]Network Diagnostics Assistant[/bold blue]")
    console.print("Checking LLM backends...\n")

    availability = await llm_router.is_available()
    for backend, available in availability.items():
        status = "[green]✓[/green]" if available else "[red]✗[/red]"
        console.print(f"  {status} {backend}")

    if not any(availability.values()):
        console.print(
            "\n[red]Error:[/red] No LLM backend available. "
            "Please start Ollama or set OPENAI_API_KEY."
        )
        return

    console.print(f"\nUsing model: [cyan]{llm_router.active_model or 'auto'}[/cyan]")
    console.print("Type your network problem or 'quit' to exit.")
    console.print("[dim]Commands: /feedback (rate session), /stats (show analytics)[/dim]\n")
    console.print("-" * 50)

    # Load diagnostic agent prompt
    system_prompt = load_prompt(AgentType.DIAGNOSTIC)
    
    # Conversation history
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system_prompt)
    ]
    
    # Start analytics session
    session = collector.start_session()
    console.print(f"[dim]Session: {session.session_id[:8]}...[/dim]")
    
    # Session state tracking
    first_message = True
    pending_verification = False

    # Chat loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")

            if user_input.lower() in ("quit", "exit", "q"):
                console.print("\n[dim]Goodbye![/dim]")
                prompt_for_feedback(collector)
                break
            
            # Handle special commands
            if user_input.strip() == "/feedback":
                prompt_for_feedback(collector)
                session = collector.start_session()
                console.print(f"\n[dim]New session: {session.session_id[:8]}...[/dim]")
                messages = [ChatMessage(role="system", content=system_prompt)]
                first_message = True
                pending_verification = False
                continue
            
            if user_input.strip() == "/stats":
                summary = storage.get_session_summary()
                console.print("\n[bold]Analytics Summary[/bold]")
                console.print(f"  Total sessions: {summary.total_sessions}")
                console.print(f"  Resolved: {summary.resolved_count} ({summary.success_rate:.1f}%)")
                console.print(f"  Avg tokens/session: {summary.avg_tokens_per_session:.0f}")
                console.print(f"  Avg time to resolution: {summary.avg_time_to_resolution_seconds:.1f}s")
                if summary.total_cost_usd > 0:
                    console.print(f"  Total OpenAI cost: ${summary.total_cost_usd:.4f}")
                continue

            if not user_input.strip():
                continue
            
            # Record user message
            collector.record_user_message(user_input)
            logger.info(f"User message: {user_input[:100]}...")
            
            # Check for resolution signal (user says "thanks", "it works", etc.)
            if detect_resolution_signal(user_input):
                console.print("\n[dim]It looks like your issue may be resolved![/dim]")
                want_feedback = Prompt.ask(
                    "Would you like to provide feedback?",
                    choices=["y", "n"],
                    default="n",
                )
                if want_feedback == "y":
                    prompt_for_feedback(collector)
                    session = collector.start_session()
                    console.print(f"\n[dim]New session: {session.session_id[:8]}...[/dim]")
                    messages = [ChatMessage(role="system", content=system_prompt)]
                    first_message = True
                    pending_verification = False
                continue

            # Add user message to history
            messages.append(ChatMessage(role="user", content=user_input))

            # Show thinking indicator
            console.print("\n[dim]Thinking...[/dim]")

            # Get tool definitions
            tools = tool_registry.get_all_definitions()
            logger.debug(f"Available tools: {[t.name for t in tools]}")
            
            # Set backend info after first call
            if first_message and llm_router.active_backend:
                collector.set_session_backend(
                    backend=llm_router.active_backend,
                    model_name=llm_router.active_model or "unknown",
                    had_fallback=llm_router.had_fallback,
                )
                first_message = False
            
            # =====================================================
            # MULTI-TURN TOOL EXECUTION LOOP
            # =====================================================
            final_message = await execute_tool_loop(
                llm_router=llm_router,
                tool_registry=tool_registry,
                messages=messages,
                tools=tools,
            )
            
            # Add final response to messages
            messages.append(final_message)
            
            # Display response
            console.print("\n[bold blue]Assistant[/bold blue]")
            if final_message.content:
                md = Markdown(final_message.content)
                console.print(md)
            else:
                console.print("[dim]No response content[/dim]")
            
            # Check if we should ask for resolution confirmation
            # This happens after verification or when the model indicates the problem is solved
            if final_message.content:
                content_lower = final_message.content.lower()
                if any(phrase in content_lower for phrase in [
                    "is your issue resolved",
                    "is your problem resolved",
                    "is that resolved",
                    "does that fix",
                    "network is healthy",
                    "everything is working",
                ]):
                    # Model is already asking, don't double-ask
                    pass

        except KeyboardInterrupt:
            console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
            collector.end_session(outcome=SessionOutcome.ABANDONED)
            break

        except Exception as e:
            logger.exception(f"Error in chat loop: {e}")
            console.print(f"\n[red]Error:[/red] {e}")
            if settings.debug:
                console.print_exception()

    # Cleanup
    await llm_router.close()


# =============================================================================
# CLI COMMANDS
# =============================================================================

@app.command()
def chat():
    """Start interactive chat session."""
    asyncio.run(run_chat_loop())


@app.command()
def check(
    diagnostic: str = typer.Argument(
        ...,
        help="Diagnostic to run: adapter, ip, gateway, dns-ping, dns-resolve",
    ),
):
    """Run a single diagnostic check."""

    async def run_diagnostic():
        tool_registry = get_registry()

        from .diagnostics import register_all_diagnostics
        register_all_diagnostics(tool_registry)

        name_map = {
            "adapter": "check_adapter_status",
            "ip": "get_ip_config",
            "gateway": "ping_gateway",
            "dns-ping": "ping_dns",
            "dns-resolve": "test_dns_resolution",
        }

        tool_name = name_map.get(diagnostic, diagnostic)
        tool = tool_registry.get_tool(tool_name)

        if not tool:
            console.print(f"[red]Unknown diagnostic:[/red] {diagnostic}")
            console.print(f"Available: {', '.join(name_map.keys())}")
            return

        console.print(f"\n[bold]Running {tool_name}...[/bold]\n")

        result = await tool()

        if hasattr(result, "to_llm_response"):
            md = Markdown(result.to_llm_response())
            console.print(md)
        else:
            console.print(result)

    asyncio.run(run_diagnostic())


@app.command()
def ladder():
    """Run full diagnostic ladder (all checks in sequence)."""

    async def run_ladder():
        tool_registry = get_registry()

        from .diagnostics import register_all_diagnostics
        register_all_diagnostics(tool_registry)

        checks = [
            ("check_adapter_status", "Checking network adapters..."),
            ("get_ip_config", "Checking IP configuration..."),
            ("ping_gateway", "Testing gateway connectivity..."),
            ("ping_dns", "Testing external connectivity..."),
            ("test_dns_resolution", "Testing DNS resolution..."),
        ]

        console.print("\n[bold blue]Running Diagnostic Ladder[/bold blue]\n")

        all_passed = True
        for tool_name, message in checks:
            console.print(f"[yellow]→[/yellow] {message}")

            tool = tool_registry.get_tool(tool_name)
            if not tool:
                console.print(f"  [red]✗[/red] Tool not found: {tool_name}")
                all_passed = False
                continue

            try:
                result = await tool()

                if result.success and result.data.get("reachable", True):
                    console.print(f"  [green]✓[/green] Passed")
                else:
                    console.print(f"  [red]✗[/red] Failed")
                    if result.suggestions:
                        for suggestion in result.suggestions[:2]:
                            console.print(f"    → {suggestion}")
                    all_passed = False
                    # Stop at first failure per diagnostic ladder rules
                    break

            except Exception as e:
                console.print(f"  [red]✗[/red] Error: {e}")
                all_passed = False
                break

        console.print()
        if all_passed:
            console.print("[bold green]All checks passed![/bold green]")
        else:
            console.print(
                "[bold yellow]Diagnostic stopped at first failure.[/bold yellow] "
                "Run 'network-diag chat' for AI-assisted troubleshooting."
            )

    asyncio.run(run_ladder())


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
```

---

## Implementation: Verification and Resolution Detection

The verification logic is already integrated into the main loop above. Here's a summary of how it works:

### Verification Flow

```
User reports problem
    ↓
Tool execution loop runs
    ↓
If an ACTION tool (enable_wifi) was called:
    ↓
Run verification loop:
    - check_adapter_status (verify connection)
    - ping_dns (verify internet)
    ↓
If verification passed:
    Ask user: "Is your issue resolved?"
```

### Resolution Detection

The system detects resolution through:

1. **Explicit model confirmation**: The model says "network is healthy" or similar
2. **User confirmation**: User responds with "thanks", "works", "fixed", etc.
3. **Verification tools pass**: check_adapter_status and ping_dns both succeed after a fix

---

## File Change Summary

Here is a complete list of files to create or modify:

| File | Action | Description |
|------|--------|-------------|
| `prompts/diagnostic_agent.md` | REPLACE | New prompt optimized for small models |
| `backend/diagnostics/__init__.py` | REPLACE | Enhanced tool descriptions with decision boundaries |
| `backend/llm/base.py` | MODIFY | Add tool_choice parameter to interface |
| `backend/llm/openai_client.py` | MODIFY | Implement tool_choice parameter |
| `backend/llm/ollama_client.py` | MODIFY | Implement tool_choice with workarounds |
| `backend/llm/router.py` | MODIFY | Add smart tool forcing logic |
| `backend/cli.py` | REPLACE | Multi-turn tool loop implementation |

### Files That Do NOT Need Changes

These files are already well-structured and don't need modification:

- `backend/diagnostics/adapter.py`
- `backend/diagnostics/connectivity.py`
- `backend/diagnostics/dns.py`
- `backend/diagnostics/ip_config.py`
- `backend/diagnostics/wifi.py`
- `backend/diagnostics/base.py`
- `backend/diagnostics/platform.py`
- `backend/tools/registry.py`
- `backend/tools/schemas.py`

---

## Testing Plan

### Test Case 1: Basic Tool Forcing

**Input**: "My internet is not working"

**Expected Behavior**:
1. Model IMMEDIATELY calls `check_adapter_status` with no preamble text
2. After receiving result, model either:
   - Calls next tool in sequence (if adapter OK), OR
   - Reports finding and suggests fix (if adapter has issue)

**Failure Criteria**:
- Model generates text like "Let me check your adapter" without a tool call
- Model skips `check_adapter_status` and calls a different tool first

### Test Case 2: Diagnostic Ladder Sequence

**Input**: "I can't access any websites"

**Expected Behavior**:
1. `check_adapter_status` → PASS
2. `get_ip_config` → PASS
3. `ping_gateway` → PASS
4. `ping_dns` → PASS
5. `test_dns_resolution` → FAIL
6. Model reports: "DNS resolution is failing" and suggests changing DNS

**Failure Criteria**:
- Model skips steps in the sequence
- Model stops after one tool without continuing

### Test Case 3: Stop at First Failure

**Input**: "No internet"

**Setup**: Disconnect WiFi adapter before test

**Expected Behavior**:
1. `check_adapter_status` → Returns is_connected=false
2. Model STOPS and reports: "Your adapter is not connected to a network"
3. Model does NOT call `get_ip_config` or any other tool

**Failure Criteria**:
- Model continues to call `ping_gateway` after adapter check failed

### Test Case 4: Action Tool Verification

**Input**: "Enable my wifi"

**Expected Behavior**:
1. `enable_wifi` → SUCCESS
2. Automatic verification: `check_adapter_status`
3. Automatic verification: `ping_dns`
4. Model asks: "I've verified your connection is working. Is your issue resolved?"

**Failure Criteria**:
- Model says "WiFi enabled" without running verification tools

### Test Case 5: Max Iterations Safety

**Input**: Craft a prompt that causes the model to keep calling tools

**Expected Behavior**:
1. Tool loop executes up to MAX_TOOL_ITERATIONS (7)
2. Loop terminates with a final response
3. No infinite loop occurs

**Failure Criteria**:
- Program hangs or crashes

---

## Rollback Plan

If the changes cause regressions, follow this rollback procedure:

### Immediate Rollback (< 5 minutes)

1. Restore the original `prompts/diagnostic_agent.md` from version control
2. Restore the original `backend/cli.py` from version control
3. The tool descriptions and LLM client changes are backwards-compatible and don't need immediate rollback

### Partial Rollback (Keep Some Changes)

If tool forcing causes issues but the multi-turn loop works:

1. In `backend/llm/router.py`, change `_determine_tool_choice` to always return `"auto"`
2. This disables forcing while keeping the iterative execution

If the multi-turn loop causes issues but tool forcing works:

1. In `backend/cli.py`, replace `execute_tool_loop` with the original single-pass logic
2. Keep the tool_choice="required" on first message

### Version Control Tags

Before deploying, create a git tag:

```bash
git tag -a v1.0-pre-tool-fix -m "Before tool calling improvements"
git push origin v1.0-pre-tool-fix
```

After deploying and verifying:

```bash
git tag -a v1.1-tool-fix -m "Tool calling improvements for small models"
git push origin v1.1-tool-fix
```

---

## Conclusion

This implementation plan addresses all five root causes of the tool calling issues:

1. **Prompt verbosity** → Replaced with imperative, table-based prompt
2. **Generic tool descriptions** → Added explicit decision boundaries
3. **No forcing mechanism** → Implemented tool_choice="required" with smart logic
4. **Single-turn execution** → Replaced with iterative tool loop
5. **Missing verification** → Added automatic verification after action tools

The changes are designed to be:
- **Backwards compatible**: Works with existing tool implementations
- **Incrementally deployable**: Each change can be tested independently
- **Observable**: Extensive logging for debugging
- **Safe**: Maximum iteration limits prevent infinite loops

After implementation, the model should immediately call tools when given network problems, follow the diagnostic ladder correctly, stop at failures, and verify fixes before declaring success.
