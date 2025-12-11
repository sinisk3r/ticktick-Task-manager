"""
Task model with LLM analysis results and Eisenhower matrix classification.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.core.database import Base


class TaskStatus(str, Enum):
    """Task status enum."""
    ACTIVE = "active"
    COMPLETED = "completed"
    DELETED = "deleted"


class EisenhowerQuadrant(str, Enum):
    """Eisenhower matrix quadrants."""
    Q1 = "Q1"  # Urgent & Important (Do First)
    Q2 = "Q2"  # Not Urgent, Important (Schedule)
    Q3 = "Q3"  # Urgent, Not Important (Delegate)
    Q4 = "Q4"  # Neither (Eliminate)


class Task(Base):
    """Task model with TickTick sync and LLM analysis."""

    __tablename__ = "tasks"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # TickTick Integration
    ticktick_task_id = Column(String(255), unique=True, nullable=True, index=True)
    ticktick_project_id = Column(String(255), nullable=True)

    # Basic Task Info
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.ACTIVE, nullable=False, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)

    # LLM Analysis Results
    urgency_score = Column(Float, nullable=True)  # 1-10
    importance_score = Column(Float, nullable=True)  # 1-10
    effort_hours = Column(Float, nullable=True)  # Estimated hours
    eisenhower_quadrant = Column(SQLEnum(EisenhowerQuadrant), nullable=True, index=True)
    analysis_reasoning = Column(Text, nullable=True)  # LLM explanation
    blockers = Column(JSONB, nullable=True)  # List of potential blockers
    tags = Column(JSONB, nullable=True)  # Suggested tags

    # Manual Overrides (user can override LLM)
    manual_priority_override = Column(Integer, nullable=True)  # 1-4 (quadrant override)
    manual_quadrant_override = Column(SQLEnum(EisenhowerQuadrant), nullable=True)
    manual_override_reason = Column(Text, nullable=True)
    manual_override_source = Column(String(255), nullable=True)  # who/what set the override
    manual_override_at = Column(DateTime(timezone=True), nullable=True)
    manual_order = Column(Integer, nullable=True, index=True)  # per-quadrant manual ordering

    # Sorting Status
    is_sorted = Column(Boolean, default=False, nullable=False, index=True)  # False = Unsorted, True = In Matrix

    # Calendar Integration (future iteration)
    calendar_event_id = Column(String(255), nullable=True)
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)

    # TickTick Extended Metadata
    ticktick_priority = Column(Integer, nullable=True)  # 0=None, 1=Low, 3=Medium, 5=High
    start_date = Column(DateTime(timezone=True), nullable=True)
    all_day = Column(Boolean, default=False, nullable=False)
    reminder_time = Column(DateTime(timezone=True), nullable=True)
    repeat_flag = Column(String(255), nullable=True)

    # Organization
    project_name = Column(String(500), nullable=True)
    parent_task_id = Column(String(255), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    column_id = Column(String(255), nullable=True)

    # Additional Metadata
    ticktick_tags = Column(JSONB, nullable=True)  # JSON array of tags
    time_estimate = Column(Integer, nullable=True)  # minutes
    focus_time = Column(Integer, nullable=True)  # minutes

    # Sync Tracking
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    last_modified_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    sync_version = Column(Integer, default=1, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    analyzed_at = Column(DateTime(timezone=True), nullable=True)  # When LLM analysis was done

    # Relationships
    user = relationship("User", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    suggestions = relationship("TaskSuggestion", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title[:30]}...', quadrant={self.eisenhower_quadrant})>"

    @property
    def effective_quadrant(self) -> EisenhowerQuadrant:
        """Get the effective quadrant (manual override takes precedence)."""
        return self.manual_quadrant_override or self.eisenhower_quadrant
