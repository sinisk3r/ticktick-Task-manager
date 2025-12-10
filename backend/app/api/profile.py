"""
Profile API endpoints for storing lightweight personal context used in LLM prompts.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.profile import Profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfilePayload(BaseModel):
    """Incoming payload for profile updates."""

    people: Optional[List[str]] = Field(
        default=None, description="Key people and their roles", max_items=20
    )
    pets: Optional[List[str]] = Field(default=None, description="Pets or animals", max_items=20)
    activities: Optional[List[str]] = Field(default=None, description="Regular activities", max_items=20)
    notes: Optional[str] = Field(default=None, max_length=1000, description="Freeform notes")

    @field_validator("people", "pets", "activities", mode="before")
    @classmethod
    def _normalize_list(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return None
        cleaned = []
        for item in value:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if text:
                cleaned.append(text[:200])  # enforce per-item max length
            if len(cleaned) >= 20:
                break
        return cleaned or None

    @field_validator("notes")
    @classmethod
    def _truncate_notes(cls, value: Optional[str]):
        if value is None:
            return value
        value = value.strip()
        return value[:1000] if value else None


class ProfileResponse(BaseModel):
    """Outgoing payload representing stored profile context."""

    user_id: int
    people: List[str] = []
    pets: List[str] = []
    activities: List[str] = []
    notes: Optional[str] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "people": ["Sam (manager)", "Alex (partner)"],
                "pets": ["Ari (cat)"],
                "activities": ["Climbing Tue/Thu", "Yoga Sat"],
                "notes": "Prefers mornings for focus work",
            }
        }


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user_id: int = Query(..., gt=0, description="User ID to get profile for"),
    db: AsyncSession = Depends(get_db),
):
    """Fetch the user's profile context. Returns empty defaults if none exist."""
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if profile:
        return profile

    return ProfileResponse(user_id=user_id, people=[], pets=[], activities=[], notes=None)


@router.put("", response_model=ProfileResponse)
async def upsert_profile(
    user_id: int = Query(..., gt=0, description="User ID to update profile for"),
    payload: ProfilePayload = ...,
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update the user's profile context.

    Content is intentionally small to keep prompts concise for 4B models.
    """
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)

    # Update fields
    profile.people = payload.people
    profile.pets = payload.pets
    profile.activities = payload.activities
    profile.notes = payload.notes

    await db.flush()
    await db.refresh(profile)

    return profile

