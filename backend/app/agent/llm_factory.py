"""LLM Provider Factory - Plugin-based provider selection"""

from typing import Union
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.llm_config import LLMSettings


def get_llm_provider(settings: LLMSettings) -> BaseChatModel:
    """
    Factory to create LLM provider based on configuration.

    Args:
        settings: LLM configuration (provider, model, API keys, etc.)

    Returns:
        Configured LangChain chat model instance

    Raises:
        ValueError: If provider is unknown or required config is missing

    Examples:
    ---------
    >>> from app.core.llm_config import get_llm_settings
    >>> settings = get_llm_settings()
    >>> llm = get_llm_provider(settings)
    >>> response = await llm.ainvoke("What is the capital of France?")

    Supported Providers:
    --------------------
    - ollama: Local Ollama instance (default: http://localhost:11434)
    - openrouter: OpenRouter API (requires API key)
    - anthropic: Anthropic Claude API (requires API key)
    - openai: OpenAI API (requires API key)
    """

    if settings.provider == "ollama":
        return ChatOllama(
            model=settings.model,
            base_url=settings.base_url or "http://localhost:11434",
            temperature=settings.temperature,
            num_predict=settings.max_tokens,
        )

    elif settings.provider == "openrouter":
        if not settings.api_key:
            raise ValueError("OpenRouter provider requires LLM_API_KEY environment variable")

        return ChatOpenAI(
            model=settings.model,
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    elif settings.provider == "anthropic":
        if not settings.api_key:
            raise ValueError("Anthropic provider requires LLM_API_KEY environment variable")

        return ChatAnthropic(
            model=settings.model,
            api_key=settings.api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    elif settings.provider == "openai":
        if not settings.api_key:
            raise ValueError("OpenAI provider requires LLM_API_KEY environment variable")

        return ChatOpenAI(
            model=settings.model,
            api_key=settings.api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: {settings.provider}. "
            f"Supported providers: ollama, openrouter, anthropic, openai"
        )


def get_llm() -> BaseChatModel:
    """
    Convenience function to get LLM with default settings from environment.

    Returns:
        Configured LangChain chat model

    Examples:
    ---------
    >>> llm = get_llm()
    >>> response = await llm.ainvoke("Explain async/await in Python")
    """
    from app.core.llm_config import get_llm_settings

    settings = get_llm_settings()
    return get_llm_provider(settings)
