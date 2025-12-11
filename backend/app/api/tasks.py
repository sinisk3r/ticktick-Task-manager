"""
Task CRUD API endpoints with LLM analysis integration.
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, delete
from pydantic import BaseModel, Field
import logging

# Initialize logger
logger = logging.getLogger(__name__)

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
    Create a new task (NO automatic LLM analysis).

    Tasks are created as unsorted (is_sorted=False) by default.
    They will appear in the Unsorted list until manually analyzed.

    NOTE: LLM analysis is NOT performed automatically.
    Users must:
    1. Use "Get AI Suggestions" in QuickAddModal before creating, OR
    2. Click "Analyze" button on task after creation
    """
    import logging
    logger = logging.getLogger(__name__)

    # Create task with basic info (unsorted, no analysis)
    new_task = Task(
        user_id=task_data.user_id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        status=TaskStatus.ACTIVE,
        is_sorted=False  # Start in unsorted list
    )

    # NOTE: NO automatic LLM analysis.
    # Task is created as-is without urgency/importance scores.
    # User must explicitly request analysis via:
    # - "Get AI Suggestions" button in QuickAddModal (before creating)
    # - "Analyze" button on existing task (after creating)

    # Save to database
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # NOTE: Tasks are NOT automatically synced to TickTick on creation.
    # Users must explicitly click the "Sync with TickTick" button to push changes.
    # Future enhancement: Add auto-sync setting in user preferences.

    logger.info(f"Created task {new_task.id} (local only - not synced to TickTick)")

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


# ============================================================================
# UNSORTED TASKS ENDPOINTS
# ============================================================================


