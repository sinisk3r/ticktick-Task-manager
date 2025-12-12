"""
User settings model - now references saved LLM configurations.
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Settings(Base):
    """
    User-specific settings.
    
    Now references a saved LLM configuration instead of storing provider details directly.
    """

    __tablename__ = "settings"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Active LLM Configuration
    active_llm_config_id = Column(Integer, ForeignKey("llm_configurations.id", ondelete="SET NULL"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="settings")
    active_llm_config = relationship("LLMConfiguration", foreign_keys=[active_llm_config_id])

    def __repr__(self):
        return f"<Settings(user_id={self.user_id}, active_config_id={self.active_llm_config_id})>"