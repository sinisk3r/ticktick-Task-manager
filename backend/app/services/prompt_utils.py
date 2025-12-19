"""
Utilities for constructing compact prompt context strings.
"""
from typing import Optional

from app.models.profile import Profile


def build_profile_context(profile: Optional[Profile], max_chars: int = 700) -> Optional[str]:
    """Build a short, bulletized profile string suitable for small LLMs."""
    if not profile:
        return None

    sections = []

    if profile.people:
        people = "; ".join(profile.people[:10])
        sections.append(f"People & roles: {people}")

    if profile.pets:
        pets = "; ".join(profile.pets[:5])
        sections.append(f"Pets: {pets}")

    if profile.activities:
        activities = "; ".join(profile.activities[:10])
        sections.append(f"Activities: {activities}")

    if profile.notes:
        sections.append(f"Notes: {profile.notes[:300]}")

    context = " | ".join([s for s in sections if s])
    if not context:
        return None

    return context[:max_chars]




