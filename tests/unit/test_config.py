"""
Unit tests for backend configuration.

UPDATED: Tests actual Settings properties including bundled mode paths.
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestBundledModeDetection:
    """Tests for is_bundled() function."""
    
    def test_not_bundled_by_default(self):
        """In normal Python, is_bundled() should return False."""
        from backend.config import is_bundled
        
        # Clear any existing frozen attribute
        frozen_backup = getattr(sys, 'frozen', None)
        meipass_backup = getattr(sys, '_MEIPASS', None)
        
        try:
            if hasattr(sys, 'frozen'):
                delattr(sys, 'frozen')
            if hasattr(sys, '_MEIPASS'):
                delattr(sys, '_MEIPASS')
            
            assert is_bundled() is False
        finally:
            # Restore original state
            if frozen_backup is not None:
                sys.frozen = frozen_backup
            if meipass_backup is not None:
                sys._MEIPASS = meipass_backup
    
    def test_bundled_with_pyinstaller_attributes(self):
        """When PyInstaller attributes are set, is_bundled() should return True."""
        from backend.config import is_bundled
        
        with patch.object(sys, 'frozen', True, create=True):
            with patch.object(sys, '_MEIPASS', '/tmp/fake_meipass', create=True):
                assert is_bundled() is True


class TestPathResolution:
    """Tests for path resolution functions."""
    
    def test_get_base_path_development(self):
        """In development, base path should be project root."""
        from backend.config import get_base_path
        
        base_path = get_base_path()
        
        # Should be a valid directory
        assert base_path.exists()
        # Should contain backend directory
        assert (base_path / "backend").exists()
    
    def test_user_data_path_creates_directory(self, temp_dir):
        """User data path should be created if it doesn't exist."""
        with patch('backend.config.Path.home', return_value=temp_dir):
            from backend.config import get_user_data_path
            
            # Force recalculation by patching platform
            with patch('sys.platform', 'darwin'):
                user_path = get_user_data_path()
                
                assert user_path.exists()
                assert "TechTime" in str(user_path)


class TestSettings:
    """Tests for the Settings class."""
    
    def test_default_settings(self):
        """Settings should have sensible defaults."""
        from backend.config import get_settings
        
        # Clear cache for fresh settings
        get_settings.cache_clear()
        settings = get_settings()
        
        assert settings.llm_backend in ("ollama", "openai")
        assert settings.ollama_model is not None
        assert settings.max_tool_rounds > 0
        assert settings.command_timeout > 0
        
        # Clear cache after test
        get_settings.cache_clear()
    
    def test_path_properties(self, mock_settings):
        """
        UPDATED: Test new path properties from phase1_updated.
        """
        settings = mock_settings
        
        # All path properties should return Path objects
        assert isinstance(settings.database_path, Path)
        assert isinstance(settings.log_path, Path)
        assert isinstance(settings.models_path, Path)
        assert isinstance(settings.prompts_path, Path)
        
        # Log and models paths should be created
        assert settings.log_path.exists()
        assert settings.models_path.exists()
        
        # Database path should end with .db
        assert str(settings.database_path).endswith('.db')
    
    def test_bundled_mode_property(self, mock_settings):
        """bundled_mode property should return False in tests."""
        assert mock_settings.bundled_mode is False
    
    def test_dns_server_list(self, mock_settings):
        """dns_server_list should parse comma-separated string."""
        settings = mock_settings
        
        server_list = settings.dns_server_list
        
        assert isinstance(server_list, list)
        assert len(server_list) > 0
        assert all(isinstance(s, str) for s in server_list)
    
    def test_get_settings_cached(self):
        """get_settings should return cached instance."""
        from backend.config import get_settings
        
        get_settings.cache_clear()
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
        
        # Clean up
        get_settings.cache_clear()


class TestSettingsEnvironmentVariables:
    """Tests for settings loaded from environment variables."""
    
    def test_llm_backend_from_env(self, temp_dir):
        """LLM backend should be configurable via environment."""
        from backend.config import get_settings
        
        get_settings.cache_clear()
        
        with patch.dict(os.environ, {"LLM_BACKEND": "openai"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.llm_backend == "openai"
        
        get_settings.cache_clear()
    
    def test_ollama_host_from_env(self, temp_dir):
        """Ollama host should be configurable via environment."""
        from backend.config import get_settings
        
        get_settings.cache_clear()
        
        with patch.dict(os.environ, {"OLLAMA_HOST": "http://custom:11434"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.ollama_host == "http://custom:11434"
        
        get_settings.cache_clear()

