# Phase 7: Final Integration & Polish

## Objective

Complete the desktop application by addressing integration gaps, adding polish features, and ensuring a smooth development workflow. This phase covers dependency management, user preferences, crash recovery, and final verification.

## Prerequisites

Before starting this phase, ensure you have:
- Phases 1-6 completed
- Desktop application running successfully with `python desktop_main.py`
- Build process working with `python scripts/build_app.py`

---

## Task 7.1: Update pyproject.toml with Desktop Dependencies

### Purpose

Add desktop-specific dependencies to the project configuration so they're properly tracked and installed.

### File: `pyproject.toml`

Add the following to your existing `pyproject.toml`:

```toml
[project]
# ... existing configuration ...

dependencies = [
    # ... existing dependencies ...
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.25.0",
]

[project.optional-dependencies]
# Backend server dependencies
server = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "websockets>=11.0",
]

# Desktop application dependencies
desktop = [
    "pywebview>=5.0",
    "httpx>=0.25.0",
]

# Build and distribution dependencies
build = [
    "pyinstaller>=6.0",
]

# Development dependencies
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]

# All dependencies for full development
all = [
    "techtime[server,desktop,build,dev]",
]

[project.scripts]
# CLI entry points
techtime-server = "backend.cli:run_server"
techtime-desktop = "desktop_main:main"
```

### Installation Commands

```bash
# Install for server development
pip install -e ".[server,dev]"

# Install for desktop development
pip install -e ".[desktop,dev]"

# Install everything
pip install -e ".[all]"

# Install for building distributable
pip install -e ".[desktop,build]"
```

---

## Task 7.2: Create Development Workflow Documentation

### Purpose

Document the development workflow so contributors can efficiently work on the desktop application.

### File: `docs/DEVELOPMENT.md`

```markdown
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
│   ├── llm/              # LLM clients
│   ├── tools/            # Tool registry
│   └── diagnostics/      # Diagnostic tools
├── desktop/              # Desktop application (Phase 2)
│   ├── __init__.py
│   ├── api.py            # PyWebView API bridge
│   ├── ollama_manager.py # Ollama sidecar management
│   └── exceptions.py     # Desktop exceptions
├── analytics/            # Analytics module
├── frontend/techtime/    # Next.js frontend
├── prompts/              # Agent prompts
├── scripts/              # Build scripts (Phase 4)
├── tests/                # Test suite (Phase 5)
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
```

---

## Task 7.3: Create User Preferences System

### Purpose

Store user preferences (theme, model selection, window state) persistently.

### File: `backend/preferences.py`

