"""
Strategy questionnaire configuration endpoint.
Provides OpenRouter API key and model settings for the strategy builder HTML.
"""
from fastapi import APIRouter
from pydantic import BaseModel
import os

router = APIRouter()


class StrategyConfig(BaseModel):
    """Configuration for strategy questionnaire AI chat"""
    openrouter_api_key: str
    default_model: str
    alternative_models: list[str]


@router.get("/api/strategy-config", response_model=StrategyConfig)
async def get_strategy_config():
    """
    Get OpenRouter configuration for strategy questionnaire.
    Returns API key and preferred models from environment variables.
    """
    return StrategyConfig(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        default_model=os.getenv("LLM_MODEL", "nex-agi/deepseek-v3.1-nex-n1:free"),
        alternative_models=[
            "nex-agi/deepseek-v3.1-nex-n1:free",
            "z-ai/glm-4.5-air:free",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4-turbo"
        ]
    )
