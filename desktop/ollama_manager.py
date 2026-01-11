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