```python
"""
User preferences management for TechTim(e).

Stores user preferences in a JSON file in the user data directory.
Preferences include:
- UI theme (light/dark/system)
- Selected model
- Window position and size
- Other user settings
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from .config import get_settings

logger = logging.getLogger("techtime.preferences")


@dataclass
class WindowState:
    """Window position and size."""
    x: int = 100
    y: int = 100
    width: int = 1200
    height: int = 800
    maximized: bool = False


@dataclass
class UserPreferences:
    """User preferences data structure."""
    
    # UI Settings
    theme: str = "system"  # "light", "dark", "system"
    
    # Model Settings
    preferred_model: str = ""  # Empty = use default from config
    
    # Window State
    window: WindowState = field(default_factory=WindowState)
    
    # Session Settings
    auto_save_sessions: bool = True
    confirm_delete_session: bool = True
    
    # Advanced
    debug_mode: bool = False
    show_tool_details: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserPreferences":
        """Create from dictionary."""
        window_data = data.pop("window", {})
        window = WindowState(**window_data)
        return cls(window=window, **data)


class PreferencesManager:
    """
    Manages loading and saving user preferences.
    
    Usage:
        prefs = PreferencesManager()
        
        # Get current preferences
        theme = prefs.get("theme")
        
        # Update a preference
        prefs.set("theme", "dark")
        
        # Save to disk
        prefs.save()
    """
    
    def __init__(self, preferences_file: Optional[Path] = None):
        """
        Initialize the preferences manager.
        
        Args:
            preferences_file: Path to preferences file (default: user_data/preferences.json)
        """
        settings = get_settings()
        
        if preferences_file:
            self._file = preferences_file
        else:
            self._file = settings.user_data_path / "preferences.json"
        
        self._preferences = self._load()
    
    def _load(self) -> UserPreferences:
        """Load preferences from disk."""
        if not self._file.exists():
            logger.info(f"No preferences file found, using defaults")
            return UserPreferences()
        
        try:
            with open(self._file, "r") as f:
                data = json.load(f)
            
            logger.debug(f"Loaded preferences from {self._file}")
            return UserPreferences.from_dict(data)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid preferences file, using defaults: {e}")
            return UserPreferences()
        except Exception as e:
            logger.warning(f"Failed to load preferences: {e}")
            return UserPreferences()
    
    def save(self) -> bool:
        """
        Save preferences to disk.
        
        Returns:
            True if save succeeded
        """
        try:
            # Ensure directory exists
            self._file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._file, "w") as f:
                json.dump(self._preferences.to_dict(), f, indent=2)
            
            logger.debug(f"Saved preferences to {self._file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a preference value.
        
        Args:
            key: Preference key (e.g., "theme", "window.width")
            default: Default value if not found
        
        Returns:
            Preference value
        """
        try:
            # Handle nested keys (e.g., "window.width")
            parts = key.split(".")
            value = self._preferences
            
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a preference value.
        
        Args:
            key: Preference key (e.g., "theme", "window.width")
            value: Value to set
        """
        try:
            parts = key.split(".")
            
            if len(parts) == 1:
                setattr(self._preferences, key, value)
            else:
                # Navigate to parent object
                obj = self._preferences
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], value)
            
            logger.debug(f"Set preference {key} = {value}")
            
        except Exception as e:
            logger.warning(f"Failed to set preference {key}: {e}")
    
    @property
    def all(self) -> UserPreferences:
        """Get all preferences."""
        return self._preferences
    
    def reset(self) -> None:
        """Reset all preferences to defaults."""
        self._preferences = UserPreferences()
        logger.info("Reset preferences to defaults")
    
    def update_window_state(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        maximized: Optional[bool] = None,
    ) -> None:
        """
        Update window state preferences.
        
        Args:
            x: Window x position
            y: Window y position
            width: Window width
            height: Window height
            maximized: Whether window is maximized
        """
        if x is not None:
            self._preferences.window.x = x
        if y is not None:
            self._preferences.window.y = y
        if width is not None:
            self._preferences.window.width = width
        if height is not None:
            self._preferences.window.height = height
        if maximized is not None:
            self._preferences.window.maximized = maximized


# Global instance
_preferences_manager: Optional[PreferencesManager] = None


def get_preferences() -> PreferencesManager:
    """Get the global preferences manager instance."""
    global _preferences_manager
    
    if _preferences_manager is None:
        _preferences_manager = PreferencesManager()
    
    return _preferences_manager
```

---

## Task 7.4: Add Preferences to Desktop API

### Purpose

Expose preferences to the frontend through the PyWebView API bridge.

### File: `desktop/api.py` (additions)

Add these methods to the `TechTimApi` class:

