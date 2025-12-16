"""
API endpoints for managing LLM configurations.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models import LLMConfiguration, LLMProvider, Settings
from app.services.llm_test import test_llm_connection


router = APIRouter(prefix="/api/llm-configurations", tags=["LLM Configurations"])


# Pydantic Models
class LLMConfigurationCreate(BaseModel):
    """Request model for creating a new LLM configuration."""
    name: str = Field(..., min_length=1, max_length=100, description="User-friendly name for the configuration")
    provider: LLMProvider = Field(..., description="LLM provider type")
    model: str = Field(..., min_length=1, max_length=500, description="Model name/identifier")
    api_key: Optional[str] = Field(None, max_length=500, description="API key (if required by provider)")
    base_url: Optional[str] = Field(None, max_length=500, description="Base URL (for Ollama or custom endpoints)")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(1000, ge=1, le=100000, description="Maximum tokens to generate")
    is_default: bool = Field(False, description="Set as default configuration for this user")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Local Ollama",
                "provider": "ollama",
                "model": "qwen3:8b",
                "base_url": "http://localhost:11434",
                "temperature": 0.2,
                "max_tokens": 1000,
                "is_default": True
            }
        }


class LLMConfigurationUpdate(BaseModel):
    """Request model for updating an LLM configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    provider: Optional[LLMProvider] = None
    model: Optional[str] = Field(None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(None, max_length=500)
    base_url: Optional[str] = Field(None, max_length=500)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=100000)
    is_default: Optional[bool] = None


class LLMConfigurationResponse(BaseModel):
    """Response model for LLM configuration."""
    id: int
    user_id: int
    name: str
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None  # Never return the actual API key
    base_url: Optional[str] = None
    temperature: float
    max_tokens: int
    is_default: bool
    
    # Connection status
    connection_status: str
    connection_error: Optional[str] = None
    last_tested_at: Optional[str] = None
    
    # Computed properties
    display_name: str
    requires_api_key: bool
    requires_base_url: bool
    
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "name": "Local Ollama",
                "provider": "ollama",
                "model": "qwen3:8b",
                "base_url": "http://localhost:11434",
                "temperature": 0.2,
                "max_tokens": 1000,
                "is_default": True,
                "connection_status": "success",
                "display_name": "Local Ollama (ollama | qwen3:8b)",
                "requires_api_key": False,
                "requires_base_url": True,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }


class ConnectionTestResult(BaseModel):
    """Result of testing an LLM configuration connection."""
    success: bool
    error: Optional[str] = None
    response_time_ms: Optional[int] = None
    model_info: Optional[dict] = None


