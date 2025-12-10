"""
Task CRUD API endpoints with LLM analysis integration.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.task import Task, TaskStatus, EisenhowerQuadrant
from app.models.user import User
from app.models.profile import Profile
from app.services import OllamaService
from app.services.ticktick import ticktick_service
from app.services.prompt_utils import build_profile_context

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


class QuadrantUpdate(BaseModel):
    """Request schema for manual quadrant overrides."""

    manual_quadrant: Optional[EisenhowerQuadrant] = Field(
        None, description="Manual quadrant override (use reset_to_ai to clear)"
    )
    reason: Optional[str] = Field(None, max_length=500, description="Reason for override")
    source: Optional[str] = Field(None, max_length=255, description="Who/what set the override")
    reset_to_ai: bool = Field(False, description="Clear manual override and revert to AI suggestion")
    reanalyze: bool = Field(False, description="Re-run LLM analysis when resetting to AI")

    class Config:
        json_schema_extra = {
            "example": {
                "manual_quadrant": "Q2",
                "reason": "Moved in matrix view",
                "source": "user",
                "reset_to_ai": False,
                "reanalyze": False,
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
    effective_quadrant: Optional[EisenhowerQuadrant]
    analysis_reasoning: Optional[str]
    manual_quadrant_override: Optional[EisenhowerQuadrant]
    manual_override_reason: Optional[str]
    manual_override_source: Optional[str]
    manual_override_at: Optional[datetime]
    manual_order: Optional[int]
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
                "effective_quadrant": "Q1",
                "analysis_reasoning": "High urgency due to deadline, important for business goals",
                "manual_override_reason": None,
                "manual_override_source": None,
                "manual_override_at": None,
                "manual_quadrant_override": None,
                "manual_order": 1,
                "created_at": "2025-12-10T10:00:00Z",
                "updated_at": "2025-12-10T10:00:00Z",
                "analyzed_at": "2025-12-10T10:00:05Z"
            }
        }


class TaskListResponse(BaseModel):
    """Response schema for list of tasks."""
    tasks: List[TaskResponse]
    total: int


async def _get_profile_context(user_id: int, db: AsyncSession) -> Optional[str]:
    """Return a compact, bulletized profile string for the given user."""
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    profile = result.scalar_one_or_none()
    return build_profile_context(profile)


def _effective_quadrant_expression(target: EisenhowerQuadrant):
    """SQL expression matching effective quadrant (manual override wins)."""
    return or_(
        Task.manual_quadrant_override == target,
        and_(
            Task.manual_quadrant_override.is_(None),
            Task.eisenhower_quadrant == target
        )
    )


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
                profile_context = await _get_profile_context(task_data.user_id, db)
                analysis = await ollama.analyze_task(task_data.description, profile_context=profile_context)

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
            _effective_quadrant_expression(quadrant)
        )

    # Order by created_at descending (newest first)
    query = query.order_by(
        Task.manual_order.asc().nullslast(),
        Task.created_at.desc()
    )

    # Count total before pagination
    count_query = select(Task.id).where(Task.user_id == user_id)
    if status:
        count_query = count_query.where(Task.status == status)
    if quadrant:
        count_query = count_query.where(
            _effective_quadrant_expression(quadrant)
        )

    result_count = await db.execute(count_query)
    total = len(result_count.all())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    tasks = result.scalars().all()

    return TaskListResponse(tasks=tasks, total=total)


class ReorderRequest(BaseModel):
    """Payload for reordering tasks within a quadrant."""

    user_id: int = Field(..., gt=0)
    quadrant: EisenhowerQuadrant
    task_ids: List[int] = Field(..., min_length=1, description="Ordered task IDs for this quadrant")


@router.post("/reorder", response_model=TaskListResponse)
async def reorder_tasks(
    payload: ReorderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reorder tasks within a quadrant. Manual order is stored server-side.
    - task_ids should represent the exact desired order for that quadrant.
    - Only tasks matching the effective quadrant are updated.
    """
    # Fetch tasks to ensure they belong to user and quadrant
    tasks_query = select(Task).where(
        Task.user_id == payload.user_id,
        Task.id.in_(payload.task_ids),
        _effective_quadrant_expression(payload.quadrant),
    )
    result = await db.execute(tasks_query)
    tasks = result.scalars().all()

    if len(tasks) != len(payload.task_ids):
        raise HTTPException(status_code=400, detail="Some tasks not found in that quadrant for this user")

    order_map = {task_id: index + 1 for index, task_id in enumerate(payload.task_ids)}

    for task in tasks:
        task.manual_order = order_map.get(task.id, task.manual_order)
        task.updated_at = datetime.utcnow()

    await db.flush()
    await db.commit()

    # Return the ordered tasks for the quadrant
    ordered_tasks = sorted(tasks, key=lambda t: order_map.get(t.id, 0))
    return TaskListResponse(tasks=ordered_tasks, total=len(ordered_tasks))


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