```python
# Add to imports at top of desktop/api.py
from backend.preferences import get_preferences, UserPreferences

# Add to TechTimApi class:

    # =========================================================================
    # User Preferences
    # =========================================================================
    
    def get_preferences(self) -> dict:
        """
        Get all user preferences.
        
        Returns:
            API response with preferences object
        """
        try:
            prefs = get_preferences()
            return api_response(True, prefs.all.to_dict())
        except Exception as e:
            logger.exception("Error getting preferences")
            return api_response(False, error=str(e))
    
    def get_preference(self, key: str) -> dict:
        """
        Get a specific preference value.
        
        Args:
            key: Preference key (e.g., "theme", "window.width")
        
        Returns:
            API response with preference value
        """
        try:
            prefs = get_preferences()
            value = prefs.get(key)
            return api_response(True, {'key': key, 'value': value})
        except Exception as e:
            logger.exception(f"Error getting preference {key}")
            return api_response(False, error=str(e))
    
    def set_preference(self, key: str, value: Any) -> dict:
        """
        Set a preference value and save.
        
        Args:
            key: Preference key
            value: New value
        
        Returns:
            API response indicating success
        """
        try:
            prefs = get_preferences()
            prefs.set(key, value)
            prefs.save()
            return api_response(True, {'key': key, 'value': value})
        except Exception as e:
            logger.exception(f"Error setting preference {key}")
            return api_response(False, error=str(e))
    
    def save_window_state(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        maximized: bool = False,
    ) -> dict:
        """
        Save current window position and size.
        
        Called by frontend when window is moved/resized.
        
        Args:
            x: Window x position
            y: Window y position
            width: Window width
            height: Window height
            maximized: Whether window is maximized
        
        Returns:
            API response indicating success
        """
        try:
            prefs = get_preferences()
            prefs.update_window_state(x, y, width, height, maximized)
            prefs.save()
            return api_response(True, {'saved': True})
        except Exception as e:
            logger.exception("Error saving window state")
            return api_response(False, error=str(e))
    
    def reset_preferences(self) -> dict:
        """
        Reset all preferences to defaults.
        
        Returns:
            API response with default preferences
        """
        try:
            prefs = get_preferences()
            prefs.reset()
            prefs.save()
            return api_response(True, prefs.all.to_dict())
        except Exception as e:
            logger.exception("Error resetting preferences")
            return api_response(False, error=str(e))
```

---

## Task 7.5: Add Crash Recovery for Orphaned Ollama

### Purpose

Detect and clean up orphaned Ollama processes from previous crashes.

### File: `desktop/process_guard.py`

```python
"""
Process guard for managing orphaned processes.

When the desktop app crashes, it may leave Ollama running.
This module provides utilities to detect and clean up orphaned processes.
"""
import os
import sys
import signal
import logging
from pathlib import Path
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger("techtime.desktop.process_guard")


class ProcessGuard:
    """
    Manages a PID file to track the Ollama process we started.
    
    On startup, checks for orphaned processes from previous runs
    and cleans them up.
    """
    
    def __init__(self, name: str = "ollama"):
        """
        Initialize the process guard.
        
        Args:
            name: Process name for the PID file
        """
        self.name = name
        settings = get_settings()
        self._pid_file = settings.user_data_path / f".{name}.pid"
    
    def check_and_cleanup(self) -> bool:
        """
        Check for orphaned process and clean up if found.
        
        Returns:
            True if an orphan was found and cleaned up
        """
        if not self._pid_file.exists():
            return False
        
        try:
            pid = int(self._pid_file.read_text().strip())
            
            # Check if process is still running
            if self._is_process_running(pid):
                logger.warning(f"Found orphaned {self.name} process (PID {pid})")
                
                # Try to terminate it
                if self._terminate_process(pid):
                    logger.info(f"Terminated orphaned {self.name} process")
                    self._cleanup_pid_file()
                    return True
                else:
                    logger.error(f"Failed to terminate orphaned process {pid}")
            else:
                # Process is gone, just clean up PID file
                logger.debug(f"Stale PID file found, cleaning up")
                self._cleanup_pid_file()
                
        except ValueError:
            # Invalid PID in file
            logger.warning("Invalid PID file, cleaning up")
            self._cleanup_pid_file()
        except Exception as e:
            logger.error(f"Error checking for orphaned process: {e}")
        
        return False
    
    def register_pid(self, pid: int) -> None:
        """
        Register a PID for tracking.
        
        Args:
            pid: Process ID to track
        """
        try:
            self._pid_file.parent.mkdir(parents=True, exist_ok=True)
            self._pid_file.write_text(str(pid))
            logger.debug(f"Registered {self.name} PID: {pid}")
        except Exception as e:
            logger.warning(f"Failed to register PID: {e}")
    
    def unregister(self) -> None:
        """Remove the PID file (called on clean shutdown)."""
        self._cleanup_pid_file()
    
    def _cleanup_pid_file(self) -> None:
        """Remove the PID file."""
        try:
            if self._pid_file.exists():
                self._pid_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to remove PID file: {e}")
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running."""
        if sys.platform == 'win32':
            return self._is_running_windows(pid)
        else:
            return self._is_running_unix(pid)
    
    def _is_running_unix(self, pid: int) -> bool:
        """Check if process is running on Unix."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def _is_running_windows(self, pid: int) -> bool:
        """Check if process is running on Windows."""
        import ctypes
        
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        
        try:
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION,
                False,
                pid
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    
    def _terminate_process(self, pid: int) -> bool:
        """Terminate a process by PID."""
        try:
            if sys.platform == 'win32':
                # Windows
                import ctypes
                PROCESS_TERMINATE = 0x0001
                handle = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_TERMINATE,
                    False,
                    pid
                )
                if handle:
                    result = ctypes.windll.kernel32.TerminateProcess(handle, 1)
                    ctypes.windll.kernel32.CloseHandle(handle)
                    return bool(result)
            else:
                # Unix
                os.kill(pid, signal.SIGTERM)
                
                # Wait briefly for graceful shutdown
                import time
                for _ in range(10):
                    time.sleep(0.5)
                    if not self._is_running_unix(pid):
                        return True
                
                # Force kill if still running
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to terminate process {pid}: {e}")
            return False


# Convenience function
def cleanup_orphaned_ollama() -> bool:
    """
    Clean up any orphaned Ollama processes from previous crashes.
    
    Call this early in application startup.
    
    Returns:
        True if an orphan was found and cleaned up
    """
    guard = ProcessGuard("ollama")
    return guard.check_and_cleanup()
```

