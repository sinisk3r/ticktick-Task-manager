"""LLM Configuration for Provider-Agnostic LLM Access"""

import os
from pathlib import Path
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
import certifi

# Ensure HTTP clients (httpx/openai/langchain) have a CA bundle available.
# Prefer a repo-level combined bundle (for corporate roots like Zscaler); fall back to certifi.
_repo_root = Path(__file__).resolve().parents[2]
_combined_ca = _repo_root / "certs" / "combined.pem"
if _combined_ca.exists():
    os.environ.setdefault("SSL_CERT_FILE", str(_combined_ca))
else:
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())


def get_ca_bundle_path() -> str:
    """Return the CA bundle path in use for HTTP clients."""
    return os.environ.get("SSL_CERT_FILE", certifi.where())


# Default models per provider
DEFAULT_MODELS = {
    "ollama": "qwen3:8b",
    "openrouter": "meta-llama/llama-3.2-3b-instruct",
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
}


class LLMSettings(BaseSettings):
    """
    LLM Provider Configuration

    Supports multiple providers with provider-specific API keys.
    All keys can be stored in .env - just change LLM_PROVIDER to switch.

    Environment Variables:
    ---------------------
    LLM_PROVIDER: Active provider (ollama | openrouter | anthropic | openai | gemini)
    LLM_MODEL: Model override (optional, uses provider default if not set)
    LLM_TEMPERATURE: Sampling temperature (0.0-1.0, default: 0.2)
    LLM_MAX_TOKENS: Maximum tokens to generate (default: 1000)

    Provider-Specific API Keys (persist all, use based on LLM_PROVIDER):
    -------------------------------------------------------------------
    GEMINI_API_KEY: Google AI Studio API key
    OPENAI_API_KEY: OpenAI API key
    ANTHROPIC_API_KEY: Anthropic API key
    OPENROUTER_API_KEY: OpenRouter API key
    OLLAMA_BASE_URL: Ollama server URL (default: http://localhost:11434)

    Example .env:
    -------------
    # Active provider (change this to switch)
    LLM_PROVIDER=gemini

    # All API keys stored persistently
    GEMINI_API_KEY=AIza...
    OPENAI_API_KEY=sk-...
    ANTHROPIC_API_KEY=sk-ant-...
    OPENROUTER_API_KEY=sk-or-...

    # Ollama (local)
    OLLAMA_BASE_URL=http://localhost:11434

    # Optional overrides
    LLM_MODEL=gemini-2.0-flash  # Override default model
    LLM_TEMPERATURE=0.2
    LLM_MAX_TOKENS=1000
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Active provider selection (with LLM_ prefix)
    provider: Literal["ollama", "openrouter", "anthropic", "openai", "gemini"] = Field(
        default="ollama", alias="LLM_PROVIDER"
    )

    # Model override (if not set, uses DEFAULT_MODELS[provider])
    model: Optional[str] = Field(default=None, alias="LLM_MODEL")

    # Generation parameters
    temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    max_tokens: int = Field(default=1000, alias="LLM_MAX_TOKENS")

    # Provider-specific API keys (all can be stored, used based on provider)
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")

    # Provider-specific URLs
    ollama_base_url: Optional[str] = Field(
        default="http://localhost:11434", alias="OLLAMA_BASE_URL"
    )

    # Legacy fallback (deprecated, use provider-specific keys)
    api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    base_url: Optional[str] = Field(default=None, alias="LLM_BASE_URL")

    @model_validator(mode="after")
    def resolve_provider_config(self) -> "LLMSettings":
        """Resolve the API key and model based on the selected provider."""
        # Set default model if not specified
        if self.model is None:
            self.model = DEFAULT_MODELS.get(self.provider, "qwen3:8b")

        return self

    def get_api_key(self) -> Optional[str]:
        """Get the API key for the current provider."""
        provider_keys = {
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "openrouter": self.openrouter_api_key,
            "ollama": None,  # Ollama doesn't need an API key
        }
        # Try provider-specific key first, fall back to legacy LLM_API_KEY
        return provider_keys.get(self.provider) or self.api_key

    def get_base_url(self) -> Optional[str]:
        """Get the base URL for the current provider."""
        if self.provider == "ollama":
            return self.ollama_base_url or self.base_url or "http://localhost:11434"
        return self.base_url


def get_llm_settings() -> LLMSettings:
    """
    Get current LLM settings from environment.

    Returns:
        LLMSettings instance with configuration resolved for the active provider

    Raises:
        ValidationError: If required config is missing
    """
    return LLMSettings()
