"""
Tool implementations for the agent runtime.

Each tool has a Pydantic input schema and returns a structured dict that can
be streamed to the frontend timeline.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator
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
# Input schemas
# -----------------------------------------------------------------------------


class FetchTasksInput(BaseModel):
    user_id: int = Field(..., gt=0)
    status: Optional[TaskStatus] = None
    quadrant: Optional[EisenhowerQuadrant] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class FetchTaskInput(BaseModel):
    user_id: int = Field(..., gt=0)
    task_id: int = Field(..., gt=0)


class CreateTaskInput(BaseModel):
    user_id: int = Field(..., gt=0)
    title: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Concise task title without quotes, max 120 chars",
    )
    description: Optional[str] = Field(
        None,
        description="Optional details that must differ from title. Provide meaningful context or leave None.",
    )
    due_date: Optional[datetime] = Field(None, description="ISO datetime string if task has a deadline")
    ticktick_priority: Optional[int] = Field(
        None, ge=0, le=5, description="Priority: 0 (none), 1 (low), 3 (medium), 5 (high)"
    )
    ticktick_tags: Optional[List[str]] = Field(default_factory=list, description="List of tag strings")
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    ticktick_project_id: Optional[str] = None

    @validator("title")
    def clean_title(cls, value: str) -> str:
        """Remove quotes, trim whitespace, enforce length limit."""
        cleaned = value.strip().strip('"').strip("'")
        if not cleaned:
            raise ValueError("title cannot be empty after cleaning")
        if len(cleaned) > 120:
            cleaned = cleaned[:117] + "..."
        return cleaned

    @validator("description")
    def prevent_duplicate_description(cls, value: Optional[str], values: dict) -> Optional[str]:
        """Ensure description differs from title and adds value."""
        if not value:
            return None

        cleaned_desc = value.strip()
        if not cleaned_desc:
            return None

        # Get the already-validated title from values
        title = values.get("title", "")

        # Reject if description exactly matches title
        if cleaned_desc == title:
            raise ValueError("description must differ from title - omit description if no additional context")

        # Reject if description is just title with minor changes
        if cleaned_desc.lower() == title.lower():
            return None

        # If description is very short (<10 chars), it likely doesn't add value
        if len(cleaned_desc) < 10:
            return None

        return cleaned_desc


class CompleteTaskInput(BaseModel):
    user_id: int = Field(..., gt=0)
    task_id: int = Field(..., gt=0)


class DeleteTaskInput(BaseModel):
    user_id: int = Field(..., gt=0)
    task_id: int = Field(..., gt=0)
    confirm: bool = Field(False, description="Must be true for destructive actions")
    soft_delete: bool = True


class QuickAnalyzeInput(BaseModel):
    user_id: int = Field(..., gt=0)
    title: Optional[str] = Field(None, max_length=500)
    description: str = Field(..., min_length=1)
    due_date: Optional[datetime] = None

    @validator("title", always=True)
    def set_default_title(cls, value: Optional[str], values: Dict[str, Any]):
        if value:
            return value
        # If no title, fall back to first 80 chars of description
        description = values.get("description", "")
        return (description[:77] + "...") if len(description) > 80 else description


# -----------------------------------------------------------------------------
# Tool implementations
# -----------------------------------------------------------------------------


async def fetch_tasks(payload: FetchTasksInput, db: AsyncSession) -> Dict[str, Any]:
    """Return a list of tasks scoped to the user."""
    query = select(Task).where(Task.user_id == payload.user_id)

    if payload.status:
        query = query.where(Task.status == payload.status)

    if payload.quadrant:
        query = query.where(
            (Task.manual_quadrant_override == payload.quadrant)
            | (
                Task.manual_quadrant_override.is_(None)
                & (Task.eisenhower_quadrant == payload.quadrant)
            )
        )

    query = query.order_by(Task.created_at.desc()).limit(payload.limit).offset(payload.offset)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return {
        "tasks": [task_to_payload(t) for t in tasks],
        "total": len(tasks),
        "summary": f"Found {len(tasks)} tasks",
    }


async def fetch_task(payload: FetchTaskInput, db: AsyncSession) -> Dict[str, Any]:
    """Return a single task if it belongs to the user."""
    result = await db.execute(
        select(Task).where(Task.id == payload.task_id, Task.user_id == payload.user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "Task not found"}

    return {"task": task_to_payload(task), "summary": f"Loaded task {task.id}"}


async def create_task(payload: CreateTaskInput, db: AsyncSession) -> Dict[str, Any]:
    """Create a task for the user."""
    task = Task(
        user_id=payload.user_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        ticktick_priority=payload.ticktick_priority or 0,
        ticktick_tags=payload.ticktick_tags or [],
        project_id=payload.project_id,
        project_name=payload.project_name,
        ticktick_project_id=payload.ticktick_project_id,
        status=TaskStatus.ACTIVE,
        is_sorted=False,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    logger.info("Agent created task %s for user %s", task.id, payload.user_id)

    return {
        "task": task_to_payload(task),
        "summary": f"Created task “{task.title}”",
    }


async def complete_task(payload: CompleteTaskInput, db: AsyncSession) -> Dict[str, Any]:
    """Mark a task as completed."""
    result = await db.execute(
        select(Task).where(Task.id == payload.task_id, Task.user_id == payload.user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "Task not found"}

    task.status = TaskStatus.COMPLETED
    task.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    return {
        "task": task_to_payload(task),
        "summary": f"Completed task “{task.title}”",
    }


async def delete_task(payload: DeleteTaskInput, db: AsyncSession) -> Dict[str, Any]:
    """Soft delete or hard delete a task. Confirmation must be handled upstream."""
    result = await db.execute(
        select(Task).where(Task.id == payload.task_id, Task.user_id == payload.user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        return {"error": "Task not found"}

    if payload.soft_delete:
        task.status = TaskStatus.DELETED
        task.updated_at = datetime.utcnow()
        await db.commit()
        summary = f"Soft-deleted task “{task.title}”"
    else:
        await db.delete(task)
        await db.commit()
        summary = f"Deleted task “{task.title}”"

    return {"summary": summary, "task_id": payload.task_id}


async def quick_analyze_task(payload: QuickAnalyzeInput, db: AsyncSession) -> Dict[str, Any]:
    """
    Lightweight analysis using the existing OllamaService.

    Falls back gracefully if the LLM is unavailable.
    """
    ollama = OllamaService()
    profile_context = None

    # Try to fetch profile context; ignore errors in agent path
    try:
        user_result = await db.execute(select(User).where(User.id == payload.user_id))
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

    analysis = await ollama.analyze_task(payload.description, profile_context=profile_context)

    return {
        "analysis": {
            "urgency": analysis.urgency,
            "importance": analysis.importance,
            "quadrant": analysis.quadrant,
            "reasoning": analysis.reasoning,
        },
        "suggested_priority": analysis.urgency if analysis.urgency else None,
        "title": payload.title,
        "summary": f"Analysis suggests {analysis.quadrant} (urgency {analysis.urgency}, importance {analysis.importance})",
    }


# Registry of tools with metadata for dispatcher
TOOL_REGISTRY = {
    "fetch_tasks": {
        "model": FetchTasksInput,
        "callable": fetch_tasks,
        "description": "List tasks for the user. Accepts status/quadrant filters.",
        "requires_confirmation": False,
    },
    "fetch_task": {
        "model": FetchTaskInput,
        "callable": fetch_task,
        "description": "Load a single task by id.",
        "requires_confirmation": False,
    },
    "create_task": {
        "model": CreateTaskInput,
        "callable": create_task,
        "description": "Create a new task with optional due date and tags.",
        "requires_confirmation": False,
        "examples": [
            {
                "title": "Review PR #456",
                "description": "Full code review focusing on security and performance",
                "ticktick_tags": ["code-review", "urgent"],
            },
            {
                "title": "Weekly team sync",
                "description": "Discuss sprint progress and blockers with engineering team",
                "due_date": "2025-12-15T10:00:00",
                "ticktick_priority": 3,
            },
            {
                "title": "Fix login bug",
                "description": None,  # No description if title is self-explanatory
                "ticktick_priority": 5,
                "ticktick_tags": ["bug"],
            },
        ],
        "common_mistakes": [
            "Setting description to same value as title",
            "Including quotes around title",
            "Creating vague titles like 'New task' or 'Do something'",
        ],
    },
    "complete_task": {
        "model": CompleteTaskInput,
        "callable": complete_task,
        "description": "Mark a task as completed.",
        "requires_confirmation": False,
    },
    "delete_task": {
        "model": DeleteTaskInput,
        "callable": delete_task,
        "description": "Delete a task (soft by default).",
        "requires_confirmation": False,  # confirmations disabled per current stance
    },
    "quick_analyze_task": {
        "model": QuickAnalyzeInput,
        "callable": quick_analyze_task,
        "description": "Run lightweight analysis on a description.",
        "requires_confirmation": False,
    },
}


__all__ = [
    "TOOL_REGISTRY",
    "fetch_tasks",
    "fetch_task",
    "create_task",
    "complete_task",
    "delete_task",
    "quick_analyze_task",
    "FetchTasksInput",
    "FetchTaskInput",
    "CreateTaskInput",
    "CompleteTaskInput",
    "DeleteTaskInput",
    "QuickAnalyzeInput",
]

