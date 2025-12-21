"""LLM Provider Factory - Plugin-based provider selection"""

import logging
from typing import Optional, Union
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.llm_config import LLMSettings, LLMUserConfig, get_ca_bundle_path
from app.models.settings import Settings as UserSettings
from app.models.llm_configuration import LLMProvider

logger = logging.getLogger(__name__)


def get_llm_provider(settings: Union[LLMSettings, LLMUserConfig]) -> BaseChatModel:
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
    - gemini: Google Gemini API (requires API key)
    """

    # Get API key using the new provider-specific resolution
    api_key = settings.get_api_key() if hasattr(settings, 'get_api_key') else settings.api_key
    base_url = settings.get_base_url() if hasattr(settings, 'get_base_url') else settings.base_url

    if settings.provider == "ollama":
        return ChatOllama(
            model=settings.model,
            base_url=base_url or "http://localhost:11434",
            temperature=settings.temperature,
            num_predict=settings.max_tokens,
        )

    elif settings.provider == "openrouter":
        if not api_key:
            raise ValueError("OpenRouter provider requires OPENROUTER_API_KEY environment variable")

        ca_path = get_ca_bundle_path()
        # LangChain expects httpx.Client for http_client and httpx.AsyncClient for
        # http_async_client. Use the async variant so OpenRouter calls work with
        # async LangChain stack and honor the corporate/Zscaler CA bundle.
        http_async_client = httpx.AsyncClient(verify=ca_path, trust_env=True)

        return ChatOpenAI(
            model=settings.model,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            http_async_client=http_async_client,
        )

    elif settings.provider == "anthropic":
        if not api_key:
            raise ValueError("Anthropic provider requires ANTHROPIC_API_KEY environment variable")

        return ChatAnthropic(
            model=settings.model,
            api_key=api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    elif settings.provider == "openai":
        if not api_key:
            raise ValueError("OpenAI provider requires OPENAI_API_KEY environment variable")

        return ChatOpenAI(
            model=settings.model,
            api_key=api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    elif settings.provider == "gemini":
        if not api_key:
            raise ValueError("Gemini provider requires GEMINI_API_KEY environment variable")

        # Log the model being used for Gemini
        logger.info(f"Creating ChatGoogleGenerativeAI with model={settings.model}")

        return ChatGoogleGenerativeAI(
            model=settings.model,
            google_api_key=api_key,
            temperature=settings.temperature,
            max_output_tokens=settings.max_tokens,
        )

    else:
        raise ValueError(
            f"Unknown LLM provider: {settings.provider}. "
            f"Supported providers: ollama, openrouter, anthropic, openai, gemini"
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
    # Fetch user settings and include the active LLM configuration
    result = await db.execute(
        select(UserSettings)
        .options(selectinload(UserSettings.active_llm_config))
        .where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalar_one_or_none()

    # If no user settings or no active LLM config, fall back to environment defaults
    if not user_settings or not user_settings.active_llm_config:
        from app.core.llm_config import get_llm_settings
        env_settings = get_llm_settings()
        logger.warning(f"No active LLM config for user_id={user_id}, using environment defaults")
        return get_llm_provider(env_settings)

    # Expire and refresh the relationship to ensure we have the latest config
    # This ensures we get fresh data after the active config is changed
    db.expire(user_settings, ["active_llm_config"])
    await db.refresh(user_settings, ["active_llm_config"])
    active_config = user_settings.active_llm_config
    
    # Double-check we have the config after refresh
    if not active_config:
        from app.core.llm_config import get_llm_settings
        env_settings = get_llm_settings()
        logger.warning(f"Active LLM config not found after refresh for user_id={user_id}, using environment defaults")
        return get_llm_provider(env_settings)

    # Log the configuration being used for debugging
    logger.info(
        f"Using LLM config for user_id={user_id}: "
        f"provider={active_config.provider.value}, "
        f"model={active_config.model}, "
        f"temperature={active_config.temperature}, "
        f"max_tokens={active_config.max_tokens}"
    )

    # Use LLMUserConfig instead of LLMSettings to avoid environment variable interference
    # LLMSettings extends BaseSettings which reads from .env, potentially overriding user settings
    # LLMUserConfig is a simple container that only uses the values passed to it
    user_config = LLMUserConfig(
        provider=active_config.provider.value,
        model=active_config.model,
        api_key=active_config.api_key,
        base_url=active_config.base_url,
        temperature=active_config.temperature or 0.2,
        max_tokens=active_config.max_tokens or 1000,
    )

    logger.info(f"Final LLM model: {user_config.model} (provider: {user_config.provider})")

    return get_llm_provider(user_config)


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
