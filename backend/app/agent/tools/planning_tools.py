"""
Planning tools for task prioritization and day planning.

These tools help users organize their day, suggest optimal task ordering,
and provide strategic recommendations based on task priority and context.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.tools import InjectedToolArg, tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, EisenhowerQuadrant

logger = logging.getLogger(__name__)


@tool(parse_docstring=True)
async def prioritize_day(
    config: Annotated[RunnableConfig, InjectedToolArg()],
    focus_areas: Optional[List[str]] = None,
    available_hours: float = 8.0,
) -> Dict[str, Any]:
    """Create prioritized plan for today based on Q1/Q2 tasks.

    Use this tool when the user asks for help planning their day, wants to know
    what to focus on, or needs guidance on task prioritization. Returns a
    structured schedule with time allocations and break suggestions.

    Args:
        focus_areas: Optional list of focus areas to prioritize (e.g., ["work", "personal"])
        available_hours: Hours available for task work (default 8.0, range 1-16)

    Returns:
        Dict with scheduled tasks, time allocations, break suggestions, and insights
    """
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    # Validate and constrain parameters
    available_hours = max(1.0, min(available_hours, 16.0))

    try:
        # Fetch Q1 and Q2 tasks (high priority)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        query = select(Task).where(
            Task.user_id == user_id,
            Task.status == TaskStatus.ACTIVE,
        )

        # Filter by quadrant (Q1 urgent+important, Q2 important)
        query = query.where(
            (Task.manual_quadrant_override.in_([EisenhowerQuadrant.Q1, EisenhowerQuadrant.Q2]))
            | (
                Task.manual_quadrant_override.is_(None)
                & Task.eisenhower_quadrant.in_([EisenhowerQuadrant.Q1, EisenhowerQuadrant.Q2])
            )
        )

        result = await db.execute(query)
        tasks = result.scalars().all()

        # Sort tasks by priority
        # Priority order: Q1 with due date today > Q1 > Q2 with due date soon > Q2
        def task_priority(task: Task) -> tuple:
            effective_quadrant = task.manual_quadrant_override or task.eisenhower_quadrant
            is_q1 = effective_quadrant == EisenhowerQuadrant.Q1

            # Calculate days until due
            days_until_due = 999
            if task.due_date:
                delta = task.due_date - datetime.utcnow()
                days_until_due = delta.days

            # Sort key: (not Q1, days_until_due, -urgency, -importance)
            return (
                not is_q1,  # Q1 comes first
                days_until_due,  # Earlier due dates first
                -(task.urgency_score or 5),  # Higher urgency first
                -(task.importance_score or 5),  # Higher importance first
            )

        sorted_tasks = sorted(tasks, key=task_priority)

        # Filter by focus areas if provided
        if focus_areas:
            focus_areas_lower = [area.lower() for area in focus_areas]
            filtered_tasks = []
            for task in sorted_tasks:
                # Check if task matches any focus area (in title, tags, or project)
                task_text = f"{task.title} {task.description or ''} {task.project_name or ''}".lower()
                task_tags = [tag.lower() for tag in (task.ticktick_tags or [])]

                if any(area in task_text or area in task_tags for area in focus_areas_lower):
                    filtered_tasks.append(task)

            if filtered_tasks:
                sorted_tasks = filtered_tasks

        # Build schedule with time allocations
        available_minutes = int(available_hours * 60)
        scheduled_tasks = []
        total_scheduled_minutes = 0
        overflow_tasks = []

        for task in sorted_tasks:
            # Estimate time if not provided (default 30 mins per task)
            estimated_minutes = task.time_estimate or 30

            if total_scheduled_minutes + estimated_minutes <= available_minutes:
                scheduled_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "quadrant": (task.manual_quadrant_override or task.eisenhower_quadrant).value,
                    "estimated_minutes": estimated_minutes,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "urgency": task.urgency_score,
                    "importance": task.importance_score,
                })
                total_scheduled_minutes += estimated_minutes
            else:
                overflow_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "quadrant": (task.manual_quadrant_override or task.eisenhower_quadrant).value,
                })

        # Calculate break suggestions (5 min break per hour worked)
        hours_worked = total_scheduled_minutes / 60
        suggested_breaks = max(1, int(hours_worked))
        break_duration_minutes = suggested_breaks * 5

        # Generate insights
        q1_count = sum(1 for t in scheduled_tasks if t["quadrant"] == "Q1")
        q2_count = sum(1 for t in scheduled_tasks if t["quadrant"] == "Q2")

        capacity_used = (total_scheduled_minutes / available_minutes) * 100

        insights = {
            "capacity_utilization": round(capacity_used, 1),
            "q1_tasks": q1_count,
            "q2_tasks": q2_count,
            "total_scheduled": len(scheduled_tasks),
            "overflow_count": len(overflow_tasks),
        }

        # Generate recommendation
        if capacity_used > 90:
            recommendation = "Your day is fully scheduled. Consider moving some Q2 tasks to tomorrow."
        elif capacity_used < 50:
            recommendation = "You have capacity for additional tasks. Review your Q3 tasks or plan proactively."
        else:
            recommendation = "Your schedule looks balanced. Focus on Q1 tasks first, then move to Q2."

        logger.info(
            f"prioritize_day: user_id={user_id}, scheduled {len(scheduled_tasks)} tasks, "
            f"{capacity_used:.1f}% capacity used"
        )

        return {
            "scheduled_tasks": scheduled_tasks,
            "overflow_tasks": overflow_tasks,
            "time_allocation": {
                "available_minutes": available_minutes,
                "scheduled_minutes": total_scheduled_minutes,
                "remaining_minutes": available_minutes - total_scheduled_minutes,
                "suggested_break_minutes": break_duration_minutes,
            },
            "insights": insights,
            "recommendation": recommendation,
            "summary": f"Scheduled {len(scheduled_tasks)} tasks for today ({total_scheduled_minutes} mins / {available_minutes} mins available)",
        }

    except Exception as e:
        logger.error(f"prioritize_day failed for user_id={user_id}: {e}", exc_info=True)
        return {
            "error": str(e),
            "summary": f"Error creating daily plan: {str(e)}",
        }


@tool(parse_docstring=True)
async def suggest_task_order(
    task_ids: List[int],
    config: Annotated[RunnableConfig, InjectedToolArg()],
    optimization_goal: str = "completion",
) -> Dict[str, Any]:
    """Suggest optimal order for given tasks.

    Use this tool when the user has multiple tasks and wants to know what order
    to tackle them in. Different optimization goals provide different strategies.

    Args:
        task_ids: List of task IDs to order (required, min 2 tasks)
        optimization_goal: Optimization strategy - completion, impact, energy, or deadlines

    Returns:
        Dict with ordered task IDs, reasoning for each, and strategy explanation
    """
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    if not task_ids or len(task_ids) < 2:
        return {"error": "Must provide at least 2 task IDs"}

    # Validate optimization goal
    valid_goals = ["completion", "impact", "energy", "deadlines"]
    if optimization_goal not in valid_goals:
        optimization_goal = "completion"

    try:
        # Fetch tasks
        query = select(Task).where(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            return {"error": "No tasks found with provided IDs"}

        # Create task lookup
        task_map = {task.id: task for task in tasks}

        # Sort based on optimization goal
        sorted_task_ids: List[int] = []

        if optimization_goal == "completion":
            # Quick wins: shorter tasks first, then by urgency
            sorted_tasks = sorted(
                tasks,
                key=lambda t: (
                    t.time_estimate or 30,  # Shorter first
                    -(t.urgency_score or 5),  # Higher urgency tiebreaker
                )
            )
            strategy = "Quick wins strategy: Tackle shorter tasks first for momentum"

        elif optimization_goal == "impact":
            # High value first: importance, then urgency
            sorted_tasks = sorted(
                tasks,
                key=lambda t: (
                    -(t.importance_score or 5),  # Higher importance first
                    -(t.urgency_score or 5),  # Higher urgency tiebreaker
                )
            )
            strategy = "Impact strategy: Focus on high-importance tasks first"

        elif optimization_goal == "energy":
            # Eat the frog: hardest/longest tasks first
            sorted_tasks = sorted(
                tasks,
                key=lambda t: (
                    -(t.time_estimate or 30),  # Longer first
                    -(t.urgency_score or 5),  # Higher urgency tiebreaker
                )
            )
            strategy = "Energy strategy: Tackle hardest tasks while fresh"

        else:  # deadlines
            # Due dates first, then urgency
            sorted_tasks = sorted(
                tasks,
                key=lambda t: (
                    t.due_date or datetime.max.replace(tzinfo=None),  # Earlier due dates first
                    -(t.urgency_score or 5),  # Higher urgency tiebreaker
                )
            )
            strategy = "Deadline strategy: Focus on time-sensitive tasks first"

        sorted_task_ids = [task.id for task in sorted_tasks]

        # Generate reasoning for each task
        ordered_tasks = []
        for idx, task in enumerate(sorted_tasks, 1):
            effective_quadrant = task.manual_quadrant_override or task.eisenhower_quadrant

            # Generate position reasoning
            if idx == 1:
                position_reason = "Start here"
            elif idx == len(sorted_tasks):
                position_reason = "Save for last"
            elif idx <= len(sorted_tasks) // 2:
                position_reason = "Tackle early"
            else:
                position_reason = "Address later"

            # Generate task-specific reasoning
            reasons = []
            if optimization_goal == "completion":
                est_min = task.time_estimate or 30
                reasons.append(f"{est_min} min task - quick to complete")
            elif optimization_goal == "impact":
                reasons.append(f"Importance score: {task.importance_score or 'N/A'}")
            elif optimization_goal == "energy":
                est_min = task.time_estimate or 30
                reasons.append(f"{est_min} min task - requires focus")
            else:  # deadlines
                if task.due_date:
                    delta = task.due_date - datetime.utcnow()
                    if delta.days < 1:
                        reasons.append("Due today - urgent")
                    elif delta.days < 3:
                        reasons.append(f"Due in {delta.days} days")
                    else:
                        reasons.append(f"Due {task.due_date.strftime('%Y-%m-%d')}")
                else:
                    reasons.append("No deadline - lower priority")

            ordered_tasks.append({
                "id": task.id,
                "title": task.title,
                "position": idx,
                "position_reason": position_reason,
                "reasoning": " | ".join(reasons) if reasons else "No specific reasoning",
                "quadrant": effective_quadrant.value if effective_quadrant else None,
                "estimated_minutes": task.time_estimate,
            })

        logger.info(
            f"suggest_task_order: user_id={user_id}, ordered {len(ordered_tasks)} tasks "
            f"using {optimization_goal} strategy"
        )

        return {
            "ordered_tasks": ordered_tasks,
            "optimization_goal": optimization_goal,
            "strategy_explanation": strategy,
            "summary": f"Ordered {len(ordered_tasks)} tasks using {optimization_goal} strategy",
        }

    except Exception as e:
        logger.error(f"suggest_task_order failed for user_id={user_id}: {e}", exc_info=True)
        return {
            "error": str(e),
            "summary": f"Error suggesting task order: {str(e)}",
        }
