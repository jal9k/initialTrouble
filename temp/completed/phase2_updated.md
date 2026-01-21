# Phase 2: Desktop Application Layer (UPDATED)

## CHANGES FROM ORIGINAL

This document has been updated to match the actual TechTim(e) codebase structure and patterns.

| Task | Original Approach | Updated Approach | Reason |
|------|-------------------|------------------|--------|
| 2.2 Ollama Manager | Basic implementation | Kept mostly same | Good as-is |
| 2.3 API Bridge | `execute(name, args)` | `execute(tool_call)` | Match actual ToolRegistry.execute() signature |
| 2.3 API Bridge | Generic ChatService | Use ChatService with analytics | Integrate with existing analytics patterns |
| 2.3 API Bridge | `from backend.analytics` | `from analytics import` | Analytics is top-level module |
| 2.4 Main Entry | Generic initialization | Match main.py patterns | Use existing `register_all_diagnostics()` |
| 2.4 Main Entry | No analytics | Full analytics setup | Match existing FastAPI startup |

---

## Objective

Create the desktop application infrastructure that manages the Ollama sidecar process and exposes the backend functionality to the PyWebView frontend through a JavaScript-callable API bridge.

## Prerequisites

Before starting this phase, ensure you have:
- Phase 1 completed (backend modifications)
- Python 3.11+ with the following packages installed:
  - `pywebview>=5.0`
  - `httpx`
- Ollama installed on your development machine (for testing)

Install PyWebView:
```bash
pip install pywebview httpx
```

---

## Task 2.1: Create Desktop Package Structure

### Purpose

Establish a dedicated package for desktop-specific code, keeping it separate from the backend logic. This package will contain the Ollama manager, PyWebView API bridge, and application entry point.

### Directory Structure

Create the following directory structure:

```
desktop/
├── __init__.py
├── api.py              # PyWebView API bridge
├── ollama_manager.py   # Ollama sidecar lifecycle
└── exceptions.py       # Desktop-specific exceptions
```

### File: `desktop/__init__.py`

```python
"""
TechTim(e) Desktop Application Package.

This package contains components specific to the desktop deployment:
- Ollama sidecar process management
- PyWebView API bridge
- Application lifecycle management
"""

__version__ = "1.0.0"
```

### File: `desktop/exceptions.py`

```python
"""Desktop-specific exceptions."""


class DesktopError(Exception):
    """Base exception for desktop application errors."""
    pass


class OllamaError(DesktopError):
    """Base exception for Ollama-related errors."""
    pass


class OllamaStartupError(OllamaError):
    """Raised when Ollama fails to start."""
    pass


class OllamaNotFoundError(OllamaError):
    """Raised when the Ollama binary cannot be found."""
    pass


class InitializationError(DesktopError):
    """Raised when application initialization fails."""
    pass
```

---

## Task 2.2: Create the Ollama Sidecar Manager

### Purpose

The Ollama manager handles finding, starting, monitoring, and stopping the Ollama server process. In bundled mode, it uses the Ollama binary shipped with the application. In development, it can use a system-installed Ollama.

### File: `desktop/ollama_manager.py`