@router.get("/unsorted", response_model=TaskListResponse)
async def get_unsorted_tasks(
    user_id: int = Query(..., gt=0, description="User ID to filter tasks"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all unsorted tasks for current user.

    Unsorted tasks are tasks that have not yet been assigned to a quadrant
    in the Eisenhower Matrix. These tasks are in a staging area waiting
    to be manually sorted or analyzed by the AI.
    """
    # Query unsorted tasks (is_sorted = False)
    stmt = select(Task).where(
        Task.user_id == user_id,
        Task.is_sorted == False,
        Task.status != TaskStatus.DELETED
    ).order_by(Task.created_at.desc())

    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return TaskListResponse(tasks=tasks, total=len(tasks))


class TaskSortRequest(BaseModel):
    """Request schema for sorting a task."""
    quadrant: EisenhowerQuadrant = Field(..., description="Target quadrant for the task")


@router.post("/{task_id}/sort", response_model=TaskResponse)
async def sort_task(
    task_id: int,
    sort_data: TaskSortRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually sort a task into a quadrant.

    This endpoint:
    1. Assigns the task to the specified quadrant
    2. Marks the task as sorted (is_sorted = True)
    3. Sets manual_quadrant_override to preserve user's choice
    4. Updates the task in the database

    Note: This does NOT sync to TickTick as TickTick doesn't have quadrant concept.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Fetch task
    stmt = select(Task).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Sort the task
    task.eisenhower_quadrant = sort_data.quadrant
    task.is_sorted = True
    task.manual_quadrant_override = sort_data.quadrant
    task.manual_override_reason = "Manually sorted from unsorted list"
    task.manual_override_source = "user"
    task.manual_override_at = datetime.utcnow()
    task.last_modified_at = datetime.utcnow()
    task.sync_version += 1

    # Set manual_order to end of quadrant
    max_order_query = select(func.max(Task.manual_order)).where(
        Task.user_id == task.user_id,
        Task.id != task.id,
        _effective_quadrant_expression(sort_data.quadrant),
    )
    max_order_result = await db.execute(max_order_query)
    max_order = max_order_result.scalar()
    task.manual_order = (max_order or 0) + 1

    await db.commit()
    await db.refresh(task)

    logger.info(f"Task {task_id} sorted to {sort_data.quadrant}")

    return task


class BatchSortRequest(BaseModel):
    """Request schema for batch sorting tasks."""
    task_ids: List[int] = Field(..., min_length=1, description="List of task IDs to sort")
    quadrant: EisenhowerQuadrant = Field(..., description="Target quadrant for all tasks")


@router.post("/sort/batch", response_model=dict)
async def batch_sort_tasks(
    batch_data: BatchSortRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Batch sort multiple tasks into a quadrant.

    Useful for sorting multiple unsorted tasks at once.
    All tasks will be assigned to the same quadrant.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Fetch tasks
    stmt = select(Task).where(Task.id.in_(batch_data.task_ids))
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found")

    # Get user_id from first task (assuming all tasks belong to same user)
    user_id = tasks[0].user_id

    # Get current max order for the quadrant
    max_order_query = select(func.max(Task.manual_order)).where(
        Task.user_id == user_id,
        Task.id.notin_(batch_data.task_ids),
        _effective_quadrant_expression(batch_data.quadrant),
    )
    max_order_result = await db.execute(max_order_query)
    max_order = max_order_result.scalar() or 0

    # Sort all tasks
    for idx, task in enumerate(tasks):
        task.eisenhower_quadrant = batch_data.quadrant
        task.is_sorted = True
        task.manual_quadrant_override = batch_data.quadrant
        task.manual_override_reason = "Batch sorted from unsorted list"
        task.manual_override_source = "user"
        task.manual_override_at = datetime.utcnow()
        task.last_modified_at = datetime.utcnow()
        task.sync_version += 1
        task.manual_order = max_order + idx + 1

    await db.commit()

    logger.info(f"Batch sorted {len(tasks)} tasks to {batch_data.quadrant}")

    return {"sorted_count": len(tasks), "quadrant": batch_data.quadrant}


# ============================================================================
# SINGLE TASK OPERATIONS
# ============================================================================


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
@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a task (local changes only - does NOT auto-sync to TickTick).

    Only fields provided in the request will be updated.
    Returns 404 if task not found.

    NOTE: Changes are saved locally only. Users must click "Sync with TickTick"
    to push changes to the cloud. Future enhancement: Add auto-sync setting.
    """
    from app.services.ticktick import TickTickService
    import logging
    logger = logging.getLogger(__name__)

    # Fetch existing task
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Track what fields changed for sync
    changes = {}
    update_data = task_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(task, field):
            old_value = getattr(task, field)
            if old_value != value:
                changes[field] = value
                setattr(task, field, value)

    # Update sync metadata
    task.last_modified_at = datetime.utcnow()
    task.sync_version = task.sync_version + 1 if task.sync_version else 1

    # Update timestamp
    task.updated_at = datetime.utcnow()

    # Commit local changes
    await db.commit()
    await db.refresh(task)

    # NOTE: Changes are NOT automatically synced to TickTick.
    # Users must explicitly click "Sync with TickTick" button.
    # This gives users full control over when cloud sync happens.

    if changes:
        logger.info(f"Updated task {task_id} locally (not synced): {list(changes.keys())}")

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
        task.is_sorted = True  # Mark as sorted when quadrant is assigned

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
    Delete a task and sync deletion to TickTick.

    By default performs soft delete (marks status as deleted).
    Use soft_delete=false for permanent deletion.

    Returns 204 No Content on success, 404 if task not found.
    """
    from app.services.ticktick import TickTickService
    import logging
    logger = logging.getLogger(__name__)

    # Fetch existing task
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Store TickTick info before deletion
    ticktick_task_id = task.ticktick_task_id
    ticktick_project_id = task.ticktick_project_id
    user_id = task.user_id

    if soft_delete:
        # Soft delete - mark as deleted
        task.status = TaskStatus.DELETED
        task.updated_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Soft deleted task {task_id} locally (not synced to TickTick)")
    else:
        # Hard delete - remove from database
        await db.delete(task)
        await db.commit()
        logger.info(f"Hard deleted task {task_id} locally (not synced to TickTick)")

    # NOTE: Deletions are NOT automatically synced to TickTick.
    # Users must click "Sync with TickTick" to push deletions.
    # This prevents accidental permanent data loss in the cloud.

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
    Sync tasks and projects from TickTick for a user (NO automatic LLM analysis).

    This endpoint:
    1. Fetches user's TickTick access token from database
    2. Syncs projects from TickTick to local database FIRST
    3. Calls TickTick API to get all tasks with comprehensive metadata
    4. Links tasks to projects via project_id
    5. Saves tasks to database WITHOUT running LLM analysis
    6. Users must explicitly click "Analyze" on tasks to run LLM

    Returns count of synced tasks and projects.

    NOTE: LLM analysis is NOT performed during sync. Users have full control
    over which tasks to analyze via the "Analyze" button in the UI.

    Raises:
        HTTPException: If user not found or TickTick not connected
    """
    import logging
    logger = logging.getLogger(__name__)

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
    failed_count = 0

    # STEP 1: Sync projects first
    from app.services.ticktick import TickTickService
    ticktick_service_instance = TickTickService(user=user)

    try:
        projects = await ticktick_service_instance.sync_projects(db)
        logger.info(f"Synced {len(projects)} projects for user {user.id}")
    except Exception as e:
        logger.error(f"Project sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Project sync failed: {str(e)}")

    # Create a mapping of ticktick_project_id → database project_id
    project_map = {
        proj.ticktick_project_id: proj.id
        for proj in projects
    }

    try:
        # STEP 2: Fetch tasks from TickTick with full metadata
        ticktick_tasks = await ticktick_service_instance.get_tasks(user.ticktick_access_token)

        # NOTE: LLM analysis is NOT performed during sync.
        # Users must explicitly click "Analyze" on tasks they want analyzed.

        # Process each task
        for task_data in ticktick_tasks:
            try:
                # Skip completed tasks
                if task_data.get("status") == "completed":
                    continue

                # Link task to project via database project_id
                ticktick_proj_id = task_data.get("ticktick_project_id")
                task_data["project_id"] = project_map.get(ticktick_proj_id)

                # Set sync metadata
                task_data["last_synced_at"] = datetime.utcnow()
                task_data["is_sorted"] = False  # New tasks start unsorted

                # Check if task already exists in database
                task_id = task_data.get("ticktick_task_id")
                existing_task_result = await db.execute(
                    select(Task).where(
                        Task.ticktick_task_id == task_id,
                        Task.user_id == user_id
                    )
                )
                existing_task = existing_task_result.scalar_one_or_none()

                if existing_task:
                    # Update existing task with new data from TickTick
                    for key, value in task_data.items():
                        if hasattr(existing_task, key) and key not in ["id", "user_id", "created_at"]:
                            setattr(existing_task, key, value)

                    # NOTE: Preserve existing analysis (don't overwrite)
                    # Users can re-analyze manually if they want fresh analysis

                    existing_task.sync_version += 1
                    existing_task.updated_at = datetime.utcnow()

                else:
                    # Create new task (unsorted, no analysis)
                    new_task = Task(
                        user_id=user_id,
                        **task_data
                    )

                    # NOTE: Task created WITHOUT analysis.
                    # Will appear in "Unsorted" list.
                    # User must click "Analyze" to get AI suggestions.

                    db.add(new_task)

                synced_count += 1

            except Exception as e:
                logger.error(f"Failed to sync task {task_data.get('ticktick_task_id', 'unknown')}: {str(e)}")
                failed_count += 1
                continue

        # Commit all changes
        await db.commit()

        # Prepare response message
        project_count = len(projects)
        message = f"Successfully synced {project_count} projects and {synced_count} tasks from TickTick (no auto-analysis)"

        return SyncResponse(
            synced_count=synced_count,
            analyzed_count=0,  # Always 0 - no auto-analysis
            failed_count=failed_count,
            message=message
        )

    except Exception as e:
        logger.error(f"Failed to sync TickTick tasks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync TickTick tasks: {str(e)}"
        )


# ============================================================================
# SUGGESTION API ENDPOINTS (Phase 5)
# ============================================================================


@router.post("/{task_id}/analyze")
async def analyze_task_suggestions(
    task_id: int,
    user_id: int = Query(..., gt=0, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    User-initiated LLM analysis for a task.
    Generates suggestions and stores in TaskSuggestion model.

    This endpoint:
    1. Fetches task details and context (project, related tasks, user workload)
    2. Calls LLM service to generate suggestions
    3. Stores suggestions in TaskSuggestion table
    4. Returns analysis and suggestions for user review
    """
    from app.services.llm_ollama import OllamaService
    from app.services.workload_calculator import (
        calculate_user_workload,
        get_project_context,
        get_related_tasks
    )
    from app.models.task_suggestion import TaskSuggestion, SuggestionStatus

    # Get task
    stmt = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Gather context
    workload = await calculate_user_workload(user_id, db)

    project_context = None
    if task.project_id:
        project_context = await get_project_context(task.project_id, db)

    related_tasks = []
    if task.project_id:
        related_tasks = await get_related_tasks(task_id, task.project_id, db)

    # Call LLM
    llm_service = OllamaService()

    task_data = {
        "title": task.title,
        "description": task.description,
        "due_date": task.due_date,
        "ticktick_priority": task.ticktick_priority,
        "project_name": task.project_name,
        "ticktick_tags": task.ticktick_tags or [],
        "start_date": task.start_date
    }

    try:
        suggestion_result = await llm_service.generate_suggestions(
            task_data=task_data,
            project_context=project_context,
            related_tasks=related_tasks,
            user_workload=workload
        )
    except Exception as e:
        logger.error(f"LLM analysis failed for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Delete old pending suggestions for this task
    delete_stmt = delete(TaskSuggestion).where(
        TaskSuggestion.task_id == task_id,
        TaskSuggestion.status == SuggestionStatus.PENDING
    )
    await db.execute(delete_stmt)

    # Store new suggestions
    created_suggestions = []
    for suggestion in suggestion_result.get("suggestions", []):
        new_suggestion = TaskSuggestion(
            task_id=task_id,
            suggestion_type=suggestion["type"],
            current_value=suggestion.get("current"),
            suggested_value=suggestion["suggested"],
            reason=suggestion["reason"],
            confidence=suggestion["confidence"],
            status=SuggestionStatus.PENDING
        )
        db.add(new_suggestion)
        created_suggestions.append(new_suggestion)

    # Update task's analyzed_at timestamp
    task.analyzed_at = datetime.utcnow()

    await db.commit()

    # Refresh to get IDs
    for suggestion in created_suggestions:
        await db.refresh(suggestion)

    return {
        "task_id": task_id,
        "analysis": suggestion_result.get("analysis", {}),
        "suggestions": [
            {
                "id": s.id,
                "type": s.suggestion_type,
                "current": s.current_value,
                "suggested": s.suggested_value,
                "reason": s.reason,
                "confidence": s.confidence
            }
            for s in created_suggestions
        ]
    }


@router.post("/analyze/batch")
async def analyze_tasks_batch(
    task_ids: List[int] = Body(...),
    user_id: int = Query(..., gt=0, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze multiple tasks in batch.

    Each task is analyzed independently. Errors for individual tasks don't
    stop the batch - failed tasks are reported in the results.
    """
    results = []

    for task_id in task_ids:
        try:
            # Call the single-task endpoint directly
            result = await analyze_task_suggestions(task_id, user_id, db)
            results.append({"task_id": task_id, "status": "success", "data": result})
        except HTTPException as e:
            logger.error(f"Batch analysis failed for task {task_id}: {e.detail}")
            results.append({"task_id": task_id, "status": "error", "error": e.detail})
        except Exception as e:
            logger.error(f"Batch analysis failed for task {task_id}: {e}")
            results.append({"task_id": task_id, "status": "error", "error": str(e)})

    return {
        "total": len(task_ids),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "results": results
    }


@router.get("/{task_id}/suggestions")
async def get_task_suggestions(
    task_id: int,
    user_id: int = Query(..., gt=0, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get pending suggestions for a task.

    Returns all pending (not yet approved/rejected) suggestions generated
    by the LLM analysis for this task.
    """
    from app.models.task_suggestion import TaskSuggestion, SuggestionStatus

    # Verify task ownership
    stmt = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get pending suggestions
    stmt = select(TaskSuggestion).where(
        TaskSuggestion.task_id == task_id,
        TaskSuggestion.status == SuggestionStatus.PENDING
    ).order_by(TaskSuggestion.created_at.desc())

    result = await db.execute(stmt)
    suggestions = result.scalars().all()

    return {
        "task_id": task_id,
        "suggestions": [
            {
                "id": s.id,
                "type": s.suggestion_type,
                "current": s.current_value,
                "suggested": s.suggested_value,
                "reason": s.reason,
                "confidence": s.confidence,
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in suggestions
        ]
    }


@router.post("/{task_id}/suggestions/approve")
async def approve_suggestions(
    task_id: int,
    suggestion_types: List[str] = Body(..., embed=True),
    user_id: int = Query(..., gt=0, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve specific suggestions (or all).

    Accepts a list of suggestion types to approve (e.g., ["priority", "tags"])
    or ["all"] to approve all pending suggestions.

    This endpoint:
    1. Fetches pending suggestions of the specified types
    2. Applies the suggested values to the task
    3. Marks suggestions as approved
    4. Syncs changes to TickTick if the task is connected
    """
    from app.models.task_suggestion import TaskSuggestion, SuggestionStatus
    from app.services.ticktick import TickTickService

    # Get task
    stmt = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get pending suggestions
    stmt = select(TaskSuggestion).where(
        TaskSuggestion.task_id == task_id,
        TaskSuggestion.status == SuggestionStatus.PENDING
    )

    if "all" not in suggestion_types:
        stmt = stmt.where(TaskSuggestion.suggestion_type.in_(suggestion_types))

    result = await db.execute(stmt)
    suggestions = result.scalars().all()

    if not suggestions:
        return {"message": "No pending suggestions to approve"}

    # Apply suggestions to task
    changes = {}

    for suggestion in suggestions:
        if suggestion.suggestion_type == "priority":
            task.ticktick_priority = suggestion.suggested_value
            changes["ticktick_priority"] = suggestion.suggested_value

        elif suggestion.suggestion_type == "tags":
            task.ticktick_tags = suggestion.suggested_value
            changes["ticktick_tags"] = suggestion.suggested_value

        elif suggestion.suggestion_type == "quadrant":
            task.eisenhower_quadrant = EisenhowerQuadrant(suggestion.suggested_value)
            task.is_sorted = True  # Move out of unsorted list
            changes["eisenhower_quadrant"] = suggestion.suggested_value

        elif suggestion.suggestion_type == "start_date":
            if suggestion.suggested_value:
                task.start_date = datetime.fromisoformat(suggestion.suggested_value)
            else:
                task.start_date = None
            changes["start_date"] = task.start_date

        # Mark suggestion as approved
        suggestion.status = SuggestionStatus.APPROVED
        suggestion.resolved_at = datetime.utcnow()
        suggestion.resolved_by_user = True

    # Update sync metadata
    task.last_modified_at = datetime.utcnow()
    task.sync_version += 1

    await db.commit()
    await db.refresh(task)

    # Push changes to TickTick if task is synced
    synced_to_ticktick = False
    if task.ticktick_task_id and changes:
        # Get user for TickTick service
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if user and user.ticktick_access_token:
            try:
                ticktick_service = TickTickService(user=user)
                await ticktick_service.update_task(task.ticktick_task_id, changes, db)
                task.last_synced_at = datetime.utcnow()
                await db.commit()
                synced_to_ticktick = True
                logger.info(f"Synced approved suggestions for task {task_id} to TickTick")
            except Exception as e:
                logger.error(f"Failed to sync approved suggestions to TickTick: {e}")

    return {
        "task_id": task_id,
        "approved_count": len(suggestions),
        "approved_types": [s.suggestion_type for s in suggestions],
        "synced_to_ticktick": synced_to_ticktick
    }


@router.post("/{task_id}/suggestions/reject")
async def reject_suggestions(
    task_id: int,
    suggestion_types: List[str] = Body(..., embed=True),
    user_id: int = Query(..., gt=0, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject specific suggestions (or all).

    Accepts a list of suggestion types to reject (e.g., ["start_date"])
    or ["all"] to reject all pending suggestions.

    Rejected suggestions are marked as rejected but not deleted,
    allowing for tracking of user preferences.
    """
    from app.models.task_suggestion import TaskSuggestion, SuggestionStatus

    # Verify task ownership
    stmt = select(Task).where(Task.id == task_id, Task.user_id == user_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get pending suggestions
    stmt = select(TaskSuggestion).where(
        TaskSuggestion.task_id == task_id,
        TaskSuggestion.status == SuggestionStatus.PENDING
    )

    if "all" not in suggestion_types:
        stmt = stmt.where(TaskSuggestion.suggestion_type.in_(suggestion_types))

    result = await db.execute(stmt)
    suggestions = result.scalars().all()

    if not suggestions:
        return {"message": "No pending suggestions to reject"}

    # Mark suggestions as rejected
    for suggestion in suggestions:
        suggestion.status = SuggestionStatus.REJECTED
        suggestion.resolved_at = datetime.utcnow()
        suggestion.resolved_by_user = True

    await db.commit()

    return {
        "task_id": task_id,
        "rejected_count": len(suggestions),
        "rejected_types": [s.suggestion_type for s in suggestions]
    }


class QuickAnalysisRequest(BaseModel):
    """Request schema for quick task analysis (without creating the task)."""
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    due_date: Optional[datetime] = None
    user_id: int = Field(..., gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Review Q4 financial report",
                "description": "Go through the quarterly financial statements and highlight key metrics",
                "due_date": "2025-12-20T17:00:00Z",
                "user_id": 1
            }
        }


class QuickAnalysisResponse(BaseModel):
    """Response schema for quick analysis."""
    urgency_score: Optional[float]
    importance_score: Optional[float]
    eisenhower_quadrant: Optional[str]
    suggested_priority: Optional[int]  # 0/1/3/5 for TickTick
    analysis_reasoning: Optional[str]

    class Config:
        json_schema_extra = {
            "example": {
                "urgency_score": 7.0,
                "importance_score": 8.0,
                "eisenhower_quadrant": "Q1",
                "suggested_priority": 5,
                "analysis_reasoning": "This is both urgent and important because..."
            }
        }


@router.post("/analyze-quick", response_model=QuickAnalysisResponse)
async def analyze_quick_task(
    request: QuickAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Quickly analyze a task description without creating the task.

    This endpoint is designed for the quick add modal where users
    want to see AI suggestions before actually creating the task.

    Returns urgency/importance scores, quadrant, and suggested priority.
    """
    try:
        ollama = OllamaService()

        # Check if Ollama is available
        if not await ollama.health_check():
            raise HTTPException(
                status_code=503,
                detail="LLM service unavailable. Please try again later."
            )

        # Get user profile context for personalized analysis
        profile_context = await _get_profile_context(request.user_id, db)

        # Perform LLM analysis
        analysis = await ollama.analyze_task(
            request.description,
            profile_context=profile_context
        )

        # Map scores to TickTick priority (0/1/3/5)
        suggested_priority = 0
        if analysis.urgency >= 7 and analysis.importance >= 7:
            suggested_priority = 5  # High priority
        elif analysis.importance >= 7:
            suggested_priority = 3  # Medium priority
        elif analysis.urgency >= 7:
            suggested_priority = 3  # Medium priority
        elif analysis.urgency >= 5 or analysis.importance >= 5:
            suggested_priority = 1  # Low priority

        return QuickAnalysisResponse(
            urgency_score=float(analysis.urgency),
            importance_score=float(analysis.importance),
            eisenhower_quadrant=analysis.quadrant,
            suggested_priority=suggested_priority,
            analysis_reasoning=analysis.reasoning
        )

    except Exception as e:
        logger.error(f"Quick analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )
