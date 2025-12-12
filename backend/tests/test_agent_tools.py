import pytest

from app.agent.dispatcher import AgentDispatcher, ConfirmationRequired
from app.agent.tools import (
    FetchTasksInput,
    CreateTaskInput,
    CompleteTaskInput,
    DeleteTaskInput,
    fetch_tasks,
    create_task,
    complete_task,
)
from app.models.user import User


@pytest.mark.asyncio
async def test_create_and_fetch_tasks(db_session):
    user = User(email="agent@test.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    created = await create_task(
        CreateTaskInput(user_id=user.id, title="Agent task", description="demo"),
        db_session,
    )
    assert created["task"]["title"] == "Agent task"

    fetched = await fetch_tasks(FetchTasksInput(user_id=user.id), db_session)
    assert fetched["total"] == 1
    assert fetched["tasks"][0]["id"] == created["task"]["id"]


@pytest.mark.asyncio
async def test_complete_and_delete_requires_confirmation(db_session):
    user = User(email="complete@test.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    created = await create_task(
        CreateTaskInput(user_id=user.id, title="Finish soon"),
        db_session,
    )

    completed = await complete_task(
        CompleteTaskInput(user_id=user.id, task_id=created["task"]["id"]),
        db_session,
    )
    assert completed["task"]["status"] == "completed"

    dispatcher = AgentDispatcher()
    with pytest.raises(ConfirmationRequired):
        await dispatcher.dispatch(
            "delete_task",
            {"user_id": user.id, "task_id": created["task"]["id"]},
            db_session,
            "trace-test",
        )

