"""
User memory model for cross-session learning and preference storage.

This model backs the LangGraph memory store with persistent storage for:
- User preferences (tone, work style, communication preferences)
- Learned facts (project context, recurring patterns)
- Work patterns (task creation times, completion rates)
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserMemory(Base):
    """Stores cross-session memory for agent personalization."""

    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Namespace for organizing memory types
    # Examples: "preferences", "learned_facts", "work_patterns"
    namespace = Column(String(100), nullable=False, index=True)

    # Key for the specific memory item (e.g., "preferred_tone", "project_names")
    key = Column(String(255), nullable=False)

    # JSONB value for flexible storage
    # Can store strings, numbers, arrays, or objects
    value = Column(JSONB, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="memories")

    # Composite index for efficient namespace+key lookups
    __table_args__ = (
        Index("ix_user_namespace_key", "user_id", "namespace", "key", unique=True),
    )

    def __repr__(self):
        return f"<UserMemory(user_id={self.user_id}, namespace={self.namespace}, key={self.key})>"
