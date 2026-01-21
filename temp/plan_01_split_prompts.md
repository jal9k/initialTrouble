# Plan: Split Prompts for Cloud vs Local Models

**Priority**: High  
**Effort**: Medium  
**Status**: Not Started

---

## Problem

The current `diagnostic_agent.md` prompt is ~189 lines long, which is:
- Too verbose for small Ollama models (3B parameter, 4K context)
- Not optimized for Claude's XML-tag parsing
- Not leveraging reasoning capabilities of cloud models

## Goal

Create provider-specific prompts that maximize effectiveness for each target:
- **Cloud models** (GPT-4, Claude, Grok): Full reasoning guidance with XML structure
- **Local models** (Ollama 3B): Condensed, action-focused prompt under 500 tokens

---

## Implementation Steps

### Step 1: Create Prompt Directory Structure

```
prompts/
├── cloud/
│   ├── openai.md       # Full reasoning prompt for GPT-4
│   └── anthropic.md    # XML-tagged prompt for Claude
├── local/
│   └── ollama.md       # Condensed <500 tokens
├── diagnostic_agent.md # Legacy/default (keep for compatibility)
└── README.md           # Updated documentation
```

### Step 2: Create Cloud Prompts

**File: `prompts/cloud/anthropic.md`**

Convert current prompt to XML-tagged format:

```markdown
<role>
You are TechTime, an IT diagnostic assistant. You diagnose network problems using tools.
</role>

<rules>
<rule name="tool_first" priority="critical">
Call a diagnostic tool IMMEDIATELY when user reports a problem.
Never explain what you will do - just call the tool.
</rule>

<rule name="diagnostic_sequence">
Follow this sequence:
1. check_adapter_status (ALWAYS first)
2. get_ip_config (if adapter connected)
3. ping_gateway (if valid IP)
4. ping_dns (if gateway reachable)
5. test_dns_resolution (if internet accessible)
</rule>

<rule name="auto_fix">
When a diagnostic fails, try automatic fixes before stopping:
- has_network_connection=false → Call enable_wifi first
- connected_count=0 → Call enable_wifi first
Only STOP after remediation fails.
</rule>
</rules>

<reasoning_approach>
When diagnosing network issues:
1. Identify the symptom (what isn't working?)
2. Determine the network layer (physical, IP, DNS?)
3. Select the appropriate diagnostic tool
4. Analyze the result before proceeding
5. Attempt automatic remediation if possible
</reasoning_approach>

<response_format>
After diagnostics, respond with:

**Finding**: [What you found]
**Cause**: [Why this is happening - must cite tool output]
**Fix**:
1. [First step]
2. [Second step]
</response_format>
```

**File: `prompts/cloud/openai.md`**

Similar structure but with markdown headers (GPT-4 prefers this):

```markdown
# TechTime Diagnostic Agent

You diagnose IT problems using tools. Follow these rules exactly.

## Core Principle: Tool-First Response

When a user reports a network problem, IMMEDIATELY call a diagnostic tool.
DO NOT write explanations first. Just call the tool.

## Diagnostic Sequence

| Step | Tool | Condition |
|------|------|-----------|
| 1 | check_adapter_status | ALWAYS first |
| 2 | get_ip_config | Adapter connected |
| 3 | ping_gateway | Valid IP exists |
| 4 | ping_dns | Gateway reachable |
| 5 | test_dns_resolution | Internet accessible |

## Reasoning Guidance

Think step-by-step:
1. What layer is likely failing? (Physical → IP → DNS)
2. Which tool confirms or eliminates this layer?
3. What does the result tell us about root cause?
4. Can I fix it automatically, or must the user act?

[... rest of rules ...]
```

### Step 3: Create Local Prompt (Condensed)

**File: `prompts/local/ollama.md`**

Target: Under 500 tokens, action-focused, no reasoning guidance.

```markdown
# IT Diagnostic Assistant

Call tools immediately for network problems. Never explain first.

## Sequence
1. check_adapter_status (always)
2. get_ip_config (if connected)
3. ping_gateway (if has IP)
4. ping_dns (if gateway ok)

## Auto-Fix Rules
- No connection → enable_wifi → re-check
- APIPA IP (169.254.x.x) → STOP, DHCP failed
- No gateway → STOP, router issue

## Response Format
**Finding**: [tool result]
**Fix**: [steps]

## Tool Mapping
| User says | Tool |
|-----------|------|
| no internet | check_adapter_status |
| wifi not working | enable_wifi |
| DNS error | test_dns_resolution |
```