@router.patch("/{task_id}/quadrant", response_model=TaskResponse)
async def update_task_quadrant(
    task_id: int,
    quadrant_update: QuadrantUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Set or clear a manual quadrant override.

    - Provide `manual_quadrant` to override the LLM suggestion.
    - Provide `reset_to_ai=true` to clear the override. Optionally set `reanalyze=true`
      to refresh AI analysis using the current description.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if quadrant_update.reset_to_ai:
        task.manual_quadrant_override = None
        task.manual_override_reason = None
        task.manual_override_source = None
        task.manual_override_at = None

        if quadrant_update.reanalyze and task.description:
            ollama = OllamaService()
            if await ollama.health_check():
                profile_context = await _get_profile_context(task.user_id, db)
                try:
                    analysis = await ollama.analyze_task(
                        task.description,
                        profile_context=profile_context,
                    )
                    task.urgency_score = float(analysis.urgency)
                    task.importance_score = float(analysis.importance)
                    task.eisenhower_quadrant = EisenhowerQuadrant(analysis.quadrant)
                    task.analysis_reasoning = analysis.reasoning
                    task.analyzed_at = datetime.utcnow()
                except Exception as e:
                    print(f"[ERROR] Re-analysis failed for task {task_id}: {str(e)}")
    else:
        if not quadrant_update.manual_quadrant:
            raise HTTPException(
                status_code=400,
                detail="manual_quadrant is required when reset_to_ai is false"
            )
        task.manual_quadrant_override = quadrant_update.manual_quadrant
        task.manual_override_reason = quadrant_update.reason or "Manual override"
        task.manual_override_source = quadrant_update.source or "user"
        task.manual_override_at = datetime.utcnow()

        # First flush the quadrant change
        await db.flush()

        # Now calculate max_order for the NEW quadrant (excluding this task)
        max_order_query = select(func.max(Task.manual_order)).where(
            Task.user_id == task.user_id,
            Task.id != task.id,  # Exclude current task
            _effective_quadrant_expression(quadrant_update.manual_quadrant),
        )
        max_order_result = await db.execute(max_order_query)
        max_order = max_order_result.scalar()
        task.manual_order = (max_order or 0) + 1

    task.updated_at = datetime.utcnow()

    await db.flush()
    await db.commit()
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


class SyncResponse(BaseModel):
    """Response schema for sync operation."""
    synced_count: int
    analyzed_count: int
    failed_count: int
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "synced_count": 15,
                "analyzed_count": 15,
                "failed_count": 0,
                "message": "Successfully synced 15 tasks from TickTick"
            }
        }


