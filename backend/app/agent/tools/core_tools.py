"""
Tool implementations for the agent runtime using LangChain @tool decorator.

Each tool returns a structured dict that can be streamed to the frontend timeline.
Tools are automatically discovered via the @tool decorator.

Note: The 'db' parameter is injected by the dispatcher and is NOT visible to the LLM.
We use Annotated with InjectedToolArg to hide it from schema generation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, List, Optional
import json
from pathlib import Path
from weakref import WeakKeyDictionary

from langchain_core.tools import InjectedToolArg, tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, EisenhowerQuadrant
from app.models.user import User
from app.services import OllamaService
from app.services.prompt_utils import build_profile_context
from app.services.wellbeing_service import WellbeingService

logger = logging.getLogger(__name__)

# Per-session locks to serialize database commits
# Uses WeakKeyDictionary to avoid keeping sessions alive
_session_locks: WeakKeyDictionary[AsyncSession, asyncio.Lock] = WeakKeyDictionary()


def _get_session_lock(db: AsyncSession) -> asyncio.Lock:
    """Get or create a lock for a database session."""
    if db not in _session_locks:
        _session_locks[db] = asyncio.Lock()
    return _session_locks[db]


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
    status: Optional[str] = "active",
    quadrant: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List tasks for the user with optional filters.

    Use this tool to retrieve tasks for a user. By default, returns only active tasks.
    You can filter by status (active, completed, deleted) or eisenhower quadrant (Q1, Q2, Q3, Q4).
    To get all tasks including completed ones, explicitly set status=None.
    Results are paginated with limit and offset.

    Args:
        status: Task status filter (active, completed, deleted). Defaults to active.
               Case-insensitive. Set to None to fetch all tasks regardless of status.
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

        # Parse status enum if provided (case-insensitive)
        if status:
            try:
                status_normalized = status.lower().strip()
                status_enum = TaskStatus(status_normalized)
                query = query.where(Task.status == status_enum)
            except ValueError:
                logger.warning(f"Invalid status value '{status}' provided to fetch_tasks, ignoring filter")

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
    # Use lock to serialize commits when multiple tools run concurrently
    lock = _get_session_lock(db)
    async with lock:
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
    # Use lock to serialize commits when multiple tools run concurrently
    lock = _get_session_lock(db)
    async with lock:
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

    # Use lock to serialize commits when multiple tools run concurrently
    lock = _get_session_lock(db)
    async with lock:
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

    # Use lock to serialize commits when multiple tools run concurrently
    lock = _get_session_lock(db)
    async with lock:
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
# New Tools: V1 MVP + Phase 2
# -----------------------------------------------------------------------------


@tool(parse_docstring=True)
async def detect_stale_tasks(
    config: Annotated[RunnableConfig, InjectedToolArg()],
    days_threshold: int = 14,
    include_completed: bool = False,
    limit: int = 20,
) -> Dict[str, Any]:
    """Find tasks that haven't been updated recently (potential avoidance pattern).

    Use this tool when the user asks about forgotten tasks, stale items, things
    they might be avoiding, or tasks that need attention. Returns tasks sorted
    by staleness (oldest first).

    Args:
        days_threshold: Number of days without update to consider stale (default: 14)
        include_completed: Include completed tasks in analysis (default: False)
        limit: Maximum number of stale tasks to return (default: 20, max: 50)
    """
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config", "stale_tasks": [], "total_stale": 0}

    # Validate and constrain parameters
    days_threshold = max(1, min(days_threshold, 365))
    limit = max(1, min(limit, 50))

    try:
        stale_cutoff = datetime.utcnow() - timedelta(days=days_threshold)

        query = select(Task).where(
            Task.user_id == user_id,
            Task.updated_at < stale_cutoff,
        )

        if not include_completed:
            query = query.where(Task.status == TaskStatus.ACTIVE)

        query = query.order_by(Task.updated_at.asc()).limit(limit)

        result = await db.execute(query)
        tasks = result.scalars().all()

        # Build stale task list with insights
        stale_tasks = []
        quadrant_counts = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0, "None": 0}
        total_staleness_days = 0

        for task in tasks:
            days_stale = (datetime.utcnow() - task.updated_at).days
            total_staleness_days += days_stale

            # Generate staleness info
            if days_stale > 30:
                staleness_reason = f"Untouched for over a month ({days_stale} days)"
                suggested_action = "Consider archiving or deleting if no longer relevant"
            elif days_stale > 21:
                staleness_reason = f"No updates for 3 weeks ({days_stale} days)"
                suggested_action = "Review priority - may need rescheduling"
            else:
                staleness_reason = f"No updates for {days_stale} days"
                suggested_action = "Quick review recommended"

            quadrant = task.eisenhower_quadrant.value if task.eisenhower_quadrant else "None"
            quadrant_counts[quadrant] = quadrant_counts.get(quadrant, 0) + 1

            stale_tasks.append({
                "id": task.id,
                "title": task.title,
                "days_stale": days_stale,
                "last_updated": task.updated_at.isoformat() if task.updated_at else None,
                "staleness_reason": staleness_reason,
                "suggested_action": suggested_action,
                "quadrant": quadrant,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            })

        avg_staleness = total_staleness_days / len(tasks) if tasks else 0

        logger.info(f"detect_stale_tasks: user_id={user_id}, found {len(stale_tasks)} stale tasks")

        return {
            "stale_tasks": stale_tasks,
            "total_stale": len(stale_tasks),
            "insights": {
                "by_quadrant": {k: v for k, v in quadrant_counts.items() if v > 0},
                "average_staleness_days": round(avg_staleness, 1),
            },
            "summary": f"Found {len(stale_tasks)} task(s) not updated in {days_threshold}+ days"
            if stale_tasks
            else f"No stale tasks found (threshold: {days_threshold} days)",
        }

    except Exception as e:
        logger.error(f"detect_stale_tasks failed for user_id={user_id}: {e}", exc_info=True)
        return {
            "stale_tasks": [],
            "total_stale": 0,
            "summary": f"Error detecting stale tasks: {str(e)}",
            "error": str(e),
        }


@tool(parse_docstring=True)
async def breakdown_task(
    config: Annotated[RunnableConfig, InjectedToolArg()],
    task_id: Optional[int] = None,
    description: Optional[str] = None,
    max_subtasks: int = 5,
    create_subtasks: bool = False,
) -> Dict[str, Any]:
    """Break down a complex task into smaller, actionable subtasks.

    Use this tool when a user has a large task they need help decomposing,
    or when they ask "how should I approach this?" about a specific task.
    Provide either task_id (to load existing task) or description (for ad-hoc analysis).

    Args:
        task_id: ID of existing task to break down (mutually exclusive with description)
        description: Task description to analyze (mutually exclusive with task_id)
        max_subtasks: Maximum subtasks to generate (default: 5, range: 2-10)
        create_subtasks: If true, create subtasks as new tasks (default: False, just suggest)
    """
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    # Validate inputs
    if task_id is None and description is None:
        return {"error": "Either task_id or description must be provided"}

    if task_id is not None and description is not None:
        return {"error": "Provide either task_id or description, not both"}

    max_subtasks = max(2, min(max_subtasks, 10))

    try:
        parent_task_info = None
        task_title = ""
        task_description = ""

        # Load task if task_id provided
        if task_id is not None:
            if task_id <= 0:
                return {"error": "task_id must be greater than 0"}

            result = await db.execute(
                select(Task).where(Task.id == task_id, Task.user_id == user_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": f"Task {task_id} not found"}

            parent_task_info = {"id": task.id, "title": task.title}
            task_title = task.title
            task_description = task.description or task.title
        else:
            task_title = description[:80] if len(description) > 80 else description
            task_description = description

        # Load prompt template
        prompts_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompts_dir / "task_breakdown_v1.txt"

        if prompt_file.exists():
            prompt_template = prompt_file.read_text()
            prompt = prompt_template.format(
                task_title=task_title,
                task_description=task_description,
                max_subtasks=max_subtasks,
            )
        else:
            # Fallback inline prompt
            prompt = f"""Break down this task into {max_subtasks} actionable subtasks.