```python
"""
Manages the Ollama server as a child process.

Ollama is bundled with the application and spawned on startup.
This manager handles:
- Locating the correct binary for the current platform
- Starting Ollama with appropriate environment variables
- Health checking to confirm it's ready
- Graceful shutdown on application exit

Example:
    manager = OllamaManager()
    await manager.start()
    
    # Application runs...
    
    manager.stop()
"""
import sys
import os
import subprocess
import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable
import json

import httpx

from backend.config import get_settings
from .exceptions import OllamaError, OllamaStartupError, OllamaNotFoundError

logger = logging.getLogger("techtime.desktop.ollama")


class OllamaManager:
    """
    Manages the Ollama sidecar process lifecycle.
    
    This class is responsible for:
    - Finding the Ollama binary (bundled or system)
    - Starting Ollama with correct environment
    - Health checking to ensure it's ready
    - Downloading models if needed
    - Graceful shutdown
    
    Attributes:
        process: The subprocess.Popen instance (None if not started)
        host: The host Ollama binds to
        port: The port Ollama listens on
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 11434):
        """
        Initialize the Ollama manager.
        
        Args:
            host: Host to bind Ollama to (default localhost)
            port: Port for Ollama API (default 11434)
        """
        self._settings = get_settings()
        self.process: Optional[subprocess.Popen] = None
        self.host = host
        self.port = port
        self._started = False
        self._owns_process = False  # True if we started Ollama ourselves
    
    @property
    def base_url(self) -> str:
        """Get the Ollama API base URL."""
        return f"http://{self.host}:{self.port}"
    
    def get_ollama_binary_path(self) -> Path:
        """
        Find the Ollama binary for the current platform.
        
        Search order:
        1. Bundled binary in resources/ollama/{platform}/
        2. System-installed Ollama in PATH
        
        Returns:
            Path to the Ollama executable
        
        Raises:
            OllamaNotFoundError: If no Ollama binary is found
        """
        # Determine platform-specific directory and binary name
        if sys.platform == 'darwin':
            import platform
            arch = 'arm64' if platform.machine() == 'arm64' else 'x64'
            platform_dir = f'darwin-{arch}'
            binary_name = 'ollama'
        elif sys.platform == 'win32':
            platform_dir = 'win32-x64'
            binary_name = 'ollama.exe'
        else:
            # Linux
            platform_dir = 'linux-x64'
            binary_name = 'ollama'
        
        # Check bundled location (PyInstaller mode)
        if self._settings.bundled_mode:
            bundled_path = self._settings.base_path / 'resources' / 'ollama' / platform_dir / binary_name
            if bundled_path.exists():
                logger.info(f"Using bundled Ollama: {bundled_path}")
                return bundled_path
        
        # Check development resources directory
        dev_resources = Path(__file__).parent.parent / 'resources' / 'ollama' / platform_dir / binary_name
        if dev_resources.exists():
            logger.info(f"Using development Ollama: {dev_resources}")
            return dev_resources
        
        # Fallback to system-installed Ollama
        import shutil
        system_ollama = shutil.which('ollama')
        if system_ollama:
            logger.info(f"Using system Ollama: {system_ollama}")
            return Path(system_ollama)
        
        raise OllamaNotFoundError(
            f"Ollama binary not found.\n"
            f"Searched locations:\n"
            f"  - {self._settings.base_path / 'resources' / 'ollama' / platform_dir / binary_name}\n"
            f"  - {dev_resources}\n"
            f"  - System PATH\n\n"
            f"Run 'python scripts/download_ollama.py' to download Ollama binaries,\n"
            f"or install Ollama system-wide from https://ollama.ai"
        )
    
    def _build_environment(self) -> dict:
        """
        Build environment variables for the Ollama process.
        
        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()
        
        # Set Ollama-specific variables
        env['OLLAMA_HOST'] = f"{self.host}:{self.port}"
        env['OLLAMA_MODELS'] = str(self._settings.models_path)
        
        # Disable update checks in bundled mode
        if self._settings.bundled_mode:
            env['OLLAMA_NOPRUNE'] = '1'
        
        # Ensure UTF-8 encoding on Windows
        if sys.platform == 'win32':
            env['PYTHONIOENCODING'] = 'utf-8'
        
        return env
    
    async def _is_healthy(self) -> bool:
        """
        Check if Ollama is responding to API requests.
        
        Returns:
            True if Ollama is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=2.0,
                )
                return response.status_code == 200
        except (httpx.RequestError, httpx.TimeoutException):
            return False
    
    async def start(self, timeout: float = 30.0) -> None:
        """
        Start the Ollama server and wait for it to be ready.
        
        If Ollama is already running (e.g., system instance), this method
        will detect that and skip starting a new process.
        
        Args:
            timeout: Maximum seconds to wait for Ollama to start
        
        Raises:
            OllamaStartupError: If Ollama fails to start within timeout
            OllamaNotFoundError: If Ollama binary cannot be found
        """
        if self._started:
            logger.debug("Ollama already started")
            return
        
        # Check if Ollama is already running
        if await self._is_healthy():
            logger.info("Ollama is already running, using existing instance")
            self._started = True
            self._owns_process = False
            return
        
        # Find and start Ollama
        binary_path = self.get_ollama_binary_path()
        logger.info(f"Starting Ollama from: {binary_path}")
        
        # Ensure models directory exists
        self._settings.models_path.mkdir(parents=True, exist_ok=True)
        
        # Build subprocess creation flags
        creation_flags = 0
        if sys.platform == 'win32':
            # Don't create a console window on Windows
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        # Start Ollama serve process
        try:
            self.process = subprocess.Popen(
                [str(binary_path), 'serve'],
                env=self._build_environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags,
            )
        except OSError as e:
            raise OllamaStartupError(f"Failed to start Ollama: {e}")
        
        self._owns_process = True
        
        # Wait for Ollama to become healthy
        logger.info(f"Waiting for Ollama to be ready (timeout: {timeout}s)...")
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check health
            if await self._is_healthy():
                logger.info("Ollama is ready")
                self._started = True
                return
            
            # Check if process died
            if self.process.poll() is not None:
                # Process exited
                stderr_output = ""
                if self.process.stderr:
                    stderr_output = self.process.stderr.read().decode(errors='replace')
                
                raise OllamaStartupError(
                    f"Ollama process exited unexpectedly with code {self.process.returncode}\n"
                    f"stderr: {stderr_output}"
                )
            
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                self.stop()
                raise OllamaStartupError(
                    f"Ollama failed to start within {timeout} seconds"
                )
            
            # Wait before next check
            await asyncio.sleep(0.5)
    
    async def list_models(self) -> list[dict]:
        """
        Get list of downloaded models.
        
        Returns:
            List of model info dictionaries with keys:
            - name: Model name (e.g., "mistral:7b-instruct")
            - size: Size in bytes
            - modified_at: Last modified timestamp
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get('models', [])
    
    async def has_model(self, model_name: str) -> bool:
        """
        Check if a specific model is downloaded.
        
        Args:
            model_name: Model identifier (e.g., "mistral:7b-instruct")
        
        Returns:
            True if model is available locally
        """
        models = await self.list_models()
        
        # Handle both exact match and base name match
        # e.g., "mistral" should match "mistral:7b-instruct"
        base_name = model_name.split(':')[0]
        
        for model in models:
            model_base = model['name'].split(':')[0]
            if model['name'] == model_name or model_base == base_name:
                return True
        
        return False
    
    async def pull_model(
        self,
        model_name: str,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> None:
        """
        Download a model from the Ollama registry.
        
        Args:
            model_name: Model to download (e.g., "mistral:7b-instruct")
            on_progress: Optional callback for progress updates.
                         Receives dict with 'status', 'completed', 'total' keys.
        
        Raises:
            httpx.HTTPError: If the download fails
        """
        logger.info(f"Pulling model: {model_name}")
        
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                'POST',
                f"{self.base_url}/api/pull",
                json={'name': model_name, 'stream': True},
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    # Call progress callback
                    if on_progress:
                        on_progress({
                            'status': data.get('status', ''),
                            'completed': data.get('completed', 0),
                            'total': data.get('total', 0),
                            'digest': data.get('digest', ''),
                        })
                    
                    # Check for completion
                    if data.get('status') == 'success':
                        logger.info(f"Model {model_name} downloaded successfully")
                        return
        
        logger.info(f"Model pull completed: {model_name}")
    
    async def delete_model(self, model_name: str) -> bool:
        """
        Delete a downloaded model.
        
        Args:
            model_name: Model to delete
        
        Returns:
            True if deleted, False if not found
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/delete",
                json={'name': model_name},
            )
            return response.status_code == 200
    
    def stop(self) -> None:
        """
        Stop the Ollama server gracefully.
        
        This only stops Ollama if we started it ourselves.
        """
        if self.process is None or not self._owns_process:
            logger.debug("No Ollama process to stop")
            self._started = False
            return
        
        logger.info("Stopping Ollama...")
        
        # Try graceful termination
        self.process.terminate()
        
        try:
            # Wait up to 5 seconds for graceful shutdown
            self.process.wait(timeout=5.0)
            logger.info("Ollama stopped gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't stop
            logger.warning("Ollama didn't stop gracefully, killing...")
            self.process.kill()
            self.process.wait()
            logger.info("Ollama killed")
        
        self.process = None
        self._started = False
        self._owns_process = False
    
    def is_running(self) -> bool:
        """
        Check if Ollama is currently running.
        
        Returns:
            True if Ollama is running
        """
        return self._started
    
    def __del__(self):
        """Ensure Ollama is stopped when manager is garbage collected."""
        self.stop()


# Convenience function for quick health check
async def check_ollama_available(host: str = "127.0.0.1", port: int = 11434) -> bool:
    """
    Quick check if Ollama is available.
    
    Args:
        host: Ollama host
        port: Ollama port
    
    Returns:
        True if Ollama is responding
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{host}:{port}/api/tags",
                timeout=2.0,
            )
            return response.status_code == 200
    except Exception:
        return False
```