@router.get("", response_model=List[LLMConfigurationResponse])
async def list_configurations(
    user_id: int = Query(..., gt=0, description="User ID to list configurations for"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all LLM configurations for a user.
    
    Returns configurations ordered by: default first, then by creation date.
    """
    result = await db.execute(
        select(LLMConfiguration)
        .where(LLMConfiguration.user_id == user_id)
        .order_by(LLMConfiguration.is_default.desc(), LLMConfiguration.created_at.asc())
    )
    configurations = result.scalars().all()
    
    # Convert to response models (hiding API keys)
    response_configs = []
    for config in configurations:
        response_config = LLMConfigurationResponse(
            id=config.id,
            user_id=config.user_id,
            name=config.name,
            provider=config.provider,
            model=config.model,
            api_key="***" if config.api_key else None,  # Hide actual API key
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            is_default=config.is_default,
            connection_status=config.connection_status,
            connection_error=config.connection_error,
            last_tested_at=config.last_tested_at.isoformat() if config.last_tested_at else None,
            display_name=config.display_name,
            requires_api_key=config.requires_api_key,
            requires_base_url=config.requires_base_url,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat()
        )
        response_configs.append(response_config)
    
    return response_configs


@router.post("", response_model=LLMConfigurationResponse)
async def create_configuration(
    user_id: int = Query(..., gt=0, description="User ID to create configuration for"),
    config_data: LLMConfigurationCreate = ...,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new LLM configuration.
    
    If this is set as default, any existing default will be unset.
    """
    # If setting as default, unset any existing default
    if config_data.is_default:
        await db.execute(
            select(LLMConfiguration)
            .where(and_(
                LLMConfiguration.user_id == user_id,
                LLMConfiguration.is_default == True
            ))
        )
        existing_defaults = (await db.execute(
            select(LLMConfiguration)
            .where(and_(
                LLMConfiguration.user_id == user_id,
                LLMConfiguration.is_default == True
            ))
        )).scalars().all()
        
        for existing_default in existing_defaults:
            existing_default.is_default = False
    
    # Create new configuration
    new_config = LLMConfiguration(
        user_id=user_id,
        name=config_data.name,
        provider=config_data.provider,
        model=config_data.model,
        api_key=config_data.api_key,
        base_url=config_data.base_url,
        temperature=config_data.temperature,
        max_tokens=config_data.max_tokens,
        is_default=config_data.is_default
    )
    
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    
    # Return response (hiding API key)
    return LLMConfigurationResponse(
        id=new_config.id,
        user_id=new_config.user_id,
        name=new_config.name,
        provider=new_config.provider,
        model=new_config.model,
        api_key="***" if new_config.api_key else None,
        base_url=new_config.base_url,
        temperature=new_config.temperature,
        max_tokens=new_config.max_tokens,
        is_default=new_config.is_default,
        connection_status=new_config.connection_status,
        connection_error=new_config.connection_error,
        last_tested_at=new_config.last_tested_at.isoformat() if new_config.last_tested_at else None,
        display_name=new_config.display_name,
        requires_api_key=new_config.requires_api_key,
        requires_base_url=new_config.requires_base_url,
        created_at=new_config.created_at.isoformat(),
        updated_at=new_config.updated_at.isoformat()
    )


@router.get("/{config_id}", response_model=LLMConfigurationResponse)
async def get_configuration(
    config_id: int,
    user_id: int = Query(..., gt=0, description="User ID for authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific LLM configuration."""
    result = await db.execute(
        select(LLMConfiguration)
        .where(and_(
            LLMConfiguration.id == config_id,
            LLMConfiguration.user_id == user_id
        ))
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return LLMConfigurationResponse(
        id=config.id,
        user_id=config.user_id,
        name=config.name,
        provider=config.provider,
        model=config.model,
        api_key="***" if config.api_key else None,
        base_url=config.base_url,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        is_default=config.is_default,
        connection_status=config.connection_status,
        connection_error=config.connection_error,
        last_tested_at=config.last_tested_at.isoformat() if config.last_tested_at else None,
        display_name=config.display_name,
        requires_api_key=config.requires_api_key,
        requires_base_url=config.requires_base_url,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat()
    )


@router.put("/{config_id}", response_model=LLMConfigurationResponse)
async def update_configuration(
    config_id: int,
    user_id: int = Query(..., gt=0, description="User ID for authorization"),
    config_update: LLMConfigurationUpdate = ...,
    db: AsyncSession = Depends(get_db)
):
    """Update an LLM configuration."""
    # Get existing configuration
    result = await db.execute(
        select(LLMConfiguration)
        .where(and_(
            LLMConfiguration.id == config_id,
            LLMConfiguration.user_id == user_id
        ))
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    # If setting as default, unset any existing default
    if config_update.is_default and not config.is_default:
        existing_defaults = (await db.execute(
            select(LLMConfiguration)
            .where(and_(
                LLMConfiguration.user_id == user_id,
                LLMConfiguration.is_default == True,
                LLMConfiguration.id != config_id
            ))
        )).scalars().all()
        
        for existing_default in existing_defaults:
            existing_default.is_default = False
    
    # Update fields
    update_data = config_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    # Reset connection status if provider details changed
    if any(field in update_data for field in ['provider', 'model', 'api_key', 'base_url']):
        config.connection_status = "untested"
        config.connection_error = None
        config.last_tested_at = None
    
    await db.commit()
    await db.refresh(config)
    
    return LLMConfigurationResponse(
        id=config.id,
        user_id=config.user_id,
        name=config.name,
        provider=config.provider,
        model=config.model,
        api_key="***" if config.api_key else None,
        base_url=config.base_url,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        is_default=config.is_default,
        connection_status=config.connection_status,
        connection_error=config.connection_error,
        last_tested_at=config.last_tested_at.isoformat() if config.last_tested_at else None,
        display_name=config.display_name,
        requires_api_key=config.requires_api_key,
        requires_base_url=config.requires_base_url,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat()
    )


@router.delete("/{config_id}")
async def delete_configuration(
    config_id: int,
    user_id: int = Query(..., gt=0, description="User ID for authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Delete an LLM configuration."""
    # Get existing configuration
    result = await db.execute(
        select(LLMConfiguration)
        .where(and_(
            LLMConfiguration.id == config_id,
            LLMConfiguration.user_id == user_id
        ))
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    # Check if this config is currently active in settings
    settings_result = await db.execute(
        select(Settings).where(and_(
            Settings.user_id == user_id,
            Settings.active_llm_config_id == config_id
        ))
    )
    settings = settings_result.scalar_one_or_none()
    
    if settings:
        # Unset the active config in settings
        settings.active_llm_config_id = None
    
    await db.delete(config)
    await db.commit()
    
    return {"message": "Configuration deleted successfully"}


@router.post("/{config_id}/test", response_model=ConnectionTestResult)
async def test_configuration(
    config_id: int,
    user_id: int = Query(..., gt=0, description="User ID for authorization"),
    db: AsyncSession = Depends(get_db)
):
    """
    Test the connection to an LLM configuration.
    
    Updates the configuration's connection status based on the test result.
    """
    # Get configuration
    result = await db.execute(
        select(LLMConfiguration)
        .where(and_(
            LLMConfiguration.id == config_id,
            LLMConfiguration.user_id == user_id
        ))
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    # Test the connection
    test_result = await test_llm_connection(config)
    
    # Update configuration with test results
    config.connection_status = "success" if test_result.success else "failed"
    config.connection_error = test_result.error
    config.last_tested_at = func.now()
    
    await db.commit()
    
    return test_result


@router.post("/{config_id}/set-active")
async def set_active_configuration(
    config_id: int,
    user_id: int = Query(..., gt=0, description="User ID for authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Set a configuration as the active one for the user."""
    # Verify configuration exists and belongs to user
    result = await db.execute(
        select(LLMConfiguration)
        .where(and_(
            LLMConfiguration.id == config_id,
            LLMConfiguration.user_id == user_id
        ))
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    # Get or create settings
    settings_result = await db.execute(
        select(Settings).where(Settings.user_id == user_id)
    )
    settings = settings_result.scalar_one_or_none()
    
    if not settings:
        settings = Settings(user_id=user_id, active_llm_config_id=config_id)
        db.add(settings)
    else:
        settings.active_llm_config_id = config_id
    
    await db.commit()
    
    return {"message": "Configuration set as active", "config_id": config_id}

