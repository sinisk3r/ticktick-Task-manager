"""
Workload calculator for providing context to LLM suggestion engine.
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task import Task, TaskStatus


async def calculate_user_workload(user_id: int, db: AsyncSession) -> dict:
    """
    Calculate user's current task workload for LLM context.

    Args:
        user_id: User ID to calculate workload for
        db: Database session

    Returns:
        dict with workload statistics:
        {
            "total_q1_tasks": int,
            "total_q2_tasks": int,
            "total_q3_tasks": int,
            "total_q4_tasks": int,
            "total_active_tasks": int,
            "estimated_hours_q1": float,
            "estimated_hours_q2": float,
            "available_hours_this_week": float
        }
    """
    workload = {}

    # Count tasks by quadrant (active tasks only)
    for quad in ["Q1", "Q2", "Q3", "Q4"]:
        # Count tasks
        count_stmt = select(func.count(Task.id)).where(
            Task.user_id == user_id,
            Task.eisenhower_quadrant == quad,
            Task.status == TaskStatus.ACTIVE
        )
        result = await db.execute(count_stmt)
        workload[f"total_{quad.lower()}_tasks"] = result.scalar() or 0

        # Sum effort hours
        effort_stmt = select(func.sum(Task.effort_hours)).where(
            Task.user_id == user_id,
            Task.eisenhower_quadrant == quad,
            Task.status == TaskStatus.ACTIVE,
            Task.effort_hours.isnot(None)
        )
        result = await db.execute(effort_stmt)
        workload[f"estimated_hours_{quad.lower()}"] = result.scalar() or 0.0

    # Total active tasks
    total_stmt = select(func.count(Task.id)).where(
        Task.user_id == user_id,
        Task.status == TaskStatus.ACTIVE
    )
    result = await db.execute(total_stmt)
    workload["total_active_tasks"] = result.scalar() or 0

    # Calculate available hours this week
    # Simple heuristic: 40 work hours per week minus high priority tasks
    # This can be enhanced with actual calendar integration later
    q1_hours = workload.get("estimated_hours_q1", 0.0)
    q2_hours = workload.get("estimated_hours_q2", 0.0)
    committed_hours = q1_hours + (q2_hours * 0.5)  # Q2 is less urgent
    workload["available_hours_this_week"] = max(0, 40 - committed_hours)

    return workload


async def get_project_context(project_id: int, db: AsyncSession) -> dict:
    """
    Get context about a project for LLM suggestions.

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        dict with project context:
        {
            "name": str,
            "total_tasks": int,
            "completed_tasks": int,
            "active_tasks": int
        }
    """
    from app.models.project import Project

    # Get project
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        return {"name": "Unknown", "total_tasks": 0, "completed_tasks": 0, "active_tasks": 0}

    # Count tasks
    total_stmt = select(func.count(Task.id)).where(Task.project_id == project_id)
    result = await db.execute(total_stmt)
    total_tasks = result.scalar() or 0

    completed_stmt = select(func.count(Task.id)).where(
        Task.project_id == project_id,
        Task.status == TaskStatus.COMPLETED
    )
    result = await db.execute(completed_stmt)
    completed_tasks = result.scalar() or 0

    active_stmt = select(func.count(Task.id)).where(
        Task.project_id == project_id,
        Task.status == TaskStatus.ACTIVE
    )
    result = await db.execute(active_stmt)
    active_tasks = result.scalar() or 0

    return {
        "name": project.name,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "active_tasks": active_tasks
    }


async def get_related_tasks(task_id: int, project_id: int, db: AsyncSession, limit: int = 5) -> list[dict]:
    """
    Get related tasks in the same project for context.

    Args:
        task_id: Current task ID
        project_id: Project ID to search within
        db: Database session
        limit: Maximum number of related tasks to return

    Returns:
        List of related task summaries
    """
    if not project_id:
        return []

    stmt = (
        select(Task)
        .where(
            Task.project_id == project_id,
            Task.id != task_id,  # Exclude current task
            Task.status == TaskStatus.ACTIVE
        )
        .order_by(Task.due_date.asc().nullsfirst())
        .limit(limit)
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return [
        {
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "eisenhower_quadrant": task.eisenhower_quadrant.value if task.eisenhower_quadrant else None,
            "ticktick_priority": task.ticktick_priority
        }
        for task in tasks
    ]