---

## Task 7.6: Update desktop_main.py with Polish Features

### Purpose

Integrate crash recovery, preferences, and window state management into the main entry point.

### File: `desktop_main.py` (updates)

Add these updates to the existing `desktop_main.py`:

```python
# Add to imports
from backend.preferences import get_preferences
from desktop.process_guard import cleanup_orphaned_ollama, ProcessGuard

# Update main() function:

def main():
    """Application entry point."""
    args = parse_args()
    settings = get_settings()
    
    # Setup logging
    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level, log_to_file=True)
    
    logger.info("=" * 60)
    logger.info("TechTim(e) Desktop Application Starting")
    logger.info("=" * 60)
    
    # NEW: Clean up any orphaned Ollama processes
    if cleanup_orphaned_ollama():
        logger.info("Cleaned up orphaned Ollama process from previous session")
    
    # Ensure directories exist
    settings.log_path.mkdir(parents=True, exist_ok=True)
    settings.models_path.mkdir(parents=True, exist_ok=True)
    
    # NEW: Load user preferences
    prefs = get_preferences()
    
    # Create managers
    ollama_manager = OllamaManager()
    process_guard = ProcessGuard("ollama")
    api = TechTimApi(ollama_manager)
    
    try:
        frontend_url = get_frontend_url(args.dev, args.port)
        logger.info(f"Loading frontend from: {frontend_url}")
        
        # NEW: Get window state from preferences
        window_prefs = prefs.all.window
        
        # Create window with saved position/size
        window = webview.create_window(
            title='TechTim(e)',
            url=frontend_url,
            js_api=api,
            x=window_prefs.x if not args.dev else None,
            y=window_prefs.y if not args.dev else None,
            width=window_prefs.width,
            height=window_prefs.height,
            min_size=(800, 600),
            confirm_close=True,
        )
        
        # NEW: Track Ollama PID when it starts
        original_start = ollama_manager.start
        
        async def tracked_start(*args, **kwargs):
            await original_start(*args, **kwargs)
            if ollama_manager.process:
                process_guard.register_pid(ollama_manager.process.pid)
        
        ollama_manager.start = tracked_start
        
        # Start webview
        webview.start(
            func=lambda: on_window_loaded(window, api),
            debug=args.debug or args.dev,
        )
        
    except FileNotFoundError as e:
        logger.error(str(e))
        # ... existing error handling ...
        
    finally:
        # NEW: Clean shutdown
        logger.info("Shutting down...")
        
        # Stop Ollama
        if ollama_manager.is_running():
            ollama_manager.stop()
        
        # Clean up PID file
        process_guard.unregister()
        
        # Save final window state would go here if we had access to window position
        # (PyWebView doesn't expose this easily, so we save on resize in frontend)
        
        logger.info("Shutdown complete")
```

