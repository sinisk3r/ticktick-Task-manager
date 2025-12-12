"""
LLM Configuration model for storing saved provider configurations.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum as SQLEnum, Boolean
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


class LLMConfiguration(Base):
    """
    Saved LLM provider configurations.
    
    Users can create multiple configurations (e.g., "Local Ollama", "OpenRouter GPT-4", etc.)
    and switch between them in settings.
    """

    __tablename__ = "llm_configurations"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Configuration Metadata
    name = Column(String(100), nullable=False)  # User-friendly name like "Local Ollama", "OpenRouter GPT-4"
    is_default = Column(Boolean, default=False, nullable=False)  # One default config per user

    # Provider Configuration
    provider = Column(SQLEnum(LLMProvider), nullable=False)
    model = Column(String(500), nullable=False)  # Model name for the provider
    api_key = Column(String(500), nullable=True)  # API key (encrypted)
    base_url = Column(String(500), nullable=True)  # Base URL (for Ollama or custom endpoints)
    
    # Generation Parameters
    temperature = Column(Float, default=0.2, nullable=False)
    max_tokens = Column(Integer, default=1000, nullable=False)

    # Connection Status (cached from last test)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    connection_status = Column(String(20), default="untested", nullable=False)  # untested, success, failed
    connection_error = Column(String(500), nullable=True)  # Error message if connection failed

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="llm_configurations")

    def __repr__(self):
        return f"<LLMConfiguration(id={self.id}, name='{self.name}', provider={self.provider})>"

    @property
    def display_name(self) -> str:
        """Generate a display name for the configuration."""
        return f"{self.name} ({self.provider.value} | {self.model})"

    @property
    def requires_api_key(self) -> bool:
        """Check if this provider requires an API key."""
        return self.provider != LLMProvider.OLLAMA

    @property
    def requires_base_url(self) -> bool:
        """Check if this provider requires a base URL."""
        return self.provider == LLMProvider.OLLAMA
