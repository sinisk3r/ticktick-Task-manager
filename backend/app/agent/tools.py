"""
Tool implementations for the agent runtime using LangChain @tool decorator.

Each tool returns a structured dict that can be streamed to the frontend timeline.
Tools are automatically discovered via the @tool decorator.

Note: The 'db' parameter is injected by the dispatcher and is NOT visible to the LLM.
We use Annotated with InjectedToolArg to hide it from schema generation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.tools import InjectedToolArg, tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, EisenhowerQuadrant
from app.models.user import User
from app.services import OllamaService
from app.services.prompt_utils import build_profile_context

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Shared payload helpers
# -----------------------------------------------------------------------------


def task_to_payload(task: Task) -> Dict[str, Any]:
    """Serialize a Task model into a compact payload for the UI."""
    return {
        "id": task.id,
        "user_id": task.user_id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value if hasattr(task.status, "value") else task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "start_date": task.start_date.isoformat() if task.start_date else None,
        "ticktick_priority": task.ticktick_priority,
        "ticktick_tags": task.ticktick_tags or [],
        "project_id": task.project_id,
        "project_name": task.project_name,
        "ticktick_project_id": task.ticktick_project_id,
        "eisenhower_quadrant": (
            task.eisenhower_quadrant.value
            if hasattr(task.eisenhower_quadrant, "value")
            else task.eisenhower_quadrant
        ),
        "effective_quadrant": (
            task.effective_quadrant.value
            if hasattr(task.effective_quadrant, "value")
            else task.effective_quadrant
        ),
        "manual_quadrant_override": (
            task.manual_quadrant_override.value
            if hasattr(task.manual_quadrant_override, "value")
            else task.manual_quadrant_override
        ),
        "urgency_score": task.urgency_score,
        "importance_score": task.importance_score,
        "analysis_reasoning": task.analysis_reasoning,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


# -----------------------------------------------------------------------------
# Tool implementations using @tool decorator
# -----------------------------------------------------------------------------


@tool(parse_docstring=True)
async def fetch_tasks(
    config: Annotated[RunnableConfig, InjectedToolArg()],
    status: Optional[str] = None,
    quadrant: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List tasks for the user with optional filters.

    Use this tool to retrieve tasks for a user. You can filter by status
    (ACTIVE, COMPLETED, DELETED) or eisenhower quadrant (Q1, Q2, Q3, Q4).
    Results are paginated with limit and offset.

    Args:
        status: Optional task status filter (ACTIVE, COMPLETED, DELETED)
        quadrant: Optional eisenhower quadrant filter (Q1, Q2, Q3, Q4)
        limit: Maximum number of tasks to return (default: 50, max: 200)
        offset: Number of tasks to skip for pagination (default: 0)
    """
    # Extract injected parameters from config
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config", "tasks": [], "total": 0}

    # Validate limit
    if limit < 1 or limit > 200:
        limit = min(max(limit, 1), 200)
    if offset < 0:
        offset = 0

    try:
        query = select(Task).where(Task.user_id == user_id)

        # Parse status enum if provided
        if status:
            try:
                status_enum = TaskStatus(status)
                query = query.where(Task.status == status_enum)
            except ValueError:
                logger.warning(f"Invalid status value '{status}' provided to fetch_tasks, ignoring")

        # Parse quadrant enum if provided
        if quadrant:
            try:
                quadrant_enum = EisenhowerQuadrant(quadrant)
                query = query.where(
                    (Task.manual_quadrant_override == quadrant_enum)
                    | (
                        Task.manual_quadrant_override.is_(None)
                        & (Task.eisenhower_quadrant == quadrant_enum)
                    )
                )
            except ValueError:
                logger.warning(f"Invalid quadrant value '{quadrant}' provided to fetch_tasks, ignoring")

        query = query.order_by(Task.created_at.desc()).limit(limit).offset(offset)

        result = await db.execute(query)
        tasks = result.scalars().all()

        logger.info(f"fetch_tasks: user_id={user_id}, found {len(tasks)} tasks (status={status}, quadrant={quadrant})")

        return {
            "tasks": [task_to_payload(t) for t in tasks],
            "total": len(tasks),
            "summary": f"Found {len(tasks)} tasks",
        }
    except Exception as e:
        logger.error(f"fetch_tasks failed for user_id={user_id}: {e}", exc_info=True)
        return {
            "tasks": [],
            "total": 0,
            "summary": f"Error fetching tasks: {str(e)}",
            "error": str(e),
        }


@tool(parse_docstring=True)
async def fetch_task(
    task_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg()],
) -> Dict[str, Any]:
    """Get a single task by ID.

    Use this tool to retrieve detailed information about a specific task.
    Returns an error if the task doesn't exist or doesn't belong to the user.

    Args:
        task_id: ID of the task to retrieve (required, must be > 0)
    """
    # Extract injected parameters from config
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    if task_id <= 0:
        return {"error": "task_id must be greater than 0"}

    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "Task not found"}

    return {"task": task_to_payload(task), "summary": f"Loaded task {task.id}"}