---

## Task 7.7: Create Makefile for Common Operations

### Purpose

Provide convenient make targets for common development and build operations.

### File: `Makefile`

```makefile
# TechTim(e) Makefile
# Common operations for development, testing, and building

.PHONY: help install install-all dev dev-frontend dev-desktop build build-frontend build-app test lint clean

# Default target
help:
	@echo "TechTim(e) Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install backend dependencies"
	@echo "  make install-all    Install all dependencies (backend + frontend)"
	@echo ""
	@echo "Development:"
	@echo "  make dev            Run desktop app in dev mode"
	@echo "  make dev-frontend   Start frontend dev server only"
	@echo "  make dev-desktop    Start desktop app (--dev mode)"
	@echo "  make dev-server     Start FastAPI server"
	@echo ""
	@echo "Build:"
	@echo "  make build          Full production build"
	@echo "  make build-frontend Build frontend only"
	@echo "  make build-app      Build desktop app only (assumes frontend built)"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all tests"
	@echo "  make test-cov       Run tests with coverage"
	@echo ""
	@echo "Quality:"
	@echo "  make lint           Run linter"
	@echo "  make format         Format code"
	@echo "  make typecheck      Run type checker"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Remove build artifacts"
	@echo "  make clean-all      Remove all generated files"

# =============================================================================
# Setup
# =============================================================================

install:
	pip install -e ".[desktop,dev]"

install-all: install
	cd frontend/techtime && npm install

# =============================================================================
# Development
# =============================================================================

dev:
	@echo "Starting development environment..."
	@echo "Run 'make dev-frontend' in another terminal first!"
	python desktop_main.py --dev --debug

dev-frontend:
	cd frontend/techtime && npm run dev

dev-desktop:
	python desktop_main.py --dev --debug

dev-server:
	python -m uvicorn backend.main:app --reload --port 8000

# =============================================================================
# Build
# =============================================================================

build: build-frontend build-app
	@echo "Build complete! Output in dist/"

build-frontend:
	python scripts/build_frontend.py

build-app:
	python scripts/build_app.py --skip-frontend

download-ollama:
	python scripts/download_ollama.py

# =============================================================================
# Testing
# =============================================================================

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=backend --cov=desktop --cov=analytics --cov-report=html --cov-report=term
	@echo "Coverage report: htmlcov/index.html"

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

# =============================================================================
# Quality
# =============================================================================

lint:
	ruff check backend/ desktop/ analytics/

format:
	ruff format backend/ desktop/ analytics/

typecheck:
	mypy backend/ desktop/ --ignore-missing-imports

quality: lint typecheck

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf build/ dist/ *.egg-info/
	rm -rf frontend/techtime/out/
	rm -rf frontend/techtime/.next/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean
	rm -rf .venv/
	rm -rf frontend/techtime/node_modules/
	rm -rf resources/ollama/
	rm -rf htmlcov/
	rm -rf .coverage

# =============================================================================
# Distribution
# =============================================================================

dist-macos:
	python scripts/distribute_macos.py --dmg

dist-windows:
	python scripts/distribute_windows.py

dist: build dist-macos dist-windows
```

---

## Task 7.8: Create Final Verification Checklist

### Purpose

Provide a comprehensive checklist to verify the desktop application is complete and working.

### File: `docs/VERIFICATION_CHECKLIST.md`