Task: {task_title}
Description: {task_description}

Return JSON only:
{{"subtasks": [{{"title": "...", "description": "...", "estimated_minutes": 30, "order": 1}}], "total_estimated_minutes": 120}}"""

        # Get LLM and generate breakdown
        from app.agent.llm_factory import get_llm_for_user

        llm = await get_llm_for_user(user_id=user_id, db=db)
        response = await llm.ainvoke(prompt)

        # Parse response
        response_text = response.content if hasattr(response, "content") else str(response)

        # Try to extract JSON from response
        try:
            # Find JSON in response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                breakdown_data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Generate simple fallback
            breakdown_data = {
                "subtasks": [
                    {"title": f"Step 1: Plan {task_title}", "description": "Define approach", "estimated_minutes": 30, "order": 1},
                    {"title": f"Step 2: Execute {task_title}", "description": "Do the work", "estimated_minutes": 60, "order": 2},
                    {"title": f"Step 3: Review {task_title}", "description": "Check results", "estimated_minutes": 15, "order": 3},
                ],
                "total_estimated_minutes": 105,
            }

        subtasks = breakdown_data.get("subtasks", [])
        total_minutes = breakdown_data.get("total_estimated_minutes", 0)

        # Create subtasks if requested
        created_task_ids = []
        if create_subtasks and subtasks:
            for subtask in subtasks[:max_subtasks]:
                new_task = Task(
                    user_id=user_id,
                    title=subtask.get("title", "Subtask")[:120],
                    description=subtask.get("description"),
                    time_estimate=subtask.get("estimated_minutes"),
                    status=TaskStatus.ACTIVE,
                    is_sorted=False,
                )
                db.add(new_task)
                await db.flush()
                created_task_ids.append(new_task.id)

            await db.commit()
            logger.info(f"breakdown_task: created {len(created_task_ids)} subtasks for user {user_id}")

        return {
            "parent_task": parent_task_info,
            "subtasks": subtasks[:max_subtasks],
            "total_estimated_minutes": total_minutes,
            "created_task_ids": created_task_ids,
            "summary": f"Broke down into {len(subtasks[:max_subtasks])} subtasks (~{total_minutes} mins total)"
            + (f", created {len(created_task_ids)} tasks" if created_task_ids else ""),
        }

    except Exception as e:
        logger.error(f"breakdown_task failed for user_id={user_id}: {e}", exc_info=True)
        return {"error": str(e), "summary": f"Error breaking down task: {str(e)}"}


@tool(parse_docstring=True)
async def draft_email(
    task_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg()],
    email_type: str = "status_update",
    recipient_context: Optional[str] = None,
    tone: str = "professional",
) -> Dict[str, Any]:
    """Generate an email draft based on a task's context.

    Use this tool when a user needs to send an email about a task - status updates,
    requests for help, escalations, or completion notifications. The draft uses
    task details and context for personalization.

    Args:
        task_id: ID of the task to draft email about (required, must be > 0)
        email_type: Type of email - "status_update", "request", "escalation", "completion" (default: "status_update")
        recipient_context: Optional context about recipient (e.g., "my manager", "the client team")
        tone: Email tone - "professional", "friendly", "formal", "urgent" (default: "professional")
    """
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    if task_id <= 0:
        return {"error": "task_id must be greater than 0"}

    # Validate email_type
    valid_types = ["status_update", "request", "escalation", "completion"]
    if email_type not in valid_types:
        email_type = "status_update"

    # Validate tone
    valid_tones = ["professional", "friendly", "formal", "urgent"]
    if tone not in valid_tones:
        tone = "professional"

    try:
        # Load task
        result = await db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return {"error": f"Task {task_id} not found"}

        # Build prompt
        prompts_dir = Path(__file__).parent.parent / "prompts"
        prompt_file = prompts_dir / "email_draft_v1.txt"

        quadrant = task.eisenhower_quadrant.value if task.eisenhower_quadrant else "Unassigned"
        status = task.status.value if task.status else "ACTIVE"
        due_date = task.due_date.strftime("%Y-%m-%d %H:%M") if task.due_date else "No deadline"

        if prompt_file.exists():
            prompt_template = prompt_file.read_text()
            prompt = prompt_template.format(
                task_title=task.title,
                task_description=task.description or "No description",
                task_status=status,
                due_date=due_date,
                quadrant=quadrant,
                email_type=email_type,
                recipient_context=recipient_context or "colleague",
                tone=tone,
            )
        else:
            # Fallback inline prompt
            prompt = f"""Draft a {tone} {email_type} email about this task:

