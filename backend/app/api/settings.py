"""
User settings API endpoints - now works with saved LLM configurations.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.settings import Settings
from app.models.llm_configuration import LLMConfiguration, LLMProvider

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Pydantic schemas for request/response validation
class ActiveLLMConfigResponse(BaseModel):
    """Response schema for active LLM configuration details."""
    id: int
    name: str
    provider: LLMProvider
    model: str
    base_url: Optional[str]
    temperature: float
    max_tokens: int
    connection_status: str
    display_name: str

    class Config:
        from_attributes = True


class SettingsResponse(BaseModel):
    """Response schema for user settings."""
    id: int
    user_id: int
    active_llm_config_id: Optional[int]
    active_llm_config: Optional[ActiveLLMConfigResponse]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "active_llm_config_id": 2,
                "active_llm_config": {
                    "id": 2,
                    "name": "Local Ollama",
                    "provider": "ollama",
                    "model": "qwen3:8b",
                    "base_url": "http://localhost:11434",
                    "temperature": 0.2,
                    "max_tokens": 1000,
                    "connection_status": "success",
                    "display_name": "Local Ollama (ollama | qwen3:8b)"
                }
            }
        }


class SettingsUpdate(BaseModel):
    """Request schema for updating user settings."""
    active_llm_config_id: Optional[int] = Field(None, description="ID of the LLM configuration to set as active")

    class Config:
        json_schema_extra = {
            "example": {
                "active_llm_config_id": 2
            }
        }


@router.get("", response_model=SettingsResponse)
async def get_settings(
    user_id: int = Query(..., gt=0, description="User ID to get settings for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user settings including active LLM configuration.

    If no settings exist, returns a settings object with no active configuration.
    """
    # Try to fetch existing settings with active config
    result = await db.execute(
        select(Settings)
        .options(selectinload(Settings.active_llm_config))
        .where(Settings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()

    if settings:
        # Convert active config to response format (hiding API key)
        active_config_response = None
        if settings.active_llm_config:
            active_config_response = ActiveLLMConfigResponse(
                id=settings.active_llm_config.id,
                name=settings.active_llm_config.name,
                provider=settings.active_llm_config.provider,
                model=settings.active_llm_config.model,
                base_url=settings.active_llm_config.base_url,
                temperature=settings.active_llm_config.temperature,
                max_tokens=settings.active_llm_config.max_tokens,
                connection_status=settings.active_llm_config.connection_status,
                display_name=settings.active_llm_config.display_name
            )

        return SettingsResponse(
            id=settings.id,
            user_id=settings.user_id,
            active_llm_config_id=settings.active_llm_config_id,
            active_llm_config=active_config_response
        )

    # No settings found - return empty settings
    return SettingsResponse(
        id=0,  # Indicates this is not persisted
        user_id=user_id,
        active_llm_config_id=None,
        active_llm_config=None
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(
    user_id: int = Query(..., gt=0, description="User ID to update settings for"),
    settings_update: SettingsUpdate = ...,
    db: AsyncSession = Depends(get_db)
):
    """
    Update user settings.

    Currently only supports updating the active LLM configuration.
    """
    # Validate that the config exists and belongs to the user (if provided)
    if settings_update.active_llm_config_id is not None:
        config_result = await db.execute(
            select(LLMConfiguration).where(
                LLMConfiguration.id == settings_update.active_llm_config_id,
                LLMConfiguration.user_id == user_id
            )
        )
        config = config_result.scalar_one_or_none()
        if not config:
            raise HTTPException(
                status_code=400, 
                detail="LLM configuration not found or does not belong to user"
            )

    # Try to fetch existing settings
    result = await db.execute(
        select(Settings)
        .options(selectinload(Settings.active_llm_config))
        .where(Settings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()

    if settings:
        # Update existing settings
        settings.active_llm_config_id = settings_update.active_llm_config_id
        await db.commit()
        await db.refresh(settings)
    else:
        # Create new settings
        settings = Settings(
            user_id=user_id,
            active_llm_config_id=settings_update.active_llm_config_id
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    # Fetch the updated settings with active config
    result = await db.execute(
        select(Settings)
        .options(selectinload(Settings.active_llm_config))
        .where(Settings.user_id == user_id)
    )
    updated_settings = result.scalar_one()

    # Convert active config to response format
    active_config_response = None
    if updated_settings.active_llm_config:
        active_config_response = ActiveLLMConfigResponse(
            id=updated_settings.active_llm_config.id,
            name=updated_settings.active_llm_config.name,
            provider=updated_settings.active_llm_config.provider,
            model=updated_settings.active_llm_config.model,
            base_url=updated_settings.active_llm_config.base_url,
            temperature=updated_settings.active_llm_config.temperature,
            max_tokens=updated_settings.active_llm_config.max_tokens,
            connection_status=updated_settings.active_llm_config.connection_status,
            display_name=updated_settings.active_llm_config.display_name
        )

    return SettingsResponse(
        id=updated_settings.id,
        user_id=updated_settings.user_id,
        active_llm_config_id=updated_settings.active_llm_config_id,
        active_llm_config=active_config_response
    )