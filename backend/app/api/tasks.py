"""
Task CRUD API endpoints with LLM analysis integration.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.task import Task, TaskStatus, EisenhowerQuadrant
from app.services import OllamaService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# Pydantic schemas for request/response validation
class TaskCreate(BaseModel):
    """Request schema for creating a task."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    user_id: int = Field(..., gt=0)  # For now, passed in request (will be from auth later)

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Finish quarterly report",
                "description": "Complete Q4 financial report and submit to management",
                "due_date": "2025-12-15T17:00:00Z",
                "user_id": 1
            }
        }


class TaskUpdate(BaseModel):
    """Request schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[TaskStatus] = None
    manual_quadrant_override: Optional[EisenhowerQuadrant] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated task title",
                "status": "completed",
                "manual_quadrant_override": "Q1"
            }
        }


class TaskResponse(BaseModel):
    """Response schema for task data."""
    id: int
    user_id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    due_date: Optional[datetime]
    urgency_score: Optional[float]
    importance_score: Optional[float]
    effort_hours: Optional[float]
    eisenhower_quadrant: Optional[EisenhowerQuadrant]
    analysis_reasoning: Optional[str]
    manual_quadrant_override: Optional[EisenhowerQuadrant]
    created_at: datetime
    updated_at: datetime
    analyzed_at: Optional[datetime]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "title": "Finish quarterly report",
                "description": "Complete Q4 financial report",
                "status": "active",
                "due_date": "2025-12-15T17:00:00Z",
                "urgency_score": 8.0,
                "importance_score": 7.0,
                "effort_hours": None,
                "eisenhower_quadrant": "Q1",
                "analysis_reasoning": "High urgency due to deadline, important for business goals",
                "manual_quadrant_override": None,
                "created_at": "2025-12-10T10:00:00Z",
                "updated_at": "2025-12-10T10:00:00Z",
                "analyzed_at": "2025-12-10T10:00:05Z"
            }
        }


class TaskListResponse(BaseModel):
    """Response schema for list of tasks."""
    tasks: List[TaskResponse]
    total: int


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new task with automatic LLM analysis.

    The task description will be analyzed by the LLM to determine:
    - Urgency score (1-10)
    - Importance score (1-10)
    - Eisenhower quadrant (Q1/Q2/Q3/Q4)
    - Analysis reasoning
    """
    # Create task with basic info
    new_task = Task(
        user_id=task_data.user_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        status=TaskStatus.ACTIVE
    )

    # Perform LLM analysis if description is provided
    if task_data.description and task_data.description.strip():
        try:
            ollama = OllamaService()

            # Check if Ollama is available
            if await ollama.health_check():
                analysis = await ollama.analyze_task(task_data.description)

                # Update task with analysis results
                new_task.urgency_score = float(analysis.urgency)
                new_task.importance_score = float(analysis.importance)
                new_task.eisenhower_quadrant = EisenhowerQuadrant(analysis.quadrant)
                new_task.analysis_reasoning = analysis.reasoning
                new_task.analyzed_at = datetime.utcnow()
            else:
                # Ollama not available - task will be created without analysis
                print("[WARN] Ollama not available, task created without analysis")
        except Exception as e:
            # Log error but don't fail task creation
            print(f"[ERROR] LLM analysis failed: {str(e)}")

    # Save to database
    db.add(new_task)
    await db.flush()
    await db.refresh(new_task)

    return new_task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    user_id: int = Query(..., gt=0, description="User ID to filter tasks"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    quadrant: Optional[EisenhowerQuadrant] = Query(None, description="Filter by Eisenhower quadrant"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    db: AsyncSession = Depends(get_db)
):
    """
    List tasks with optional filtering by status and quadrant.

    Query parameters:
    - user_id: Required - filter tasks by user
    - status: Optional - filter by task status (active, completed, deleted)
    - quadrant: Optional - filter by Eisenhower quadrant (Q1, Q2, Q3, Q4)
    - limit: Maximum number of tasks to return (default 100, max 500)
    - offset: Number of tasks to skip for pagination (default 0)
    """
    # Build query with filters
    query = select(Task).where(Task.user_id == user_id)

    if status:
        query = query.where(Task.status == status)

    if quadrant:
        # Check both LLM quadrant and manual override
        query = query.where(
            (Task.eisenhower_quadrant == quadrant) |
            (Task.manual_quadrant_override == quadrant)
        )

    # Order by created_at descending (newest first)
    query = query.order_by(Task.created_at.desc())

    # Count total before pagination
    count_query = select(Task.id).where(Task.user_id == user_id)
    if status:
        count_query = count_query.where(Task.status == status)
    if quadrant:
        count_query = count_query.where(
            (Task.eisenhower_quadrant == quadrant) |
            (Task.manual_quadrant_override == quadrant)
        )

    result_count = await db.execute(count_query)
    total = len(result_count.all())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    tasks = result.scalars().all()

    return TaskListResponse(tasks=tasks, total=total)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single task by ID.

    Returns 404 if task not found.
    """
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a task.

    Only fields provided in the request will be updated.
    Returns 404 if task not found.
    """
    # Fetch existing task
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Update fields that are provided
    update_data = task_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    # Update timestamp
    task.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(task)

    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    soft_delete: bool = Query(True, description="If true, mark as deleted. If false, permanently delete."),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a task.

    By default performs soft delete (marks status as deleted).
    Use soft_delete=false for permanent deletion.

    Returns 204 No Content on success, 404 if task not found.
    """
    # Fetch existing task
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if soft_delete:
        # Soft delete - mark as deleted
        task.status = TaskStatus.DELETED
        task.updated_at = datetime.utcnow()
        await db.flush()
    else:
        # Hard delete - remove from database
        await db.delete(task)

    return None