@router.post("/sync", response_model=SyncResponse)
async def sync_ticktick_tasks(
    user_id: int = Query(1, description="User ID to sync tasks for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync tasks from TickTick for a user.

    This endpoint:
    1. Fetches user's TickTick access token from database
    2. Calls TickTick API to get all tasks
    3. For each task, performs LLM analysis
    4. Saves tasks to database with analysis results

    Returns count of synced tasks and analysis results.

    Raises:
        HTTPException: If user not found or TickTick not connected
    """
    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.ticktick_access_token:
        raise HTTPException(
            status_code=400,
            detail="TickTick not connected. Please connect your TickTick account first."
        )

    # Initialize counters
    synced_count = 0
    analyzed_count = 0
    failed_count = 0

    try:
        # Fetch tasks from TickTick
        ticktick_tasks = await ticktick_service.get_tasks(user.ticktick_access_token)

        # Initialize LLM service
        ollama = OllamaService()
        ollama_available = await ollama.health_check()
        profile_context = await _get_profile_context(user_id, db)

        # Process each task
        for tt_task in ticktick_tasks:
            try:
                # Skip completed tasks (status=2 in TickTick)
                if tt_task.get("status") == 2:
                    continue

                # Check if task already exists in database
                task_id = tt_task.get("id")
                existing_task_result = await db.execute(
                    select(Task).where(
                        Task.ticktick_task_id == task_id,
                        Task.user_id == user_id
                    )
                )
                existing_task = existing_task_result.scalar_one_or_none()

                # Prepare task description for analysis
                task_description = tt_task.get("content") or tt_task.get("title", "")

                # Perform LLM analysis if Ollama is available and task has description
                analysis_result = None
                if ollama_available and task_description.strip():
                    try:
                        analysis_result = await ollama.analyze_task(
                            task_description,
                            profile_context=profile_context
                        )
                        analyzed_count += 1
                    except Exception as e:
                        print(f"[ERROR] Analysis failed for task {task_id}: {str(e)}")

                if existing_task:
                    # Update existing task
                    existing_task.title = tt_task.get("title", existing_task.title)
                    existing_task.description = tt_task.get("content")
                    existing_task.ticktick_project_id = tt_task.get("project_id")

                    # Update analysis if available
                    if analysis_result:
                        existing_task.urgency_score = float(analysis_result.urgency)
                        existing_task.importance_score = float(analysis_result.importance)
                        existing_task.eisenhower_quadrant = EisenhowerQuadrant(analysis_result.quadrant)
                        existing_task.analysis_reasoning = analysis_result.reasoning
                        existing_task.analyzed_at = datetime.utcnow()

                    existing_task.updated_at = datetime.utcnow()

                else:
                    # Create new task
                    new_task = Task(
                        user_id=user_id,
                        title=tt_task.get("title", "Untitled Task"),
                        description=tt_task.get("content"),
                        ticktick_task_id=task_id,
                        ticktick_project_id=tt_task.get("project_id"),
                        status=TaskStatus.ACTIVE,
                    )

                    # Add analysis results if available
                    if analysis_result:
                        new_task.urgency_score = float(analysis_result.urgency)
                        new_task.importance_score = float(analysis_result.importance)
                        new_task.eisenhower_quadrant = EisenhowerQuadrant(analysis_result.quadrant)
                        new_task.analysis_reasoning = analysis_result.reasoning
                        new_task.analyzed_at = datetime.utcnow()

                    db.add(new_task)

                synced_count += 1

            except Exception as e:
                print(f"[ERROR] Failed to sync task {tt_task.get('id', 'unknown')}: {str(e)}")
                failed_count += 1
                continue

        # Commit all changes
        await db.commit()

        # Prepare response message
        if not ollama_available:
            message = f"Synced {synced_count} tasks from TickTick (LLM analysis unavailable)"
        else:
            message = f"Successfully synced {synced_count} tasks from TickTick ({analyzed_count} analyzed)"

        return SyncResponse(
            synced_count=synced_count,
            analyzed_count=analyzed_count,
            failed_count=failed_count,
            message=message
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync TickTick tasks: {str(e)}"
        )