### Step 4: Update `prompts.py` for Provider Selection

```python
# backend/prompts.py

from enum import Enum
from pathlib import Path
from functools import lru_cache


class ProviderType(Enum):
    """LLM provider categories for prompt selection."""
    CLOUD_OPENAI = "openai"
    CLOUD_ANTHROPIC = "anthropic"
    CLOUD_XAI = "xai"
    CLOUD_GOOGLE = "google"
    LOCAL_OLLAMA = "ollama"


def _get_prompt_for_provider(agent_type: AgentType, provider: str) -> Path:
    """
    Get the appropriate prompt file for a provider.
    
    Args:
        agent_type: The agent type (diagnostic, triage, etc.)
        provider: Provider name (openai, anthropic, ollama, etc.)
    
    Returns:
        Path to the prompt file
    """
    prompts_dir = _get_prompts_dir()
    
    # Map providers to prompt directories
    if provider in ("openai", "xai", "google"):
        cloud_prompt = prompts_dir / "cloud" / "openai.md"
        if cloud_prompt.exists():
            return cloud_prompt
    
    if provider == "anthropic":
        anthropic_prompt = prompts_dir / "cloud" / "anthropic.md"
        if anthropic_prompt.exists():
            return anthropic_prompt
    
    if provider == "ollama":
        local_prompt = prompts_dir / "local" / "ollama.md"
        if local_prompt.exists():
            return local_prompt
    
    # Fallback to legacy prompt
    return prompts_dir / f"{agent_type.value}_agent.md"


@lru_cache(maxsize=20)
def load_prompt(agent_type: AgentType | str, provider: str | None = None) -> str:
    """
    Load a system prompt for the specified agent type and provider.
    
    Args:
        agent_type: AgentType enum or string name
        provider: Optional provider name for provider-specific prompts
        
    Returns:
        System prompt content as string
    """
    if isinstance(agent_type, str):
        agent_type = AgentType(agent_type)
    
    if provider:
        prompt_file = _get_prompt_for_provider(agent_type, provider)
    else:
        prompt_file = PROMPTS_DIR / f"{agent_type.value}_agent.md"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_file}")
    
    return prompt_file.read_text()
```

### Step 5: Update `chat_service.py` to Pass Provider

```python
# In chat() method

# Get system prompt for current provider
provider = self._gluellm_wrapper.active_provider or "ollama"
system_prompt = load_prompt(AgentType.DIAGNOSTIC, provider=provider)
```

### Step 6: Update `gluellm_wrapper.py` to Support Prompt Selection

```python
# Modify chat() to accept optional prompt selection

async def chat(
    self,
    messages: list[dict[str, Any]],
    system_prompt: str | None = None,
    use_provider_prompt: bool = True,
) -> "ChatServiceResponse":
    # ... existing code ...
    
    # If no custom prompt and provider prompts enabled, load provider-specific
    if system_prompt is None and use_provider_prompt:
        from ..prompts import load_prompt, AgentType
        system_prompt = load_prompt(AgentType.DIAGNOSTIC, provider=provider)
```

---

## Testing Plan

1. **Unit Tests**
   - Test prompt loading for each provider
   - Verify fallback to legacy prompt when provider-specific not found
   - Test cache behavior with provider parameter

2. **Integration Tests**
   - Verify Claude receives XML-tagged prompt
   - Verify Ollama receives condensed prompt
   - Test provider switching preserves correct prompts

3. **Manual Validation**
   - Test with GPT-4: Should follow reasoning guidance
   - Test with Claude: Should parse XML structure
   - Test with Ollama 3B: Should fit in context, respond quickly

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `prompts/cloud/openai.md` | Create | Full reasoning prompt for GPT-4/Grok/Gemini |
| `prompts/cloud/anthropic.md` | Create | XML-tagged prompt for Claude |
| `prompts/local/ollama.md` | Create | Condensed prompt for local models |
| `backend/prompts.py` | Modify | Add provider-aware prompt loading |
| `backend/chat_service.py` | Modify | Pass provider to prompt loader |
| `prompts/README.md` | Update | Document new structure |

---

## Success Criteria

- [ ] Cloud prompts leverage reasoning guidance
- [ ] Anthropic prompt uses XML tags
- [ ] Ollama prompt under 500 tokens
- [ ] Automatic prompt selection based on provider
- [ ] Fallback to legacy prompt works
- [ ] All existing tests pass
