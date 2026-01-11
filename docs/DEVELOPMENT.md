# TechTim(e) Development Guide

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed (for testing)

### Initial Setup

```bash
# Clone and enter project
git clone <repo-url>
cd network-diag

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[all]"

# Install frontend dependencies
cd frontend/techtime
npm install
cd ../..
```

## Development Modes

### Mode 1: Desktop App with Hot Reload (Recommended)

Run the frontend dev server and desktop app together for live reloading:

**Terminal 1 - Frontend Dev Server:**
```bash
cd frontend/techtime
npm run dev
```

**Terminal 2 - Desktop App:**
```bash
python desktop_main.py --dev --debug
```

The `--dev` flag tells the desktop app to load from `http://localhost:3000` instead of static files.

Changes to frontend code will hot-reload automatically.

### Mode 2: Backend Server Only

For testing the FastAPI backend without PyWebView:

```bash
# Start the FastAPI server
python -m uvicorn backend.main:app --reload --port 8000

# In another terminal, start the frontend
cd frontend/techtime
npm run dev
```

Access at `http://localhost:3000`

### Mode 3: Static Build Testing

Test the production-like static build:

```bash
# Build the frontend
cd frontend/techtime
npm run build

# Run desktop app with static files
cd ../..
python desktop_main.py
```

## Project Structure

```
network-diag/
├── backend/              # FastAPI backend
│   ├── config.py         # Configuration management
│   ├── main.py           # FastAPI entry point
│   ├── chat_service.py   # Chat orchestration (Phase 1)
│   ├── preferences.py    # User preferences management
│   ├── llm/              # LLM clients
│   ├── tools/            # Tool registry
│   └── diagnostics/      # Diagnostic tools
├── desktop/              # Desktop application (Phase 2)
│   ├── __init__.py
│   ├── api.py            # PyWebView API bridge
│   ├── ollama_manager.py # Ollama sidecar management
│   ├── process_guard.py  # Orphaned process cleanup
│   └── exceptions.py     # Desktop exceptions
├── analytics/            # Analytics module
├── frontend/techtime/    # Next.js frontend
├── prompts/              # Agent prompts
├── scripts/              # Build scripts (Phase 4)
├── tests/                # Test suite (Phase 5)
├── docs/                 # Documentation
├── desktop_main.py       # Desktop entry point
└── techtim.spec          # PyInstaller spec
```

## Common Tasks

### Adding a New Diagnostic Tool

1. Create tool in `backend/diagnostics/`:
   ```python
   from backend.tools import tool
   
   @tool(description="Does something useful")
   async def my_new_tool(param: str) -> str:
       # Implementation
       return "Result"
   ```

2. Import in `backend/diagnostics/__init__.py`

3. The tool is automatically registered

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=backend --cov=desktop --cov=analytics

# Specific test file
pytest tests/unit/test_chat_service.py

# Tests matching pattern
pytest -k "test_session"
```

### Building the App

```bash
# Full build (downloads Ollama, builds frontend, runs PyInstaller)
python scripts/build_app.py

# Quick rebuild (skip Ollama download)
python scripts/build_app.py --skip-deps

# Clean build
python scripts/build_app.py --clean
```

### Linting and Formatting

```bash
# Run ruff linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Type checking
mypy backend/ desktop/
```

## Debugging

### Enable Debug Mode

```bash
python desktop_main.py --debug
```

This enables:
- Verbose logging
- Chrome DevTools (right-click in window → Inspect)

### View Logs

Logs are stored in the user data directory:

- **macOS**: `~/Library/Application Support/TechTime/logs/`
- **Windows**: `%APPDATA%\TechTime\logs\`
- **Linux**: `~/.local/share/TechTime/logs/`

### Common Issues

**"Frontend not found"**
```bash
cd frontend/techtime && npm run build
```

**"Ollama not found"**
- Install Ollama: https://ollama.ai
- Or run in dev mode: `python desktop_main.py --dev`

**"Model not available"**
```bash
ollama pull mistral:7b-instruct
```

## Environment Variables

Create a `.env` file in the project root:

```env
# LLM Configuration
LLM_BACKEND=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral:7b-instruct

# Optional: OpenAI fallback
OPENAI_API_KEY=sk-...

# Debug settings
DEBUG=false
LOG_LEVEL=INFO
```

## Using Make Commands

The project includes a Makefile for common operations:

```bash
# Show all available commands
make help

# Install all dependencies
make install-all

# Run in development mode
make dev-frontend  # Terminal 1
make dev-desktop   # Terminal 2

# Build the application
make build

# Run tests
make test
make test-cov

# Lint and format
make lint
make format
```

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run tests and linting: `make test lint`
4. Submit a pull request

## Architecture Notes

### Chat Flow

1. User sends message via WebSocket
2. `ChatService` orchestrates the conversation
3. LLM generates response (may include tool calls)
4. Tools are executed and results returned
5. Response streamed back to frontend

### Desktop Integration

- PyWebView creates a native window embedding the frontend
- JavaScript API bridge connects frontend to Python backend
- Ollama runs as a managed subprocess (sidecar)
- User preferences persist in the platform's app data directory

### Bundled Mode

When packaged with PyInstaller:
- Resources extracted to temporary directory (`sys._MEIPASS`)
- User data stored in platform app data directory
- Ollama binary bundled and managed by the app
