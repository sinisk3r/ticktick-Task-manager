"""
Middleware for dynamic prompt generation and personalization.

This middleware injects user preferences, work style, and communication
preferences into the system prompt at runtime, enabling personalized
agent responses.
"""
import logging
from typing import Any, Dict
from langchain_core.messages import SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.profile import Profile
from app.models.memory import UserMemory

logger = logging.getLogger(__name__)


async def load_user_preferences(user_id: int, db: AsyncSession) -> Dict[str, Any]:
    """
    Load user preferences from Profile and UserMemory tables.

    Args:
        user_id: User ID to load preferences for
        db: Database session

    Returns:
        Dictionary with user preferences:
        - work_style: str (e.g., "deep_focus", "structured")
        - preferred_tone: str (e.g., "friendly", "professional")
        - energy_pattern: dict (peak hours, low energy times)
        - communication_style: dict (verbosity, formality)
        - custom_facts: list (learned facts from UserMemory)
    """
    preferences = {
        "work_style": None,
        "preferred_tone": "friendly",  # Default
        "energy_pattern": {},
        "communication_style": {},
        "custom_facts": [],
    }

    try:
        # Load profile
        result = await db.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            if profile.work_style:
                preferences["work_style"] = profile.work_style
            if profile.preferred_tone:
                preferences["preferred_tone"] = profile.preferred_tone
            if profile.energy_pattern:
                preferences["energy_pattern"] = profile.energy_pattern
            if profile.communication_style:
                preferences["communication_style"] = profile.communication_style

        # Load custom memories from UserMemory
        # Get preferences namespace
        result = await db.execute(
            select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.namespace == "preferences"
            )
        )
        memories = result.scalars().all()

        for memory in memories:
            # Store each preference key-value pair
            preferences[memory.key] = memory.value

        # Get learned facts
        result = await db.execute(
            select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.namespace == "learned_facts"
            )
        )
        facts = result.scalars().all()
        preferences["custom_facts"] = [fact.value for fact in facts]

    except Exception as e:
        logger.warning(f"Failed to load user preferences for user {user_id}: {e}")

    return preferences


def generate_personalized_system_prompt(preferences: Dict[str, Any]) -> str:
    """
    Generate system prompt based on user preferences.

    Args:
        preferences: User preferences dictionary from load_user_preferences

    Returns:
        Personalized system prompt string
    """
    base_prompt = "You are Context, an AI task management assistant."

    # Adapt tone
    tone = preferences.get("preferred_tone", "friendly")
    if tone == "casual":
        base_prompt += " Keep it relaxed and friendly. Use contractions, be warm and conversational."
    elif tone == "direct":
        base_prompt += " Be concise and to-the-point. No fluff. Get straight to the answer."
    elif tone == "encouraging":
        base_prompt += " Be supportive and motivational. Celebrate progress and encourage growth."
    elif tone == "professional":
        base_prompt += " Use formal, professional language. Be clear and business-like."
    else:  # Default friendly
        base_prompt += " Be warm, helpful, and conversational."

    # Adapt to work style
    work_style = preferences.get("work_style")
    if work_style == "structured":
        base_prompt += " Offer organized, step-by-step guidance. Provide clear frameworks."
    elif work_style == "flexible":
        base_prompt += " Keep suggestions open-ended. Allow room for user's own approach."
    elif work_style == "deep_focus":
        base_prompt += " Prioritize deep work blocks. Minimize interruptions and context switching."
    elif work_style == "meeting_heavy":
        base_prompt += " Account for meeting overhead. Suggest time-efficient task approaches."

    # Communication style adjustments
    comm_style = preferences.get("communication_style", {})
    if comm_style.get("verbosity") == "concise":
        base_prompt += " Keep responses very brief (1-2 sentences when possible)."
    elif comm_style.get("verbosity") == "detailed":
        base_prompt += " Provide thorough explanations with context and examples."

    # Add learned facts context
    custom_facts = preferences.get("custom_facts", [])
    if custom_facts:
        facts_str = ", ".join(str(fact) for fact in custom_facts[:5])  # Limit to 5
        base_prompt += f"\n\nContext about the user: {facts_str}"

    return base_prompt


def create_personalized_system_message(preferences: Dict[str, Any]) -> SystemMessage:
    """
    Create a LangChain SystemMessage with personalized prompt.

    Args:
        preferences: User preferences dictionary

    Returns:
        SystemMessage for agent initialization
    """
    prompt = generate_personalized_system_prompt(preferences)
    return SystemMessage(content=prompt)
