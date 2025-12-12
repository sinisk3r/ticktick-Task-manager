"""LLM Configuration for Provider-Agnostic LLM Access"""

from typing import Literal, Optional
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """
    LLM Provider Configuration

    Supports multiple providers via config:
    - ollama: Local Ollama instance
    - openrouter: OpenRouter API
    - anthropic: Anthropic Claude API
    - openai: OpenAI API

    Environment Variables:
    ---------------------
    LLM_PROVIDER: Provider name (ollama | openrouter | anthropic | openai)
    LLM_MODEL: Model identifier (e.g., qwen3:8b, claude-sonnet-4, gpt-4)
    LLM_BASE_URL: Base URL for API (optional, defaults per provider)
    LLM_API_KEY: API key (required for cloud providers)
    LLM_TEMPERATURE: Sampling temperature (0.0-1.0, default: 0.2)
    LLM_MAX_TOKENS: Maximum tokens to generate (default: 1000)

    Examples:
    ---------
    # Ollama (local)
    LLM_PROVIDER=ollama
    LLM_MODEL=qwen3:8b
    LLM_BASE_URL=http://localhost:11434

    # OpenRouter
    LLM_PROVIDER=openrouter
    LLM_MODEL=meta-llama/llama-3.2-3b-instruct
    LLM_API_KEY=your_key

    # Anthropic Claude
    LLM_PROVIDER=anthropic
    LLM_MODEL=claude-sonnet-4
    LLM_API_KEY=your_key

    # OpenAI
    LLM_PROVIDER=openai
    LLM_MODEL=gpt-4-turbo
    LLM_API_KEY=your_key
    """

    provider: Literal["ollama", "openrouter", "anthropic", "openai"] = "ollama"
    model: str = "qwen3:8b"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 1000

    class Config:
        env_file = ".env"
        env_prefix = "LLM_"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars that don't match our model


def get_llm_settings() -> LLMSettings:
    """
    Get current LLM settings from environment.

    Returns:
        LLMSettings instance with configuration

    Raises:
        ValidationError: If required config is missing (e.g., API key for cloud providers)
    """
    return LLMSettings()
