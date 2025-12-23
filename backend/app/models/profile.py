"""
User profile model for personal context injection into LLM prompts.
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, String
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

    # Chat UX v2: User preference fields for agent personalization
    # Work style: How the user approaches work
    work_style = Column(
        String(50),
        nullable=True,
        comment="deep_focus, meeting_heavy, context_switcher, structured, flexible"
    )

    # Preferred tone: How the assistant should communicate
    preferred_tone = Column(
        String(50),
        nullable=True,
        comment="professional, friendly, casual, direct, encouraging"
    )

    # Energy pattern: Peak hours, low energy times (JSONB)
    # Example: {"peak_hours": ["9-11", "14-16"], "low_energy": ["13-14", "16-18"]}
    energy_pattern = Column(JSONB, nullable=True)

    # Communication style preferences (JSONB)
    # Example: {"verbosity": "concise", "formality": "informal", "emoji_usage": "minimal"}
    communication_style = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<Profile(user_id={self.user_id})>"