### Verification Steps

Test the Ollama manager:

```python
# test_ollama_manager.py
import asyncio
from desktop.ollama_manager import OllamaManager, check_ollama_available

async def test():
    # Quick availability check
    available = await check_ollama_available()
    print(f"Ollama already available: {available}")
    
    # Test manager
    manager = OllamaManager()
    
    try:
        # Find binary
        binary = manager.get_ollama_binary_path()
        print(f"Found Ollama at: {binary}")
        
        # Start (or connect to existing)
        await manager.start(timeout=30)
        print("Ollama started successfully")
        
        # List models
        models = await manager.list_models()
        print(f"Available models: {[m['name'] for m in models]}")
        
    finally:
        manager.stop()

asyncio.run(test())
```

---

## Task 2.3: Create the PyWebView API Bridge

### Purpose

The API bridge exposes Python functions to JavaScript. Each public method becomes callable from the frontend as `window.pywebview.api.method_name()`.

### File: `desktop/api.py`

**IMPORTANT:** This version integrates with the actual TechTim(e) patterns:
- Uses `ChatService` from Phase 1
- Imports analytics from top-level `analytics/` module
- Uses correct `ToolRegistry.execute(tool_call)` signature
- Integrates with existing session persistence

```python
"""
PyWebView API bridge for the TechTim(e) desktop application.

This class is exposed to JavaScript as window.pywebview.api.
All public methods can be called from the frontend.

Threading note: PyWebView calls these methods from a background thread,
not the main thread. We use asyncio.new_event_loop() to run async code.

Example usage from JavaScript:
    const result = await window.pywebview.api.send_message('session-123', 'Hello');
    console.log(result.data.content);
"""
import asyncio
import uuid
import json
import logging
from typing import Optional, Any
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.config import get_settings
from backend.chat_service import ChatService, StreamChunk
from backend.tools import get_registry, ToolCall
from backend.tools.schemas import ToolCall as ToolCallSchema

# Import from top-level analytics module (NOT backend.analytics)
from analytics import AnalyticsCollector, AnalyticsStorage

from .ollama_manager import OllamaManager

logger = logging.getLogger("techtime.desktop.api")


def api_response(success: bool, data: Any = None, error: str = None) -> dict:
    """Helper to create API response dictionaries."""
    return {
        'success': success,
        'data': data,
        'error': error,
    }


class TechTimApi:
    """
    API exposed to the PyWebView frontend.
    
    Every public method (not starting with _) is callable from JavaScript:
        window.pywebview.api.method_name(args...)
    
    Methods should return dictionaries that will be JSON-serialized.
    Use the api_response helper for consistent response format.
    
    Threading: Methods are called from PyWebView's background thread.
    Use _run_async() to execute async code.
    """
    
    def __init__(self, ollama_manager: OllamaManager):
        """
        Initialize the API bridge.
        
        Args:
            ollama_manager: The Ollama sidecar manager instance
        """
        self._settings = get_settings()
        self.ollama = ollama_manager
        
        # Initialize analytics (matching main.py pattern)
        db_path = self._settings.database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._analytics_storage = AnalyticsStorage(db_path)
        self._analytics_collector = AnalyticsCollector(storage=self._analytics_storage)
        
        # Initialize chat service with analytics
        self.chat_service = ChatService(
            analytics_collector=self._analytics_collector,
            analytics_storage=self._analytics_storage,
        )
        
        # Tool registry
        self.tool_registry = get_registry()
        
        self._window = None  # Set after window creation
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._initialized = False
        
        logger.info("TechTimApi created")
    
    async def _initialize(self) -> None:
        """Initialize the chat service and tools."""
        if self._initialized:
            return
        
        await self.chat_service.initialize()
        self._initialized = True
        logger.info("TechTimApi initialized")
    
    def set_window(self, window) -> None:
        """
        Set the PyWebView window reference.
        
        This is called after window creation to enable JavaScript callbacks.
        
        Args:
            window: The pywebview.Window instance
        """
        self._window = window
        logger.debug("Window reference set")
    
    def _run_async(self, coro):
        """
        Run an async coroutine from synchronous context.
        
        PyWebView calls methods synchronously, but our backend uses async.
        This helper bridges the gap by creating a new event loop.
        
        Args:
            coro: The coroutine to run
        
        Returns:
            The coroutine's result
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def _call_js(self, js_code: str) -> None:
        """
        Execute JavaScript in the webview.
        
        Args:
            js_code: JavaScript code to execute
        """
        if self._window:
            self._window.evaluate_js(js_code)
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    def create_session(self) -> dict:
        """
        Create a new chat session.
        
        Returns:
            API response with session_id in data
        """
        try:
            session_id = str(uuid.uuid4())
            return api_response(True, {'session_id': session_id})
        except Exception as e:
            logger.exception("Error creating session")
            return api_response(False, error=str(e))
    
    def list_sessions(self) -> dict:
        """
        Get all sessions from the database.
        
        Returns:
            API response with list of session summaries
        """
        try:
            # Use analytics storage to get persisted sessions
            sessions = self._analytics_storage.get_sessions(limit=50)
            
            session_list = [
                {
                    "id": s.session_id,
                    "startTime": s.started_at.isoformat(),
                    "outcome": s.outcome.value,
                    "issueCategory": s.issue_category.value if s.issue_category.value != "unknown" else None,
                    "preview": s.preview or "New conversation...",
                    "message_count": s.message_count,
                }
                for s in sessions
            ]
            
            return api_response(True, session_list)
        except Exception as e:
            logger.exception("Error listing sessions")
            return api_response(False, error=str(e))
    
    def get_session_messages(self, session_id: str) -> dict:
        """
        Get message history for a session from the database.
        
        Args:
            session_id: The session to retrieve
        
        Returns:
            API response with list of messages
        """
        try:
            # Get persisted messages from database
            db_messages = self._analytics_storage.get_messages(session_id)
            
            messages = []
            for msg in db_messages:
                if msg.role == "system":
                    continue  # Skip system messages
                messages.append({
                    "id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                })
            
            return api_response(True, messages)
        except Exception as e:
            logger.exception(f"Error getting messages for session {session_id}")
            return api_response(False, error=str(e))
    
    def delete_session(self, session_id: str) -> dict:
        """
        Delete a chat session from the database.
        
        Args:
            session_id: The session to delete
        
        Returns:
            API response indicating success/failure
        """
        try:
            # Delete from database
            success = self._analytics_storage.delete_session(session_id)
            
            # Also delete from in-memory chat service
            self.chat_service.delete_session(session_id)
            
            if success:
                return api_response(True)
            return api_response(False, error='Session not found')
        except Exception as e:
            logger.exception(f"Error deleting session {session_id}")
            return api_response(False, error=str(e))
    
    # =========================================================================
    # Chat Operations
    # =========================================================================
    
    def send_message(self, session_id: str, message: str) -> dict:
        """
        Send a message and get the complete response.
        
        This is the non-streaming version. It blocks until the LLM
        finishes and all tools have executed.
        
        Args:
            session_id: The conversation session
            message: User's input message
        
        Returns:
            API response with content and tool_results
        """
        async def _send():
            await self._initialize()
            response = await self.chat_service.chat(session_id, message)
            return response.to_dict()
        
        try:
            result = self._run_async(_send())
            return api_response(True, result)
        except Exception as e:
            logger.exception("Error in send_message")
            return api_response(False, error=str(e))
    
    def send_message_streaming(self, session_id: str, message: str) -> dict:
        """
        Send a message with streaming response.
        
        Returns immediately and sends chunks to frontend via callbacks.
        
        The frontend should set up these listeners before calling:
            window.onStreamChunk = (chunk) => { ... };
            window.onStreamDone = () => { ... };
            window.onStreamError = (error) => { ... };
        
        Args:
            session_id: The conversation session
            message: User's input message
        
        Returns:
            API response indicating stream has started
        """
        def on_chunk(chunk: StreamChunk):
            """Send each chunk to the frontend."""
            if self._window:
                chunk_json = json.dumps({
                    'type': chunk.type,
                    'data': chunk.data,
                })
                self._call_js(f'window.onStreamChunk && window.onStreamChunk({chunk_json})')
        
        def run_stream():
            """Background task for streaming."""
            async def _stream():
                try:
                    await self._initialize()
                    await self.chat_service.chat_stream(
                        session_id,
                        message,
                        on_chunk=on_chunk,
                    )
                except Exception as e:
                    logger.exception("Stream error")
                    if self._window:
                        error_json = json.dumps(str(e))
                        self._call_js(f'window.onStreamError && window.onStreamError({error_json})')
                finally:
                    if self._window:
                        self._call_js('window.onStreamDone && window.onStreamDone()')
            
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_stream())
            finally:
                loop.close()
        
        # Run in background thread
        self._executor.submit(run_stream)
        
        return api_response(True, {'status': 'streaming_started'})
    
    # =========================================================================
    # Tool Operations
    # =========================================================================
    
    def list_tools(self) -> dict:
        """
        Get available diagnostic tools.
        
        Returns:
            API response with list of tool definitions
        """
        try:
            tools = self.tool_registry.get_all_definitions()
            tool_list = [
                {
                    'name': t.name,
                    'description': t.description,
                    'parameters': [
                        {
                            'name': p.name,
                            'type': p.type,
                            'description': p.description,
                            'required': p.required,
                        }
                        for p in t.parameters
                    ],
                }
                for t in tools
            ]
            return api_response(True, tool_list)
        except Exception as e:
            logger.exception("Error listing tools")
            return api_response(False, error=str(e))
    
    def execute_tool(self, name: str, arguments: dict) -> dict:
        """
        Manually execute a diagnostic tool.
        
        Args:
            name: Tool name (e.g., 'ping_gateway')
            arguments: Tool parameters as dictionary
        
        Returns:
            API response with tool result
        """
        async def _execute():
            # Create a ToolCall object (matching actual ToolRegistry.execute signature)
            tool_call = ToolCallSchema(
                id=f"manual-{uuid.uuid4().hex[:8]}",
                name=name,
                arguments=arguments,
            )
            
            result = await self.tool_registry.execute(tool_call)
            return {
                'success': result.success,
                'content': result.content,
            }
        
        try:
            result = self._run_async(_execute())
            return api_response(True, result)
        except Exception as e:
            logger.exception(f"Error executing tool {name}")
            return api_response(False, error=str(e))
    
    # =========================================================================
    # Model Management
    # =========================================================================
    
    def list_models(self) -> dict:
        """
        Get downloaded Ollama models.
        
        Returns:
            API response with list of model info
        """
        try:
            models = self._run_async(self.ollama.list_models())
            return api_response(True, models)
        except Exception as e:
            logger.exception("Error listing models")
            return api_response(False, error=str(e))
    
    def check_model_status(self) -> dict:
        """
        Check if the configured model is available.
        
        Returns:
            API response with model availability status
        """
        try:
            has_model = self._run_async(
                self.ollama.has_model(self._settings.ollama_model)
            )
            return api_response(True, {
                'model': self._settings.ollama_model,
                'available': has_model,
            })
        except Exception as e:
            logger.exception("Error checking model status")
            return api_response(False, error=str(e))
    
    def download_model(self, model_name: str) -> dict:
        """
        Start downloading a model.
        
        Progress is sent via window.onModelProgress callback.
        Completion is signaled via window.onModelDownloadComplete callback.
        
        Args:
            model_name: Model to download (e.g., 'mistral:7b-instruct')
        
        Returns:
            API response indicating download started
        """
        def on_progress(progress: dict):
            """Send progress to frontend."""
            if self._window:
                progress_json = json.dumps(progress)
                self._call_js(f'window.onModelProgress && window.onModelProgress({progress_json})')
        
        def run_download():
            """Background download task."""
            try:
                self._run_async(self.ollama.pull_model(model_name, on_progress))
                if self._window:
                    self._call_js(f'window.onModelDownloadComplete && window.onModelDownloadComplete("{model_name}")')
            except Exception as e:
                logger.exception(f"Error downloading model {model_name}")
                if self._window:
                    error_json = json.dumps(str(e))
                    self._call_js(f'window.onModelDownloadError && window.onModelDownloadError({error_json})')
        
        self._executor.submit(run_download)
        
        return api_response(True, {
            'status': 'download_started',
            'model': model_name,
        })
    
    # =========================================================================
    # System Information
    # =========================================================================
    
    def get_app_info(self) -> dict:
        """
        Get application information.
        
        Returns:
            API response with version, paths, and status
        """
        try:
            return api_response(True, {
                'version': '1.0.0',
                'bundled_mode': self._settings.bundled_mode,
                'ollama_host': self._settings.ollama_host,
                'configured_model': self._settings.ollama_model,
                'user_data_path': str(self._settings.user_data_path),
                'ollama_running': self.ollama.is_running(),
            })
        except Exception as e:
            logger.exception("Error getting app info")
            return api_response(False, error=str(e))
    
    def get_diagnostics(self) -> dict:
        """
        Get diagnostic information for troubleshooting.
        
        Returns:
            API response with system diagnostics
        """
        import sys
        import platform
        
        try:
            return api_response(True, {
                'python_version': sys.version,
                'platform': platform.platform(),
                'machine': platform.machine(),
                'bundled_mode': self._settings.bundled_mode,
                'base_path': str(self._settings.base_path),
                'user_data_path': str(self._settings.user_data_path),
                'database_path': str(self._settings.database_path),
                'models_path': str(self._settings.models_path),
                'ollama_host': self._settings.ollama_host,
                'ollama_running': self.ollama.is_running(),
                'tools_count': len(self.tool_registry),
            })
        except Exception as e:
            logger.exception("Error getting diagnostics")
            return api_response(False, error=str(e))
    
    # =========================================================================
    # Analytics (matching existing API)
    # =========================================================================
    
    def get_analytics_summary(self) -> dict:
        """
        Get session analytics summary.
        
        Returns:
            API response with analytics summary
        """
        try:
            summary = self._analytics_storage.get_session_summary()
            return api_response(True, {
                'total_sessions': summary.total_sessions,
                'resolved_count': summary.resolved_count,
                'unresolved_count': summary.unresolved_count,
                'abandoned_count': summary.abandoned_count,
                'in_progress_count': summary.in_progress_count,
                'avg_messages_per_session': summary.avg_messages_per_session,
                'total_cost_usd': summary.total_cost_usd,
            })
        except Exception as e:
            logger.exception("Error getting analytics summary")
            return api_response(False, error=str(e))
    
    def get_tool_stats(self) -> dict:
        """
        Get tool usage statistics.
        
        Returns:
            API response with tool stats
        """
        try:
            stats = self._analytics_storage.get_tool_stats()
            return api_response(True, [
                {
                    'tool_name': s.tool_name,
                    'total_calls': s.total_calls,
                    'success_count': s.success_count,
                    'failure_count': s.failure_count,
                    'avg_execution_time_ms': s.avg_execution_time_ms,
                }
                for s in stats
            ])
        except Exception as e:
            logger.exception("Error getting tool stats")
            return api_response(False, error=str(e))
```

