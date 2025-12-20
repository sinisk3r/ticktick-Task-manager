from app.models.task import Task, EisenhowerQuadrant


def test_effective_quadrant_prefers_manual():
    task = Task(
        user_id=1,
        title="Test",
        description="desc",
        eisenhower_quadrant=EisenhowerQuadrant.Q2,
        manual_quadrant_override=EisenhowerQuadrant.Q1,
    )
    assert task.effective_quadrant == EisenhowerQuadrant.Q1


def test_effective_quadrant_defaults_to_llm():
    task = Task(
        user_id=1,
        title="Test",
        description="desc",
        eisenhower_quadrant=EisenhowerQuadrant.Q3,
    )
    assert task.effective_quadrant == EisenhowerQuadrant.Q3





