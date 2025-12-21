# Session Debug Reference

This document maps the tools and prompts used in the terminal session to their source files.

## Terminal Session Summary

From the terminal output, the agent:
1. Started a chat session using the `diagnostic_agent` prompt
2. Called `check_adapter_status` twice
3. Failed to call `enable_wifi` when it should have
4. Encountered a 500 error from Ollama

---

## Tool Locations

### `check_adapter_status`

The tool that was called in the session to check network adapter status.

| File | Description |
|------|-------------|
| `backend/diagnostics/adapter.py` | **Implementation** - The actual diagnostic logic |
| `backend/diagnostics/__init__.py:28,35-48` | **Registration** - Where it's registered with the tool registry |
| `docs/functions/check_adapter_status.md` | **Documentation** - Usage docs and examples |

### `enable_wifi`

The tool that **should have been called** but wasn't.

| File | Description |
|------|-------------|
| `backend/diagnostics/wifi.py` | **Implementation** - WiFi enable/disable logic |
| `backend/diagnostics/__init__.py:32,122-137` | **Registration** - Where it's registered with the tool registry |
| `docs/functions/enable_wifi.md` | **Documentation** - Usage docs and examples |

---

## Prompt Locations

### System Prompt (Diagnostic Agent)

The prompt that instructs the LLM how to behave and when to use tools.

| File | Description |
|------|-------------|
| `prompts/diagnostic_agent.md` | **Main prompt** - OSI ladder diagnostic flow, tool usage rules |
| `backend/prompts.py` | **Loader** - How prompts are loaded and used |
| `backend/cli.py:133` | **Usage** - Where the prompt is loaded in CLI |

### Key Prompt Sections

From `prompts/diagnostic_agent.md`:

- **Lines 7-17**: OSI Diagnostic Ladder definition
- **Lines 19-40**: Critical rules (start at Layer 1, stop at failure, etc.)
- **Lines 42-74**: Decision tree for diagnostics
- **Lines 89-111**: Verification flow after fixes (should trigger `enable_wifi` → verify)
- **Lines 133-141**: Example showing correct `enable_wifi` usage

---

## LLM Client Locations

### Ollama Client (used in session)

| File | Description |
|------|-------------|
| `backend/llm/ollama_client.py` | **Implementation** - Ollama API client |
| `backend/llm/router.py` | **Router** - Backend selection and fallback logic |
| `backend/config.py:23` | **Config** - Model setting (`ministral-3:3b`) |

---

## Tool Registry

The central registry that manages all diagnostic tools.

| File | Description |
|------|-------------|
| `backend/tools/registry.py` | **Implementation** - Tool registration and execution |
| `backend/tools/schemas.py` | **Schemas** - ToolCall, ToolResult, ToolDefinition types |

---

## Logging (NEW)

Logs are now written to help debug issues like the one in this session.

| File | Description |
|------|-------------|
| `backend/logging_config.py` | **Configuration** - Logging setup |
| `data/logs/network_diag_YYYYMMDD.log` | **Log files** - Daily rotating log files |

### What Gets Logged

- User messages
- LLM requests and responses
- Tool calls and results
- Errors and exceptions
- Timing information

### Enable Debug Logging

Set `debug=true` in `.env` or run with:
```bash
DEBUG=true python -m backend.cli chat
```

---

## Why `enable_wifi` Wasn't Called

Based on the code review:

1. **Tool was properly registered** (`backend/diagnostics/__init__.py:122-137`)
2. **Prompt instructs to use it** (`prompts/diagnostic_agent.md:133-141`)
3. **LLM (ministral:3b) didn't follow instructions** - Small models often struggle with tool calling
4. **No logging** meant we couldn't see why the LLM made its decisions

### Recommendations

1. Use a larger model (e.g., `llama3:8b`, `gpt-4o-mini`)
2. Check `data/logs/` for detailed debug info after running with new logging
3. Consider adding examples of tool calling to the prompt for smaller models

---

## Quick Reference: File Paths

```
network-diag/
├── backend/
│   ├── cli.py                    # CLI entry point
│   ├── config.py                 # Settings (model, backend)
│   ├── logging_config.py         # NEW: Logging setup
│   ├── prompts.py                # Prompt loader
│   ├── diagnostics/
│   │   ├── __init__.py           # Tool registration
│   │   ├── adapter.py            # check_adapter_status
│   │   └── wifi.py               # enable_wifi
│   ├── llm/
│   │   ├── router.py             # LLM backend router
│   │   └── ollama_client.py      # Ollama client
│   └── tools/
│       ├── registry.py           # Tool registry
│       └── schemas.py            # Tool schemas
├── prompts/
│   └── diagnostic_agent.md       # Main agent prompt
├── docs/
│   └── functions/
│       ├── check_adapter_status.md
│       └── enable_wifi.md
└── data/
    ├── analytics.db              # Session analytics
    └── logs/                     # NEW: Log files
        └── network_diag_*.log
```

