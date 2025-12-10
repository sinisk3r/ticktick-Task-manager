"""
Application configuration using Pydantic Settings.
Environment variables are loaded from .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Database
    database_url: str = "postgresql+asyncpg://context:context_dev@127.0.0.1:5433/context"

    # Redis
    redis_url: str = "redis://127.0.0.1:6379"

    # Ollama LLM
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"

    # API Configuration
    api_v1_prefix: str = "/api"
    project_name: str = "Context Task Management"
    debug: bool = True

    # CORS
    frontend_url: str = "http://localhost:3000"
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Security
    secret_key: str = "dev-secret-key-change-in-production-min-32-chars"

    # TickTick (for later iterations)
    ticktick_client_id: Optional[str] = None
    ticktick_client_secret: Optional[str] = None
    ticktick_redirect_uri: Optional[str] = None

    # Anthropic Claude API (for later iterations)
    anthropic_api_key: Optional[str] = None


# Global settings instance
settings = Settings()
