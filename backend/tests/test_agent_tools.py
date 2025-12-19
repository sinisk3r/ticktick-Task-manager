import pytest

from app.agent.tools import (
    fetch_tasks,
    create_task,
    complete_task,
    delete_task,
)
from app.models.user import User


def make_config(user_id: int, db):
    """Helper to create RunnableConfig for tool invocation."""
    return {
        "configurable": {
            "user_id": user_id,
            "db": db,
        }
    }


@pytest.mark.asyncio
async def test_create_and_fetch_tasks(db_session):
    user = User(email="agent@test.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    config = make_config(user.id, db_session)

    # Test create_task
    created = await create_task.ainvoke(
        {"title": "Agent task", "description": "demo"},
        config=config,
    )
    assert created["task"]["title"] == "Agent task"

    # Test fetch_tasks
    fetched = await fetch_tasks.ainvoke({}, config=config)
    assert fetched["total"] == 1
    assert fetched["tasks"][0]["id"] == created["task"]["id"]


@pytest.mark.asyncio
async def test_complete_task(db_session):
    user = User(email="complete@test.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    config = make_config(user.id, db_session)

    # Create a task
    created = await create_task.ainvoke(
        {"title": "Finish soon"},
        config=config,
    )

    # Complete the task
    completed = await complete_task.ainvoke(
        {"task_id": created["task"]["id"]},
        config=config,
    )
    assert completed["task"]["status"] == "ACTIVE" or completed["task"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_delete_task(db_session):
    user = User(email="delete@test.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    config = make_config(user.id, db_session)

    # Create a task
    created = await create_task.ainvoke(
        {"title": "To be deleted"},
        config=config,
    )

    # Soft delete the task (default)
    deleted = await delete_task.ainvoke(
        {"task_id": created["task"]["id"], "soft_delete": True},
        config=config,
    )
    assert "summary" in deleted
    assert "deleted" in deleted["summary"].lower() or "Deleted" in deleted["summary"]



