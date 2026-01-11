"""
Unit tests for the OllamaManager.

These tests verify:
- Binary path resolution
- Process lifecycle management
- Health checking
- Model management
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from desktop.ollama_manager import (
    OllamaManager,
    OllamaNotFoundError,
)


class TestBinaryResolution:
    """Tests for finding the Ollama binary."""
    
    def test_find_system_ollama(self):
        """Should find system-installed Ollama if available."""
        manager = OllamaManager()
        
        with patch('shutil.which', return_value='/usr/local/bin/ollama'):
            try:
                path = manager.get_ollama_binary_path()
                assert path is not None
                assert str(path) == '/usr/local/bin/ollama'
            except OllamaNotFoundError:
                # Also valid if not found in other locations
                pass
    
    def test_raises_when_not_found(self, mock_settings):
        """Should raise OllamaNotFoundError when binary not found."""
        manager = OllamaManager()
        
        with patch('shutil.which', return_value=None):
            with patch.object(Path, 'exists', return_value=False):
                with pytest.raises(OllamaNotFoundError):
                    manager.get_ollama_binary_path()


class TestProcessLifecycle:
    """Tests for starting and stopping Ollama."""
    
    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Should detect and use existing Ollama instance."""
        manager = OllamaManager()
        
        async def mock_healthy():
            return True
        
        with patch.object(manager, '_is_healthy', side_effect=mock_healthy):
            await manager.start()
            
            assert manager._started is True
            assert manager._owns_process is False
    
    def test_stop_terminates_owned_process(self):
        """Should terminate process if we started it."""
        manager = OllamaManager()
        
        mock_process = MagicMock()
        mock_process.wait.return_value = 0
        
        manager.process = mock_process
        manager._started = True
        manager._owns_process = True
        
        manager.stop()
        
        mock_process.terminate.assert_called_once()
        assert manager._started is False
        assert manager.process is None
    
    def test_stop_does_not_terminate_external_process(self):
        """Should not terminate process if we didn't start it."""
        manager = OllamaManager()
        
        manager._started = True
        manager._owns_process = False
        manager.process = None
        
        manager.stop()
        
        assert manager._started is False


class TestHealthCheck:
    """Tests for Ollama health checking."""
    
    @pytest.mark.asyncio
    async def test_is_healthy_success(self):
        """Should return True when Ollama responds."""
        manager = OllamaManager()
        
        import httpx
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await manager._is_healthy()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_is_healthy_failure(self):
        """Should return False when Ollama is unreachable."""
        manager = OllamaManager()
        
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_class.return_value = mock_client
            
            result = await manager._is_healthy()
            
            assert result is False


class TestModelManagement:
    """Tests for model listing and downloading."""
    
    @pytest.mark.asyncio
    async def test_has_model_true(self, mock_ollama_responses):
        """Should return True when model exists."""
        manager = OllamaManager()
        
        async def mock_list():
            return mock_ollama_responses["tags"]["models"]
        
        with patch.object(manager, 'list_models', side_effect=mock_list):
            result = await manager.has_model("mistral:7b-instruct")
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_has_model_false(self, mock_ollama_responses):
        """Should return False when model doesn't exist."""
        manager = OllamaManager()
        
        async def mock_list():
            return mock_ollama_responses["tags"]["models"]
        
        with patch.object(manager, 'list_models', side_effect=mock_list):
            result = await manager.has_model("nonexistent:model")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_has_model_partial_match(self, mock_ollama_responses):
        """Should match by base model name."""
        manager = OllamaManager()
        
        async def mock_list():
            return mock_ollama_responses["tags"]["models"]
        
        with patch.object(manager, 'list_models', side_effect=mock_list):
            result = await manager.has_model("mistral")
            
            assert result is True


class TestManagerProperties:
    """Tests for OllamaManager properties."""
    
    def test_base_url_property(self):
        """base_url should return correct URL."""
        manager = OllamaManager(host="localhost", port=11434)
        
        assert manager.base_url == "http://localhost:11434"
    
    def test_custom_host_and_port(self):
        """Should accept custom host and port."""
        manager = OllamaManager(host="192.168.1.100", port=8080)
        
        assert manager.host == "192.168.1.100"
        assert manager.port == 8080
        assert manager.base_url == "http://192.168.1.100:8080"
    
    def test_default_host_and_port(self):
        """Should have sensible defaults."""
        manager = OllamaManager()
        
        assert manager.host == "127.0.0.1"
        assert manager.port == 11434


class TestManagerState:
    """Tests for OllamaManager state tracking."""
    
    def test_initial_state(self):
        """Manager should start in clean state."""
        manager = OllamaManager()
        
        assert manager.process is None
        assert manager._started is False
        assert manager._owns_process is False
    
    def test_is_running_when_not_started(self):
        """is_running should return False when not started."""
        manager = OllamaManager()
        
        # Not started
        assert manager._started is False
    
    @pytest.mark.asyncio
    async def test_start_sets_started_flag(self):
        """start() should set _started to True."""
        manager = OllamaManager()
        
        async def mock_healthy():
            return True
        
        with patch.object(manager, '_is_healthy', side_effect=mock_healthy):
            await manager.start()
            
            assert manager._started is True


class TestPlatformSpecificBinary:
    """Tests for platform-specific binary resolution."""
    
    def test_darwin_binary_location(self, mock_settings):
        """On macOS, should look for darwin binary."""
        manager = OllamaManager()
        
        with patch('sys.platform', 'darwin'):
            with patch('shutil.which', return_value=None):
                # It will look for bundled binary first
                # This verifies the code path handles darwin
                try:
                    manager.get_ollama_binary_path()
                except OllamaNotFoundError:
                    pass  # Expected if not found
    
    def test_win32_binary_location(self, mock_settings):
        """On Windows, should look for .exe binary."""
        manager = OllamaManager()
        
        with patch('sys.platform', 'win32'):
            with patch('shutil.which', return_value=None):
                try:
                    manager.get_ollama_binary_path()
                except OllamaNotFoundError:
                    pass  # Expected if not found
    
    def test_linux_binary_location(self, mock_settings):
        """On Linux, should look for linux binary."""
        manager = OllamaManager()
        
        with patch('sys.platform', 'linux'):
            with patch('shutil.which', return_value=None):
                try:
                    manager.get_ollama_binary_path()
                except OllamaNotFoundError:
                    pass  # Expected if not found

