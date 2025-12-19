"""
User profile model for personal context injection into LLM prompts.
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Profile(Base):
    """Stores lightweight, user-provided context used by LLM analysis."""

    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # Structured context (small lists of short strings)
    people = Column(JSONB, nullable=True)  # e.g., ["Ari (cat)", "Sam (manager)"]
    pets = Column(JSONB, nullable=True)  # e.g., ["Ari (cat)"]
    activities = Column(JSONB, nullable=True)  # e.g., ["Climbing Tue/Thu", "Yoga Sat"]
    notes = Column(Text, nullable=True)  # Freeform but truncated before saving

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<Profile(user_id={self.user_id})>"




