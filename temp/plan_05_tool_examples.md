# Plan: Enhance Tool Descriptions with Examples

**Priority**: Medium  
**Effort**: Low  
**Status**: Not Started

---

## Problem

Current tool descriptions lack usage examples, making it harder for LLMs to understand:
- When to use each tool
- Expected input formats
- What output to expect

```python
# Current: Description only
lines = [definition.description, ""]
lines.append("Args:")
for param in definition.parameters:
    lines.append(f"    {param.name}: {param.description}")
```

## Goal

Add structured examples to tool definitions and include them in the generated docstrings, improving LLM tool selection accuracy.

---

## Implementation Steps

### Step 1: Extend ToolDefinition Schema

**Modify: `backend/tools/schemas.py`**

```python
"""Tool schema definitions for TechTime diagnostics."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolExample:
    """
    An example of tool usage for LLM guidance.
    
    Examples help LLMs understand:
    - When to use a tool
    - What input parameters to provide
    - What kind of output to expect
    """
    
    description: str
    """Brief description of what this example demonstrates."""
    
    input: dict[str, Any]
    """Example input parameters."""
    
    output_summary: str
    """Summary of expected output (not full output, just description)."""
    
    use_when: str | None = None
    """Optional: When this tool should be used."""


@dataclass
class ParameterDefinition:
    """Definition of a single tool parameter."""
    
    name: str
    """Parameter name as it appears in function signature."""
    
    type: str
    """Parameter type: 'string', 'number', 'boolean', 'array', 'object'."""
    
    description: str
    """Human-readable description of what this parameter does."""
    
    required: bool = True
    """Whether this parameter is required."""
    
    default: Any | None = None
    """Default value if not provided."""
    
    enum: list[str] | None = None
    """List of allowed values (for string enums)."""


@dataclass
class ToolDefinition:
    """
    Complete definition of a diagnostic tool.
    
    This schema is used to:
    1. Register tools with the ToolRegistry
    2. Generate tool schemas for LLM providers
    3. Build documentation
    """
    
    name: str
    """Unique tool identifier (snake_case)."""
    
    description: str
    """Detailed description of what this tool does and when to use it."""
    
    parameters: list[ParameterDefinition] = field(default_factory=list)
    """List of input parameters."""
    
    examples: list[ToolExample] = field(default_factory=list)  # NEW
    """Usage examples for LLM guidance."""
    
    category: str = "diagnostic"
    """Tool category: 'diagnostic', 'remediation', 'info'."""
    
    platforms: list[str] = field(default_factory=lambda: ["macos", "windows", "linux"])
    """Platforms this tool supports."""
    
    requires_admin: bool = False
    """Whether this tool requires elevated privileges."""
```

### Step 2: Update Tool Adapter to Include Examples

**Modify: `backend/llm/tool_adapter.py`**

```python
def _build_docstring(definition: ToolDefinition) -> str:
    """
    Build a comprehensive docstring for GlueLLM schema generation.
    
    GlueLLM parses docstrings to extract parameter descriptions,
    so we format them in Google-style docstring format with examples.
    """
    lines = [definition.description, ""]
    
    # Add examples if available (NEW)
    if definition.examples:
        lines.append("Examples:")
        for i, example in enumerate(definition.examples, 1):
            lines.append(f"    Example {i}: {example.description}")
            if example.use_when:
                lines.append(f"        Use when: {example.use_when}")
            lines.append(f"        Input: {_format_example_input(example.input)}")
            lines.append(f"        Output: {example.output_summary}")
            lines.append("")
    
    if definition.parameters:
        lines.append("Args:")
        for param in definition.parameters:
            required = "(required)" if param.required else "(optional)"
            default = f", default={param.default}" if param.default is not None else ""
            enum_info = f", one of: {param.enum}" if param.enum else ""
            lines.append(
                f"    {param.name}: {param.description} {required}{default}{enum_info}"
            )
        lines.append("")
    
    lines.append("Returns:")
    lines.append("    str: Result of the tool execution")
    
    return "\n".join(lines)


def _format_example_input(input_dict: dict[str, Any]) -> str:
    """Format example input as a readable string."""
    if not input_dict:
        return "(no parameters)"
    
    parts = [f"{k}={repr(v)}" for k, v in input_dict.items()]
    return ", ".join(parts)
```

