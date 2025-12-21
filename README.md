# Network Diagnostics Troubleshooter

An intelligent, cross-platform network diagnostics tool that uses LLM reasoning (Ollama/OpenAI) to diagnose and troubleshoot network connectivity issues.

## Features

- **LLM-Powered Reasoning**: Uses Ministral 3B (via Ollama) or OpenAI GPT models to intelligently diagnose network issues
- **Cross-Platform**: Works on both macOS and Windows
- **Multiple Interfaces**: CLI for terminal users, Web UI for graphical interaction
- **Systematic Diagnostics**: Follows the OSI model ladder for thorough troubleshooting

## Quick Start

### 1. Activate the Environment

```bash
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

