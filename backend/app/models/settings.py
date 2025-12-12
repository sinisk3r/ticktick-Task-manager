"""
User settings model for LLM provider configuration.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.core.database import Base


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"  # For future iterations


class Settings(Base):
    """User-specific settings for LLM configuration."""

    __tablename__ = "settings"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # LLM Configuration - Dynamic Runtime Configuration
    llm_provider = Column(SQLEnum(LLMProvider), default=LLMProvider.OLLAMA, nullable=False)
    llm_model = Column(String(500), nullable=True)  # Model name for current provider
    llm_api_key = Column(String(500), nullable=True)  # API key for current provider
    llm_base_url = Column(String(500), nullable=True)  # Base URL (for Ollama or custom endpoints)
    llm_temperature = Column(Float, default=0.2, nullable=True)
    llm_max_tokens = Column(Integer, default=1000, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<Settings(user_id={self.user_id}, provider={self.llm_provider})>"
