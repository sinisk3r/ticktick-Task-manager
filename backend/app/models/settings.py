"""
User settings model for LLM provider configuration.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.core.database import Base


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"  # For future iterations


class Settings(Base):
    """User-specific settings for LLM configuration."""

    __tablename__ = "settings"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # LLM Configuration
    llm_provider = Column(SQLEnum(LLMProvider), default=LLMProvider.OLLAMA, nullable=False)
    ollama_url = Column(String(500), default="http://localhost:11434", nullable=True)
    ollama_model = Column(String(255), default="qwen3:4b", nullable=True)

    # Future provider settings (Iteration 3)
    gemini_api_key = Column(String(500), nullable=True)
    openrouter_api_key = Column(String(500), nullable=True)
    openrouter_model = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<Settings(user_id={self.user_id}, provider={self.llm_provider})>"