```markdown
# TechTim(e) Desktop Application - Verification Checklist

Use this checklist to verify the desktop application is ready for release.

## Development Environment

- [ ] `pip install -e ".[all]"` completes without errors
- [ ] `cd frontend/techtime && npm install` completes without errors
- [ ] `pytest` passes all tests
- [ ] `ruff check .` passes without errors (or expected warnings only)

## Development Mode

- [ ] `npm run dev` starts frontend on http://localhost:3000
- [ ] `python desktop_main.py --dev` opens window loading from dev server
- [ ] Frontend hot reload works (change code, see update)
- [ ] Chrome DevTools accessible (right-click → Inspect)

## Static Build Mode

- [ ] `npm run build` creates `frontend/techtime/out/index.html`
- [ ] `python desktop_main.py` loads from static files
- [ ] All pages render correctly

## Desktop Application Features

### Startup
- [ ] Loading screen shows during initialization
- [ ] Progress bar updates during model download (if needed)
- [ ] Error messages display properly if startup fails
- [ ] Application reaches ready state

### Chat
- [ ] Can start new conversation
- [ ] Messages send and receive
- [ ] Tool calls display in UI
- [ ] Tool results show success/failure
- [ ] Streaming responses work
- [ ] Conversation history persists after restart

### Sessions
- [ ] Session list shows in sidebar
- [ ] Can switch between sessions
- [ ] Can delete sessions
- [ ] Session preview shows first message

### Tools
- [ ] Manual tool panel lists all tools
- [ ] Can execute tools manually
- [ ] Tool results display correctly

### Analytics
- [ ] Analytics dashboard shows data
- [ ] Session counts are accurate
- [ ] Tool statistics display

### Preferences
- [ ] Theme selection persists
- [ ] Window position saves on close
- [ ] Window opens at saved position

## Build Process

- [ ] `python scripts/download_ollama.py` downloads binaries
- [ ] `python scripts/build_frontend.py` builds frontend
- [ ] `python scripts/build_app.py` completes without errors
- [ ] `dist/TechTime/` (or `.app`) is created

## Bundled Application

### macOS
- [ ] `dist/TechTime.app` launches
- [ ] Ollama starts automatically
- [ ] Model downloads if needed
- [ ] Chat works
- [ ] No console window appears

### Windows
- [ ] `dist/TechTime/TechTime.exe` launches
- [ ] Ollama starts automatically
- [ ] Model downloads if needed
- [ ] Chat works
- [ ] No console window appears

## Edge Cases

- [ ] Handles Ollama not found gracefully
- [ ] Handles model not available gracefully
- [ ] Handles network errors gracefully
- [ ] Clean shutdown (no orphaned processes)
- [ ] Crash recovery cleans up orphaned Ollama

## Distribution

### macOS
- [ ] `python scripts/distribute_macos.py --dmg` creates DMG
- [ ] DMG mounts and shows app
- [ ] App runs from Applications folder

### Windows
- [ ] `python scripts/distribute_windows.py` creates installer
- [ ] Installer runs and installs app
- [ ] App runs from Start Menu
- [ ] Uninstaller works

## Documentation

- [ ] README.md is up to date
- [ ] DEVELOPMENT.md explains workflow
- [ ] DISTRIBUTION.md explains release process
- [ ] All phases documented in temp/phase*_updated.md
```

---

## Acceptance Criteria

Phase 7 is complete when:

1. **Dependencies documented**: `pyproject.toml` includes all desktop dependencies
2. **Development workflow works**: Can run in dev mode with hot reload
3. **Preferences persist**: Theme, window state, and settings save/load correctly
4. **Crash recovery works**: Orphaned Ollama processes are cleaned up on startup
5. **Makefile provides shortcuts**: Common operations are one command
6. **Verification checklist passes**: All items checked off

---

## Files Created/Modified Summary

| File | Description |
|------|-------------|
| `pyproject.toml` | Updated with desktop dependencies |
| `docs/DEVELOPMENT.md` | Development workflow guide |
| `docs/VERIFICATION_CHECKLIST.md` | Release readiness checklist |
| `backend/preferences.py` | User preferences manager |
| `desktop/process_guard.py` | Orphaned process cleanup |
| `desktop/api.py` | Added preferences API methods |
| `desktop_main.py` | Added crash recovery, preferences |
| `Makefile` | Development shortcuts |

---

## Summary

Phase 7 completes the desktop application by:

1. **Formalizing dependencies** in `pyproject.toml`
2. **Documenting development workflow** for contributors
3. **Adding user preferences** that persist between sessions
4. **Implementing crash recovery** to clean up orphaned processes
5. **Creating a Makefile** for convenient development
6. **Providing verification checklists** for release confidence

After completing Phase 7, the TechTim(e) desktop application is ready for testing and distribution.

