"""Configuration management for TechTime.

This module handles settings and path resolution for both development
and bundled (PyInstaller) deployment modes. Key concepts:

- Base path: Where application code and bundled resources live.
  In development, this is the project root. When bundled, PyInstaller
  extracts files to a temp directory (sys._MEIPASS).

- User data path: Where user-specific data is stored (database, logs,
  downloaded models). This persists across app restarts and is located
  in the platform's standard application data directory.
"""

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# Bundled Mode Detection Functions
# =============================================================================

def is_bundled() -> bool:
    """
    Check if running inside a PyInstaller bundle.
    
    PyInstaller sets sys.frozen to True and adds sys._MEIPASS
    pointing to the temp extraction directory.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_base_path() -> Path:
    """
    Get the base path for application resources.
    
    When bundled, PyInstaller extracts files to sys._MEIPASS.
    When running from source, use the directory containing this file's parent.
    
    Returns:
        Path to the application base directory
    """
    if is_bundled():
        # PyInstaller extracts to a temp directory
        return Path(sys._MEIPASS)
    # Development: backend/ is inside project root
    return Path(__file__).parent.parent


def get_user_data_path() -> Path:
    """
    Get the path for persistent user data.
    
    This directory stores:
    - SQLite database (analytics.db)
    - Log files
    - Downloaded Ollama models
    
    The location follows platform conventions:
    - macOS: ~/Library/Application Support/TechTime/
    - Windows: %APPDATA%/TechTime/
    - Linux: ~/.local/share/TechTime/
    
    Returns:
        Path to user data directory (created if it doesn't exist)
    """
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    elif sys.platform == 'win32':
        # Use APPDATA if available, fall back to home directory
        appdata = os.environ.get('APPDATA')
        base = Path(appdata) if appdata else Path.home() / 'AppData' / 'Roaming'
    else:
        # Linux and other Unix-like systems
        xdg_data = os.environ.get('XDG_DATA_HOME')
        base = Path(xdg_data) if xdg_data else Path.home() / '.local' / 'share'
    
    path = base / 'TechTime'
    path.mkdir(parents=True, exist_ok=True)
    return path


# =============================================================================
# Settings Class
# =============================================================================

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================================================================
    # LLM Configuration - Cloud-First with Ollama Fallback
    # =========================================================================
    
    # Provider priority (checked in order when online)
    # Set via PROVIDER_PRIORITY env var as comma-separated list
    provider_priority: list[str] = ["openai", "anthropic", "xai", "google", "ollama"]
    
    # OpenAI Configuration (Primary cloud provider)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    
    # Anthropic Configuration
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    
    # xAI/Grok Configuration
    xai_api_key: str | None = None
    xai_model: str = "grok-2"
    
    # Google/Gemini Configuration
    google_api_key: str | None = None
    google_model: str = "gemini-1.5-pro"
    
    # Ollama Configuration (Fallback - always running sidecar)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "ministral-3:3b"
    
    # Connectivity detection
    connectivity_check_url: str = "https://api.openai.com"
    connectivity_timeout_ms: int = 3000
    
    # GlueLLM settings
    gluellm_max_tool_iterations: int = 10
    
    # Legacy setting (deprecated, kept for compatibility)
    llm_backend: Literal["ollama", "openai"] = "ollama"

    # =========================================================================
    # Server Configuration (EXISTING)
    # =========================================================================
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # =========================================================================
    # Diagnostic Configuration (EXISTING)
    # =========================================================================
    
    command_timeout: int = 10
    dns_servers: str = "8.8.8.8,1.1.1.1"
    dns_test_hosts: str = "google.com,cloudflare.com"
    
    # =========================================================================
    # NEW: Desktop/Bundled Mode Configuration
    # =========================================================================
    
    max_tool_rounds: int = Field(
        default=10,
        description="Maximum number of tool execution rounds per chat turn"
    )

    # =========================================================================
    # EXISTING: Property Methods
    # =========================================================================
    
    @property
    def dns_server_list(self) -> list[str]:
        """Parse DNS servers string into list."""
        return [s.strip() for s in self.dns_servers.split(",")]

    @property
    def dns_test_host_list(self) -> list[str]:
        """Parse DNS test hosts string into list."""
        return [h.strip() for h in self.dns_test_hosts.split(",")]

    # =========================================================================
    # NEW: Bundled Mode Properties
    # =========================================================================
    
    @property
    def bundled_mode(self) -> bool:
        """True when running inside PyInstaller bundle."""
        return is_bundled()
    
    @property
    def base_path(self) -> Path:
        """Base path for application resources."""
        return get_base_path()
    
    @property
    def user_data_path(self) -> Path:
        """Path for persistent user data."""
        return get_user_data_path()
    
    @property
    def database_path(self) -> Path:
        """Path to the SQLite analytics database."""
        if self.bundled_mode:
            return self.user_data_path / "analytics.db"
        # Development mode: use existing data/ directory
        path = Path(__file__).parent.parent / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path / "analytics.db"
    
    @property
    def log_path(self) -> Path:
        """Directory for log files."""
        if self.bundled_mode:
            path = self.user_data_path / "logs"
        else:
            path = Path(__file__).parent.parent / "data" / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def models_path(self) -> Path:
        """Directory where Ollama stores downloaded models."""
        path = self.user_data_path / "models"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def prompts_path(self) -> Path:
        """Directory containing agent prompt templates."""
        if self.bundled_mode:
            return self.base_path / "prompts"
        return Path(__file__).parent.parent / "prompts"


# =============================================================================
# Global Settings Accessor (PRESERVED PATTERN)
# =============================================================================

@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