### Verification Steps

The API can't be fully tested without PyWebView, but you can test the non-window methods:

```python
# test_api.py
from desktop.ollama_manager import OllamaManager
from desktop.api import TechTimApi

# Create manager (don't start Ollama yet)
manager = OllamaManager()
api = TechTimApi(manager)

# Test session creation
result = api.create_session()
print(f"Create session: {result}")

# Test listing
result = api.list_sessions()
print(f"List sessions: {result}")

# Test tools
result = api.list_tools()
print(f"Tools available: {len(result['data'])} tools")

# Test app info
result = api.get_app_info()
print(f"App info: {result}")

# Test analytics
result = api.get_analytics_summary()
print(f"Analytics: {result}")
```

---

## Task 2.4: Create the Main Entry Point

### Purpose

The main entry point ties everything together: starts Ollama, ensures the model is downloaded, creates the PyWebView window, and handles graceful shutdown.

### File: `desktop_main.py` (in project root)

**Note:** Named `desktop_main.py` to avoid confusion with `main.py` (FastAPI server).

```python
"""
TechTim(e) Desktop Application Entry Point

This script:
1. Configures logging
2. Starts the Ollama sidecar
3. Ensures the required model is downloaded
4. Creates the PyWebView window with the frontend
5. Handles graceful shutdown on exit

Usage:
    python desktop_main.py          # Normal mode
    python desktop_main.py --dev    # Development mode (uses Next.js dev server)
"""
import sys
import asyncio
import logging
import argparse
import threading
from pathlib import Path

import webview

from backend.config import get_settings
from backend.logging_config import setup_logging
from desktop.ollama_manager import OllamaManager
from desktop.api import TechTimApi
from desktop.exceptions import OllamaNotFoundError, OllamaStartupError

logger = logging.getLogger("techtime.desktop")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='TechTim(e) Desktop Application')
    parser.add_argument(
        '--dev',
        action='store_true',
        help='Development mode: use Next.js dev server instead of static files'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with verbose logging'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=3000,
        help='Port for Next.js dev server (default: 3000)'
    )
    return parser.parse_args()


def get_frontend_url(dev_mode: bool, port: int = 3000) -> str:
    """
    Get the URL or path to load in the webview.
    
    Args:
        dev_mode: If True, use Next.js dev server
        port: Port for Next.js dev server
    
    Returns:
        URL string or file path
    """
    settings = get_settings()
    
    if dev_mode:
        # Development: connect to Next.js dev server
        return f'http://localhost:{port}'
    
    # Production: load static files
    if settings.bundled_mode:
        # PyInstaller bundle
        frontend_path = settings.base_path / 'frontend' / 'out' / 'index.html'
    else:
        # Development with static build
        frontend_path = Path(__file__).parent / 'frontend' / 'techtime' / 'out' / 'index.html'
    
    if not frontend_path.exists():
        raise FileNotFoundError(
            f"Frontend not found at {frontend_path}\n\n"
            f"To fix this, either:\n"
            f"  1. Run in dev mode: python desktop_main.py --dev\n"
            f"  2. Build the frontend: cd frontend/techtime && npm run build\n"
        )
    
    return str(frontend_path)


async def initialize_app(
    api: TechTimApi,
    window: webview.Window,
) -> bool:
    """
    Initialize the application after window is created.
    
    This runs asynchronously while a loading screen is shown.
    
    Args:
        api: The API bridge instance
        window: The PyWebView window
    
    Returns:
        True if initialization succeeded, False otherwise
    """
    settings = get_settings()
    
    def update_status(message: str):
        """Update the loading status in the frontend."""
        logger.info(f"Status: {message}")
        window.evaluate_js(f'window.setLoadingStatus && window.setLoadingStatus("{message}")')
    
    def update_progress(percent: int, message: str):
        """Update the loading progress bar."""
        window.evaluate_js(
            f'window.setLoadingProgress && window.setLoadingProgress({percent}, "{message}")'
        )
    
    try:
        # Step 1: Start Ollama
        update_status("Starting AI engine...")
        await api.ollama.start(timeout=30)
        
        # Step 2: Check for model
        update_status("Checking AI model...")
        has_model = await api.ollama.has_model(settings.ollama_model)
        
        # Step 3: Download model if needed
        if not has_model:
            update_status(f"Downloading AI model ({settings.ollama_model})...")
            
            def on_progress(progress: dict):
                status = progress.get('status', '')
                completed = progress.get('completed', 0)
                total = progress.get('total', 1)
                
                if total > 0:
                    pct = int(completed / total * 100)
                    update_progress(pct, status)
            
            await api.ollama.pull_model(settings.ollama_model, on_progress)
        
        # Step 4: Initialize chat service
        update_status("Initializing...")
        await api._initialize()
        
        # Step 5: Signal ready
        update_status("Ready!")
        window.evaluate_js('window.onAppReady && window.onAppReady()')
        
        logger.info("Application initialized successfully")
        return True
        
    except OllamaNotFoundError as e:
        logger.error(f"Ollama not found: {e}")
        error_message = str(e).replace('"', '\\"').replace('\n', '\\n')
        window.evaluate_js(f'window.onAppError && window.onAppError("{error_message}")')
        return False
        
    except OllamaStartupError as e:
        logger.error(f"Ollama startup failed: {e}")
        error_message = str(e).replace('"', '\\"').replace('\n', '\\n')
        window.evaluate_js(f'window.onAppError && window.onAppError("{error_message}")')
        return False
        
    except Exception as e:
        logger.exception("Failed to initialize application")
        error_message = str(e).replace('"', '\\"').replace('\n', '\\n')
        window.evaluate_js(f'window.onAppError && window.onAppError("{error_message}")')
        return False


def on_window_loaded(window: webview.Window, api: TechTimApi):
    """
    Called when the webview finishes loading.
    
    Starts the async initialization process in a background thread.
    """
    api.set_window(window)
    
    def run_init():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(initialize_app(api, window))
        except Exception as e:
            logger.exception("Initialization thread error")
        finally:
            loop.close()
    
    # Run initialization in background thread
    init_thread = threading.Thread(target=run_init, daemon=True)
    init_thread.start()


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
    logger.info(f"Bundled mode: {settings.bundled_mode}")
    logger.info(f"Development mode: {args.dev}")
    logger.info(f"User data path: {settings.user_data_path}")
    logger.info(f"Database path: {settings.database_path}")
    
    # Ensure directories exist
    settings.log_path.mkdir(parents=True, exist_ok=True)
    settings.models_path.mkdir(parents=True, exist_ok=True)
    
    # Create managers
    ollama_manager = OllamaManager()
    api = TechTimApi(ollama_manager)
    
    try:
        # Get frontend URL
        frontend_url = get_frontend_url(args.dev, args.port)
        logger.info(f"Loading frontend from: {frontend_url}")
        
        # Create window
        window = webview.create_window(
            title='TechTim(e)',
            url=frontend_url,
            js_api=api,
            width=1200,
            height=800,
            min_size=(800, 600),
            confirm_close=True,
        )
        
        # Start webview event loop
        # debug=True enables Chrome DevTools (right-click -> Inspect)
        webview.start(
            func=lambda: on_window_loaded(window, api),
            debug=args.debug or args.dev,
        )
        
    except FileNotFoundError as e:
        logger.error(str(e))
        
        # Show error dialog
        webview.create_window(
            title='TechTim(e) - Error',
            html=f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            padding: 40px;
                            text-align: center;
                            background: #1a1a2e;
                            color: #eee;
                        }}
                        h1 {{ color: #ff6b6b; }}
                        pre {{
                            text-align: left;
                            background: #16213e;
                            padding: 20px;
                            border-radius: 8px;
                            overflow-x: auto;
                        }}
                        button {{
                            background: #4a69bd;
                            color: white;
                            border: none;
                            padding: 12px 24px;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 16px;
                        }}
                        button:hover {{ background: #1e3799; }}
                    </style>
                </head>
                <body>
                    <h1>Failed to Start</h1>
                    <pre>{str(e)}</pre>
                    <button onclick="window.close()">Close</button>
                </body>
                </html>
            ''',
            width=600,
            height=400,
        )
        webview.start()
        sys.exit(1)
        
    except Exception as e:
        logger.exception("Unexpected error during startup")
        sys.exit(1)
    
    finally:
        # Cleanup
        logger.info("Shutting down...")
        ollama_manager.stop()
        logger.info("Goodbye!")


if __name__ == '__main__':
    main()
```