@tool(parse_docstring=True)
async def create_task(
    title: str,
    config: Annotated[RunnableConfig, InjectedToolArg()],
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    ticktick_priority: Optional[int] = None,
    ticktick_tags: Optional[List[str]] = None,
    project_id: Optional[int] = None,
    project_name: Optional[str] = None,
    ticktick_project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new task for the user.

    Use this tool to create tasks based on user requests. Provide a clear,
    concise title (max 120 chars, no quotes). Only include description if it
    adds meaningful context beyond the title - avoid duplicating the title.

    Args:
        title: Concise task title without quotes, max 120 chars (required)
        description: Optional details that differ from title. Provide meaningful context or omit.
        due_date: Optional ISO datetime string if task has a deadline
        ticktick_priority: Priority level - 0 (none), 1 (low), 3 (medium), 5 (high)
        ticktick_tags: Optional list of tag strings
        project_id: Optional project ID
        project_name: Optional project name
        ticktick_project_id: Optional TickTick project ID

    Examples:
        - create_task(title="Review PR #456", description="Full code review focusing on security and performance", ticktick_tags=["code-review", "urgent"])
        - create_task(title="Weekly team sync", due_date="2025-12-15T10:00:00", ticktick_priority=3)
        - create_task(title="Fix login bug", ticktick_priority=5, ticktick_tags=["bug"])
    """
    # Extract injected parameters from config
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    # Validate and clean title
    if not title:
        return {"error": "title cannot be empty"}

    cleaned_title = title.strip().strip('"').strip("'")
    if not cleaned_title:
        return {"error": "title cannot be empty after cleaning"}

    if len(cleaned_title) > 120:
        cleaned_title = cleaned_title[:117] + "..."

    # Validate and clean description
    cleaned_description = None
    if description:
        cleaned_description = description.strip()
        # Reject if description matches title
        if cleaned_description == cleaned_title or cleaned_description.lower() == cleaned_title.lower():
            cleaned_description = None
        # Reject if too short to add value
        elif len(cleaned_description) < 10:
            cleaned_description = None

    # Validate priority
    if ticktick_priority is not None:
        if ticktick_priority < 0 or ticktick_priority > 5:
            return {"error": "ticktick_priority must be between 0 and 5"}

    task = Task(
        user_id=user_id,
        title=cleaned_title,
        description=cleaned_description,
        due_date=due_date,
        ticktick_priority=ticktick_priority or 0,
        ticktick_tags=ticktick_tags or [],
        project_id=project_id,
        project_name=project_name,
        ticktick_project_id=ticktick_project_id,
        status=TaskStatus.ACTIVE,
        is_sorted=False,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info("Agent created task %s for user %s", task.id, user_id)

    return {
        "task": task_to_payload(task),
        "summary": f"Created task '{task.title}'",
    }


@tool(parse_docstring=True)
async def update_task(
    task_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg()],
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    start_date: Optional[datetime] = None,
    ticktick_priority: Optional[int] = None,
    ticktick_tags: Optional[List[str]] = None,
    time_estimate: Optional[int] = None,
    all_day: Optional[bool] = None,
) -> Dict[str, Any]:
    """Update an existing task with new values.

    Use this tool to modify task properties. Only provide the fields you want
    to change. The tool will track what changed and return a summary.

    Args:
        task_id: ID of task to update (required, must be > 0)
        title: New title (max 120 chars, quotes removed automatically)
        description: New description or null to clear
        due_date: New due date as ISO datetime
        start_date: New start date as ISO datetime
        ticktick_priority: New priority: 0 (none), 1 (low), 3 (medium), 5 (high)
        ticktick_tags: New tags list
        time_estimate: Duration in minutes (must be > 0)
        all_day: All day event flag
    """
    # Extract injected parameters from config
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    if task_id <= 0:
        return {"error": "task_id must be greater than 0"}

    # Fetch task with ownership check
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": f"Task {task_id} not found or not owned by user"}

    # Track what changed for summary
    changes = []

    # Clean and validate title if provided
    if title is not None:
        cleaned_title = title.strip().strip('"').strip("'")
        if cleaned_title and cleaned_title != task.title:
            if len(cleaned_title) > 120:
                cleaned_title = cleaned_title[:117] + "..."
            task.title = cleaned_title
            changes.append(f"title → '{cleaned_title}'")

    # Update description
    if description is not None and description != task.description:
        task.description = description
        changes.append("description updated")

    # Update dates
    if due_date is not None and due_date != task.due_date:
        task.due_date = due_date
        changes.append(f"due date → {due_date.strftime('%Y-%m-%d %H:%M') if due_date else 'cleared'}")

    if start_date is not None and start_date != task.start_date:
        task.start_date = start_date
        changes.append(f"start date → {start_date.strftime('%Y-%m-%d %H:%M')}")

    # Validate and update priority
    if ticktick_priority is not None:
        if ticktick_priority < 0 or ticktick_priority > 5:
            return {"error": "ticktick_priority must be between 0 and 5"}
        if ticktick_priority != task.ticktick_priority:
            task.ticktick_priority = ticktick_priority
            changes.append(f"priority → {ticktick_priority}")

    # Update tags
    if ticktick_tags is not None and ticktick_tags != task.ticktick_tags:
        task.ticktick_tags = ticktick_tags
        changes.append(f"tags → {ticktick_tags}")

    # Validate and update time estimate
    if time_estimate is not None:
        if time_estimate <= 0:
            return {"error": "time_estimate must be greater than 0"}
        if time_estimate != task.time_estimate:
            task.time_estimate = time_estimate
            changes.append(f"duration → {time_estimate} mins")

    # Update all_day flag
    if all_day is not None and all_day != task.all_day:
        task.all_day = all_day
        changes.append(f"all_day → {all_day}")

    if not changes:
        return {
            "task": task_to_payload(task),
            "summary": f"No changes made to task '{task.title}'"
        }

    task.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)

    logger.info("Agent updated task %s for user %s: %s", task.id, user_id, ", ".join(changes))

    return {
        "task": task_to_payload(task),
        "summary": f"Updated task '{task.title}': {', '.join(changes)}",
        "changes": changes
    }


@tool(parse_docstring=True)
async def complete_task(
    task_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg()],
) -> Dict[str, Any]:
    """Mark a task as completed.

    Use this tool when a user indicates they've finished a task or wants to
    mark it as done. This changes the task status to COMPLETED.

    Args:
        task_id: ID of the task to complete (required, must be > 0)
    """
    # Extract injected parameters from config
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    if task_id <= 0:
        return {"error": "task_id must be greater than 0"}

    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "Task not found"}

    task.status = TaskStatus.COMPLETED
    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    logger.info("Agent completed task %s for user %s", task.id, user_id)

    return {
        "task": task_to_payload(task),
        "summary": f"Completed task '{task.title}'",
    }


@tool(parse_docstring=True)
async def delete_task(
    task_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg()],
    confirm: bool = False,
    soft_delete: bool = True,
) -> Dict[str, Any]:
    """Delete a task (soft delete by default).

    Use this tool to remove tasks. Soft delete (default) changes status to
    DELETED but preserves the record. Hard delete permanently removes it.

    Args:
        task_id: ID of the task to delete (required, must be > 0)
        confirm: Must be true for destructive actions (default: False)
        soft_delete: If true, soft delete (preserve record); if false, hard delete (default: True)
    """
    # Extract injected parameters from config
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    if task_id <= 0:
        return {"error": "task_id must be greater than 0"}

    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "Task not found"}

    task_title = task.title

    if soft_delete:
        task.status = TaskStatus.DELETED
        task.updated_at = datetime.utcnow()
        await db.commit()
        summary = f"Soft-deleted task '{task_title}'"
        logger.info("Agent soft-deleted task %s for user %s", task_id, user_id)
    else:
        await db.delete(task)
        await db.commit()
        summary = f"Deleted task '{task_title}'"
        logger.info("Agent hard-deleted task %s for user %s", task_id, user_id)

    return {"summary": summary, "task_id": task_id}


@tool(parse_docstring=True)
async def quick_analyze_task(
    description: str,
    config: Annotated[RunnableConfig, InjectedToolArg()],
    title: Optional[str] = None,
    due_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Run lightweight analysis on a task description.

    Use this tool to get urgency/importance analysis and quadrant suggestions
    for a task description using the Ollama LLM. Falls back gracefully if
    the LLM is unavailable.

    Args:
        description: Task description to analyze (required, min 1 char)
        title: Optional task title (defaults to first 80 chars of description)
        due_date: Optional due date as ISO datetime
    """
    # Extract injected parameters from config
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    if not description or len(description) < 1:
        return {"error": "description must have at least 1 character"}

    # Set default title if not provided
    if not title:
        title = (description[:77] + "...") if len(description) > 80 else description

    # Validate title length
    if title and len(title) > 500:
        title = title[:497] + "..."

    ollama = OllamaService()
    profile_context = None

    # Try to fetch profile context; ignore errors in agent path
    try:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.profile:
            profile_context = build_profile_context(user.profile)
    except Exception:
        profile_context = None

    if not await ollama.health_check():
        return {
            "error": "LLM unavailable for quick analysis",
            "summary": "LLM unavailable; skipped analysis",
        }

    analysis = await ollama.analyze_task(description, profile_context=profile_context)

    return {
        "analysis": {
            "urgency": analysis.urgency,
            "importance": analysis.importance,
            "quadrant": analysis.quadrant,
            "reasoning": analysis.reasoning,
        },
        "suggested_priority": analysis.urgency if analysis.urgency else None,
        "title": title,
        "summary": f"Analysis suggests {analysis.quadrant} (urgency {analysis.urgency}, importance {analysis.importance})",
    }


# -----------------------------------------------------------------------------
# Export all tools for discovery
__all__ = [
    "fetch_tasks",
    "fetch_task",
    "create_task",
    "update_task",
    "complete_task",
    "delete_task",
    "quick_analyze_task",
    "task_to_payload",
]

