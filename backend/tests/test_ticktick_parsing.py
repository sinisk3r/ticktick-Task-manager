import pytest

from app.services.ticktick import TickTickService


@pytest.fixture
def ticktick_service():
    return TickTickService()


def test_parse_datetime_handles_z_suffix(ticktick_service):
    parsed = ticktick_service._parse_datetime("2025-12-15T09:00:00Z")
    assert parsed is not None
    assert parsed.year == 2025
    assert parsed.hour == 9


def test_calculate_time_estimate_from_pomodoro(ticktick_service):
    minutes = ticktick_service._calculate_time_estimate(
        [{"estimatedPomo": 2}, {"estimatedPomo": 1}]
    )
    assert minutes == 75


def test_calculate_focus_time_seconds_to_minutes(ticktick_service):
    minutes = ticktick_service._calculate_focus_time(
        [{"focusTime": 1800}, {"focusTime": 3600}]
    )
    assert minutes == 90


def test_calculate_time_estimate_returns_none_when_empty(ticktick_service):
    assert ticktick_service._calculate_time_estimate([]) is None

