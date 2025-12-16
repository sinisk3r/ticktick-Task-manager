import pytest

from app.models.profile import Profile
from app.services.prompt_utils import build_profile_context


def test_build_profile_context_none_when_no_profile():
    assert build_profile_context(None) is None


def test_build_profile_context_includes_sections():
    profile = Profile(
        user_id=1,
        people=["Sam (manager)", "Alex (partner)"],
        pets=["Ari (cat)"],
        activities=["Climbing Tue", "Yoga Sat"],
        notes="Morning focus time",
    )

    context = build_profile_context(profile)
    assert context
    assert "People & roles" in context
    assert "Pets" in context
    assert "Activities" in context
    assert "Notes" in context


def test_build_profile_context_truncates():
    profile = Profile(
        user_id=1,
        notes="x" * 2000,
    )
    context = build_profile_context(profile, max_chars=100)
    assert len(context) <= 100