### Step 3: Add Examples to Existing Tool Definitions

**Modify: `backend/diagnostics/__init__.py`**

Update tool registrations to include examples:

```python
from ..tools.schemas import ToolDefinition, ParameterDefinition, ToolExample

# check_adapter_status
registry.register(
    ToolDefinition(
        name="check_adapter_status",
        description="""Check the status of network adapters on the system.
        
This is the FIRST diagnostic to run for any network connectivity issue.
It identifies which network interfaces exist and their connection state.""",
        parameters=[],
        examples=[
            ToolExample(
                description="Initial network troubleshooting",
                input={},
                output_summary="JSON with adapter names, connection states, and IP info",
                use_when="User reports 'no internet', 'WiFi not working', or 'can't connect'",
            ),
        ],
        category="diagnostic",
    ),
    check_adapter_status,
)

# enable_wifi
registry.register(
    ToolDefinition(
        name="enable_wifi",
        description="""Enable the WiFi adapter and attempt to connect to a network.
        
Call this when check_adapter_status shows WiFi is disabled or not connected.""",
        parameters=[],
        examples=[
            ToolExample(
                description="Enable disabled WiFi",
                input={},
                output_summary="Success/failure message with new WiFi state",
                use_when="check_adapter_status shows has_network_connection=false",
            ),
        ],
        category="remediation",
    ),
    enable_wifi,
)

# ping_gateway
registry.register(
    ToolDefinition(
        name="ping_gateway",
        description="""Ping the default gateway to test local network connectivity.
        
Run this AFTER confirming the adapter has a valid IP address.""",
        parameters=[],
        examples=[
            ToolExample(
                description="Test router reachability",
                input={},
                output_summary="Ping results with latency, packet loss, and reachability status",
                use_when="get_ip_config shows valid IP (not 169.254.x.x) and gateway",
            ),
        ],
        category="diagnostic",
    ),
    ping_gateway,
)

# ping_dns
registry.register(
    ToolDefinition(
        name="ping_dns",
        description="""Ping public DNS servers to test internet connectivity.
        
Run this AFTER confirming the gateway is reachable.""",
        parameters=[],
        examples=[
            ToolExample(
                description="Test internet access via DNS ping",
                input={},
                output_summary="Ping results to 8.8.8.8 and 1.1.1.1 with reachability status",
                use_when="ping_gateway shows gateway is reachable",
            ),
        ],
        category="diagnostic",
    ),
    ping_dns,
)

# test_dns_resolution
registry.register(
    ToolDefinition(
        name="test_dns_resolution",
        description="""Test DNS resolution by resolving hostnames to IP addresses.
        
Run this AFTER confirming internet is accessible (ping_dns passes).""",
        parameters=[
            ParameterDefinition(
                name="hostnames",
                type="string",
                description="Comma-separated hostnames to resolve",
                required=False,
                default="google.com,cloudflare.com",
            ),
        ],
        examples=[
            ToolExample(
                description="Test default hostname resolution",
                input={},
                output_summary="Resolution results for google.com and cloudflare.com",
                use_when="ping_dns passes but user reports 'website won't load'",
            ),
            ToolExample(
                description="Test specific hostname",
                input={"hostnames": "mycompany.com"},
                output_summary="Resolution result for the specific hostname",
                use_when="User reports specific website not loading",
            ),
        ],
        category="diagnostic",
    ),
    test_dns_resolution,
)

# toggle_bluetooth
registry.register(
    ToolDefinition(
        name="toggle_bluetooth",
        description="""Toggle Bluetooth on or off, or check its current status.
        
NOTE: This is SEPARATE from network diagnostics. Only use for Bluetooth issues.""",
        parameters=[
            ParameterDefinition(
                name="action",
                type="string",
                description="Action to perform",
                required=False,
                default="status",
                enum=["on", "off", "status"],
            ),
        ],
        examples=[
            ToolExample(
                description="Enable Bluetooth",
                input={"action": "on"},
                output_summary="Bluetooth enabled/already on confirmation",
                use_when="User says 'fix bluetooth' or 'enable bluetooth'",
            ),
            ToolExample(
                description="Check Bluetooth status",
                input={"action": "status"},
                output_summary="Current Bluetooth state (on/off) and connected devices",
                use_when="User asks 'is bluetooth on?' or 'check bluetooth'",
            ),
        ],
        category="remediation",
    ),
    toggle_bluetooth,
)
```

