"""
User settings API endpoints for LLM provider configuration.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.settings import Settings, LLMProvider

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Pydantic schemas for request/response validation
class SettingsResponse(BaseModel):
    """Response schema for user settings."""
    id: int
    user_id: int
    llm_provider: LLMProvider
    llm_model: Optional[str]
    llm_api_key: Optional[str]  # Masked in response
    llm_base_url: Optional[str]
    llm_temperature: Optional[float]
    llm_max_tokens: Optional[int]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "llm_provider": "openrouter",
                "llm_model": "nex-agi/deepseek-v3.1-nex-n1:free",
                "llm_api_key": "sk-or-***",
                "llm_base_url": None,
                "llm_temperature": 0.2,
                "llm_max_tokens": 1000
            }
        }


class SettingsUpdate(BaseModel):
    """Request schema for updating user settings."""
    llm_provider: Optional[LLMProvider] = None
    llm_model: Optional[str] = Field(None, max_length=500)
    llm_api_key: Optional[str] = Field(None, max_length=500)
    llm_base_url: Optional[str] = Field(None, max_length=500)
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    llm_max_tokens: Optional[int] = Field(None, ge=1, le=100000)

    class Config:
        json_schema_extra = {
            "example": {
                "llm_provider": "openrouter",
                "llm_model": "nex-agi/deepseek-v3.1-nex-n1:free",
                "llm_api_key": "sk-or-v1-xxx",
                "llm_temperature": 0.2,
                "llm_max_tokens": 1000
            }
        }


@router.get("", response_model=SettingsResponse)
async def get_settings(
    user_id: int = Query(..., gt=0, description="User ID to get settings for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user settings.

    If no settings exist for the user, returns default settings:
    - LLM Provider: Ollama
    - Ollama URL: http://localhost:11434
    - Ollama Model: qwen3:4b

    Query parameters:
    - user_id: Required - user to get settings for
    """
    # Try to fetch existing settings
    result = await db.execute(
        select(Settings).where(Settings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()

    if settings:
        return settings

    # No settings found - return defaults (without saving to DB)
    # This allows users to see what the defaults are without creating a record
    return SettingsResponse(
        id=0,  # Indicates this is not persisted
        user_id=user_id,
        llm_provider=LLMProvider.OLLAMA,
        llm_model="qwen3:8b",
        llm_api_key=None,
        llm_base_url="http://localhost:11434",
        llm_temperature=0.2,
        llm_max_tokens=1000
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    user_id: int = Query(..., gt=0, description="User ID to update settings for"),
    settings_update: SettingsUpdate = ...,
    db: AsyncSession = Depends(get_db)
):
    """
    Update user settings.

    If settings don't exist, they will be created with the provided values
    (any unspecified fields will use defaults).

    Only fields provided in the request will be updated for existing settings.

    Query parameters:
    - user_id: Required - user to update settings for
    """
    # Try to fetch existing settings
    result = await db.execute(
        select(Settings).where(Settings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()

    if settings:
        # Update existing settings
        update_data = settings_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(settings, field, value)

        await db.flush()
        await db.refresh(settings)

        return settings

    else:
        # Create new settings with provided values + defaults for missing fields
        update_data = settings_update.model_dump(exclude_unset=True)

        new_settings = Settings(
            user_id=user_id,
            llm_provider=update_data.get("llm_provider", LLMProvider.OLLAMA),
            llm_model=update_data.get("llm_model", "qwen3:8b"),
            llm_api_key=update_data.get("llm_api_key"),
            llm_base_url=update_data.get("llm_base_url", "http://localhost:11434"),
            llm_temperature=update_data.get("llm_temperature", 0.2),
            llm_max_tokens=update_data.get("llm_max_tokens", 1000)
        )

        db.add(new_settings)
        await db.flush()
        await db.refresh(new_settings)

        return new_settings
