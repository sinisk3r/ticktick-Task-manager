"""
TaskSuggestion model for AI-generated task improvement suggestions.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.core.database import Base


class SuggestionStatus(str, Enum):
    """Status of AI suggestion."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TaskSuggestion(Base):
    """AI-generated suggestions for task improvements."""

    __tablename__ = "task_suggestions"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Suggestion Details
    suggestion_type = Column(String(100), nullable=False)  # priority, tags, quadrant, start_date, etc.
    current_value = Column(JSONB, nullable=True)  # Current value (before suggestion)
    suggested_value = Column(JSONB, nullable=False)  # AI-suggested value
    reason = Column(String(1000), nullable=False)  # Explanation from AI
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0

    # Status Tracking
    status = Column(SQLEnum(SuggestionStatus), default=SuggestionStatus.PENDING, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_user = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    task = relationship("Task", back_populates="suggestions")

    def __repr__(self):
        return f"<TaskSuggestion(id={self.id}, task_id={self.task_id}, type='{self.suggestion_type}', status={self.status})>"