### Step 4: Create Example Templates

**File: `backend/tools/example_templates.py`**

```python
"""Standard example templates for common tool patterns."""

from .schemas import ToolExample


def network_diagnostic_example(
    tool_name: str,
    use_when: str,
) -> ToolExample:
    """Create a standard network diagnostic example."""
    return ToolExample(
        description=f"Run {tool_name} for network troubleshooting",
        input={},
        output_summary="JSON with diagnostic results and recommendations",
        use_when=use_when,
    )


def remediation_example(
    action: str,
    use_when: str,
) -> ToolExample:
    """Create a standard remediation example."""
    return ToolExample(
        description=f"Attempt to {action}",
        input={},
        output_summary="Success/failure with details",
        use_when=use_when,
    )
```

### Step 5: Add Validation for Examples

**Modify: `backend/tools/registry.py`**

```python
def register(
    self,
    definition: ToolDefinition,
    func: Callable,
) -> None:
    """
    Register a tool with the registry.
    
    Args:
        definition: Tool definition with metadata
        func: The callable function
    """
    # Validate definition
    if not definition.name:
        raise ValueError("Tool definition must have a name")
    
    if definition.name in self._tools:
        raise ValueError(f"Tool '{definition.name}' already registered")
    
    # Warn if no examples (soft validation)
    if not definition.examples:
        import logging
        logging.getLogger("techtime.tools").warning(
            f"Tool '{definition.name}' has no examples - consider adding some"
        )
    
    self._definitions[definition.name] = definition
    self._tools[definition.name] = func
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/tools/schemas.py` | Modify | Add ToolExample class |
| `backend/llm/tool_adapter.py` | Modify | Include examples in docstring |
| `backend/diagnostics/__init__.py` | Modify | Add examples to all tools |
| `backend/tools/example_templates.py` | Create | Reusable example templates |
| `backend/tools/registry.py` | Modify | Warn on missing examples |

---

## Example Output (Generated Docstring)

Before:
```
Check the status of network adapters on the system.

Args:
    (none)

Returns:
    str: Result of the tool execution
```

After:
```
Check the status of network adapters on the system.

This is the FIRST diagnostic to run for any network connectivity issue.
It identifies which network interfaces exist and their connection state.

Examples:
    Example 1: Initial network troubleshooting
        Use when: User reports 'no internet', 'WiFi not working', or 'can't connect'
        Input: (no parameters)
        Output: JSON with adapter names, connection states, and IP info

Args:
    (none)

Returns:
    str: Result of the tool execution
```

---

## Testing Plan

1. **Unit Tests**
   - ToolExample serialization
   - Docstring generation with examples
   - Example validation

2. **Integration Tests**
   - Tools with examples generate proper schemas
   - LLM receives examples in tool description

3. **Manual Validation**
   - Test with GPT-4: Does it use tools more appropriately?
   - Test tool selection accuracy before/after

---

## Success Criteria

- [ ] All diagnostic tools have at least 1 example
- [ ] Examples include use_when guidance
- [ ] Generated docstrings include examples
- [ ] Examples are included in LLM tool schemas
- [ ] No regression in tool execution
- [ ] All tests pass
