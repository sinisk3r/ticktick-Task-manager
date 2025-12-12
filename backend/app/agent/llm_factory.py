"""LLM Provider Factory - Plugin-based provider selection"""

from typing import Union, Optional
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_config import LLMSettings
from app.models.settings import Settings as UserSettings, LLMProvider


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


async def get_llm_for_user(user_id: int, db: AsyncSession) -> BaseChatModel:
    """
    Get LLM configured for a specific user from database settings.

    Args:
        user_id: User ID to fetch settings for
        db: Database session

    Returns:
        Configured LangChain chat model based on user preferences

    Examples:
    ---------
    >>> llm = await get_llm_for_user(user_id=1, db=db)
    >>> response = await llm.ainvoke("Create a task")
    """
    # Fetch user settings from database
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalar_one_or_none()

    # If no user settings, fall back to environment defaults
    if not user_settings:
        from app.core.llm_config import get_llm_settings
        env_settings = get_llm_settings()
        return get_llm_provider(env_settings)

    # Convert database settings to LLMSettings
    llm_settings = LLMSettings(
        provider=user_settings.llm_provider.value,
        model=user_settings.llm_model or "qwen3:8b",
        api_key=user_settings.llm_api_key,
        base_url=user_settings.llm_base_url,
        temperature=user_settings.llm_temperature or 0.2,
        max_tokens=user_settings.llm_max_tokens or 1000,
    )

    return get_llm_provider(llm_settings)


def get_llm() -> BaseChatModel:
    """
    Convenience function to get LLM with default settings from environment.

    Note: This function is deprecated for user-facing features.
    Use get_llm_for_user() instead to respect user preferences.

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