### Verification Steps

1. First, ensure Ollama is installed on your system or run `python scripts/download_ollama.py`

2. Test with an existing Next.js dev server:
   ```bash
   # Terminal 1: Start Next.js
   cd frontend/techtime
   npm run dev
   
   # Terminal 2: Start desktop app in dev mode
   python desktop_main.py --dev --debug
   ```

3. If you see a window with your frontend, Phase 2 is complete!

---

## Acceptance Criteria

Phase 2 is complete when:

1. **Ollama manager works**: The `OllamaManager` can start/stop Ollama and list models:
   ```python
   import asyncio
   from desktop.ollama_manager import OllamaManager
   
   async def test():
       m = OllamaManager()
       await m.start()
       print(await m.list_models())
       m.stop()
   
   asyncio.run(test())
   ```

2. **API bridge is callable**: Methods return proper response dictionaries:
   ```python
   from desktop.ollama_manager import OllamaManager
   from desktop.api import TechTimApi
   
   api = TechTimApi(OllamaManager())
   print(api.get_app_info())  # Should return {'success': True, 'data': {...}}
   print(api.list_tools())    # Should list diagnostic tools
   ```

3. **Main entry point runs**: `python desktop_main.py --dev` opens a window (with Next.js dev server running)

4. **Error handling works**: Missing frontend shows error dialog instead of crashing

5. **Analytics integration works**: Sessions are persisted to database

---

## Files Created Summary

| File | Description |
|------|-------------|
| `desktop/__init__.py` | Package initialization |
| `desktop/exceptions.py` | Desktop-specific exceptions |
| `desktop/ollama_manager.py` | Ollama sidecar lifecycle management |
| `desktop/api.py` | PyWebView JavaScript API bridge (with analytics) |
| `desktop_main.py` | Application entry point |

---

## Dependencies Added

Add these to your `pyproject.toml` or `requirements.txt`:

```
pywebview>=5.0
httpx>=0.25.0
```

---

## Next Phase

After completing Phase 2, proceed to **Phase 3: Frontend Modifications**, which updates the Next.js app to use the PyWebView bridge instead of HTTP calls.
