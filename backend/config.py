"""Configuration management for Network Diagnostics."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM Configuration
    llm_backend: Literal["ollama", "openai"] = "ollama"

    # Ollama Configuration
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "ministral-3:3b"

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Diagnostic Configuration
    command_timeout: int = 10
    dns_servers: str = "8.8.8.8,1.1.1.1"
    dns_test_hosts: str = "google.com,cloudflare.com"

    @property
    def dns_server_list(self) -> list[str]:
        """Parse DNS servers string into list."""
        return [s.strip() for s in self.dns_servers.split(",")]

    @property
    def dns_test_host_list(self) -> list[str]:
        """Parse DNS test hosts string into list."""
        return [h.strip() for h in self.dns_test_hosts.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