Task: {task.title}
Description: {task.description or 'No description'}
Status: {status}
Due: {due_date}
Recipient: {recipient_context or 'colleague'}

Return JSON only:
{{"subject": "...", "body": "...", "suggested_ccs": []}}"""

        # Get LLM and generate email
        from app.agent.llm_factory import get_llm_for_user

        llm = await get_llm_for_user(user_id=user_id, db=db)
        response = await llm.ainvoke(prompt)

        response_text = response.content if hasattr(response, "content") else str(response)

        # Parse response
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                email_data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError:
            # Fallback
            email_data = {
                "subject": f"{email_type.replace('_', ' ').title()}: {task.title}",
                "body": f"Hi,\n\nI wanted to provide an update on: {task.title}\n\n{task.description or ''}\n\nBest regards",
                "suggested_ccs": [],
            }

        logger.info(f"draft_email: generated {email_type} email for task {task_id}")

        return {
            "task": {"id": task.id, "title": task.title},
            "email": {
                "subject": email_data.get("subject", ""),
                "body": email_data.get("body", ""),
                "suggested_ccs": email_data.get("suggested_ccs", []),
                "email_type": email_type,
                "tone": tone,
            },
            "summary": f"Drafted {email_type} email for '{task.title}'",
        }

    except Exception as e:
        logger.error(f"draft_email failed for user_id={user_id}: {e}", exc_info=True)
        return {"error": str(e), "summary": f"Error drafting email: {str(e)}"}


@tool(parse_docstring=True)
async def get_workload_analytics(
    config: Annotated[RunnableConfig, InjectedToolArg()],
    period: str = "this_week",
) -> Dict[str, Any]:
    """Get workload analytics and capacity insights for the user.

    Use this tool when the user asks about their workload, capacity, how busy
    they are, or whether they can take on more work. Provides detailed breakdown
    of scheduled work, available capacity, and risk assessment.

    Args:
        period: Time period to analyze - "today", "this_week", "this_month" (default: "this_week")
    """
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    # Validate period
    valid_periods = ["today", "this_week", "this_month"]
    if period not in valid_periods:
        period = "this_week"

    try:
        service = WellbeingService(db, user_id)
        result = await service.calculate_workload(period)

        logger.info(f"get_workload_analytics: user_id={user_id}, period={period}, risk={result.get('risk_level')}")

        return result

    except Exception as e:
        logger.error(f"get_workload_analytics failed for user_id={user_id}: {e}", exc_info=True)
        return {
            "error": str(e),
            "summary": f"Error calculating workload: {str(e)}",
        }


@tool
async def get_rest_recommendation(
    config: Annotated[RunnableConfig, InjectedToolArg()],
) -> Dict[str, Any]:
    """Check if the user needs rest based on work intensity and patterns. Use this when the user seems overwhelmed, mentions being tired, or asks if they should take a break."""
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    try:
        service = WellbeingService(db, user_id)
        result = await service.calculate_rest_recommendation()

        logger.info(
            f"get_rest_recommendation: user_id={user_id}, "
            f"needs_rest={result.get('needs_rest')}, urgency={result.get('urgency')}"
        )

        return result

    except Exception as e:
        logger.error(f"get_rest_recommendation failed for user_id={user_id}: {e}", exc_info=True)
        return {
            "error": str(e),
            "summary": f"Error calculating rest recommendation: {str(e)}",
        }


# -----------------------------------------------------------------------------
# Export all tools for discovery
__all__ = [
    # Core task tools
    "fetch_tasks",
    "fetch_task",
    "create_task",
    "update_task",
    "complete_task",
    "delete_task",
    "quick_analyze_task",
    # V1 MVP + Phase 2 tools
    "detect_stale_tasks",
    "breakdown_task",
    "draft_email",
    "get_workload_analytics",
    "get_rest_recommendation",
    # Helpers
    "task_to_payload",
]

