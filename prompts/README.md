# System Prompts for Network Diagnostics

This directory contains specialized system prompts for different diagnostic agents, optimized for [Ministral-3](https://ollama.com/library/ministral-3).

## Agent Types

| Agent | File | Purpose |
|-------|------|---------|
| Triage | `triage_agent.md` | Initial assessment, categorize the issue |
| Diagnostic | `diagnostic_agent.md` | Systematic OSI-layer troubleshooting |
| Remediation | `remediation_agent.md` | Suggest and guide fixes |
| Quick Check | `quick_check_agent.md` | Fast basic checks only |

## Ministral-3 Optimization

These prompts leverage Ministral-3's strengths:
- **Function Calling**: Native tool use for diagnostics
- **System Prompt Adherence**: Strong instruction following
- **Structured Output**: JSON and markdown support
- **Agentic Reasoning**: Multi-step problem solving

## Usage

Load the appropriate prompt based on context:

```python
from pathlib import Path

def load_prompt(agent_type: str) -> str:
    prompt_file = Path(__file__).parent / "prompts" / f"{agent_type}_agent.md"
    return prompt_file.read_text()
```

