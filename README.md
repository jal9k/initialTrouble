# TechTim(e)

An intelligent, cross-platform L1 desktop support tool that uses LLM reasoning (Ollama/OpenAI) to diagnose and troubleshoot IT issues.

## Features

- **LLM-Powered Reasoning**: Uses Ministral 3B (via Ollama) or OpenAI GPT models to intelligently diagnose issues
- **Cross-Platform**: Works on both macOS and Windows
- **Multiple Interfaces**: CLI for terminal users, Web UI for graphical interaction
- **Systematic Diagnostics**: Follows structured troubleshooting for thorough problem resolution

## Quick Start

### 1. Activate the Environment

```bash
# Future environment name (after recreating)
conda activate techtime

# Current environment (if not yet migrated)
conda activate network-diag
```

### 2. Configure Environment

```bash
cp env.example.txt .env
# Edit .env with your configuration
```

### 3. Run the CLI

```bash
python -m backend.cli
```

### 4. Run the API Server

```bash
uvicorn backend.main:app --reload
```

## Diagnostic Functions

| Function | Layer | Purpose |
|----------|-------|---------|
| `check_adapter_status` | Physical | Check if network adapter is enabled |
| `get_ip_config` | Link | Verify IP address assignment |
| `ping_gateway` | Network | Test gateway reachability |
| `ping_dns` | Network | Test external DNS server reachability |
| `test_dns_resolution` | Application | Verify DNS name resolution |

## Architecture

```
User → CLI/Web UI → FastAPI → LLM Router → Diagnostics → OS Commands
```

The LLM receives your problem description, decides which diagnostic functions to run, interprets the results, and suggests fixes.

## Requirements

- Python 3.11+
- Conda (for environment management)
- Ollama (optional, for local LLM) or OpenAI API key

## License

MIT
