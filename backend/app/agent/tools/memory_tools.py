"""
Memory tools for storing and retrieving user preferences and learned facts.

These tools enable the agent to remember user preferences across sessions,
detect work patterns, and provide personalized recommendations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, Optional

from langchain_core.tools import InjectedToolArg, tool
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import UserMemory
from app.models.profile import Profile
from app.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


@tool(parse_docstring=True)
async def store_user_preference(
    preference_key: str,
    preference_value: str,
    config: Annotated[RunnableConfig, InjectedToolArg()],
) -> Dict[str, Any]:
    """Store learned user preference.

    Use this tool when the user explicitly states a preference or you detect
    a pattern in their behavior that should be remembered. Preferences are
    stored in the "preferences" namespace and persist across sessions.

    Args:
        preference_key: Key for preference (e.g., "preferred_time", "work_style", "tone")
        preference_value: Value to store (string representation)

    Returns:
        Success message with stored preference details
    """
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    if not preference_key or not preference_value:
        return {"error": "Both preference_key and preference_value are required"}

    try:
        # Check if preference already exists
        query = select(UserMemory).where(
            UserMemory.user_id == user_id,
            UserMemory.namespace == "preferences",
            UserMemory.key == preference_key,
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing preference
            old_value = existing.value
            existing.value = {"preference": preference_value}
            existing.updated_at = datetime.utcnow()
            action = "updated"
        else:
            # Create new preference
            new_memory = UserMemory(
                user_id=user_id,
                namespace="preferences",
                key=preference_key,
                value={"preference": preference_value},
            )
            db.add(new_memory)
            old_value = None
            action = "stored"

        await db.commit()

        logger.info(
            f"store_user_preference: user_id={user_id}, {action} {preference_key}={preference_value}"
        )

        return {
            "success": True,
            "action": action,
            "preference_key": preference_key,
            "preference_value": preference_value,
            "previous_value": old_value.get("preference") if old_value else None,
            "summary": f"{action.capitalize()} preference: {preference_key} = {preference_value}",
        }

    except Exception as e:
        logger.error(f"store_user_preference failed for user_id={user_id}: {e}", exc_info=True)
        return {
            "error": str(e),
            "summary": f"Error storing preference: {str(e)}",
        }


@tool
async def get_user_context(
    config: Annotated[RunnableConfig, InjectedToolArg()],
) -> Dict[str, Any]:
    """Retrieve stored preferences, learned facts, and work patterns. Use this tool at the start of a conversation to load user context and provide personalized responses."""
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    try:
        # Fetch all user memories
        memories_query = select(UserMemory).where(UserMemory.user_id == user_id)
        memories_result = await db.execute(memories_query)
        memories = memories_result.scalars().all()

        # Organize memories by namespace
        preferences = {}
        learned_facts = {}
        work_patterns = {}

        for memory in memories:
            value = memory.value.get("preference") if "preference" in memory.value else memory.value

            if memory.namespace == "preferences":
                preferences[memory.key] = value
            elif memory.namespace == "learned_facts":
                learned_facts[memory.key] = value
            elif memory.namespace == "work_patterns":
                work_patterns[memory.key] = value

        # Fetch profile information
        profile_query = select(Profile).where(Profile.user_id == user_id)
        profile_result = await db.execute(profile_query)
        profile = profile_result.scalar_one_or_none()

        profile_data = {}
        if profile:
            profile_data = {
                "work_style": profile.work_style,
                "preferred_tone": profile.preferred_tone,
                "energy_pattern": profile.energy_pattern,
                "communication_style": profile.communication_style,
                "people": profile.people,
                "pets": profile.pets,
                "activities": profile.activities,
                "notes": profile.notes,
            }

        logger.info(
            f"get_user_context: user_id={user_id}, "
            f"loaded {len(preferences)} preferences, {len(learned_facts)} facts, "
            f"{len(work_patterns)} patterns"
        )

        return {
            "preferences": preferences,
            "profile": profile_data,
            "work_patterns": work_patterns,
            "learned_facts": learned_facts,
            "summary": f"Loaded {len(preferences)} preferences, "
                      f"{len(learned_facts)} facts, {len(work_patterns)} patterns",
        }

    except Exception as e:
        logger.error(f"get_user_context failed for user_id={user_id}: {e}", exc_info=True)
        return {
            "error": str(e),
            "summary": f"Error retrieving user context: {str(e)}",
        }


@tool(parse_docstring=True)
async def detect_work_pattern(
    config: Annotated[RunnableConfig, InjectedToolArg()],
    analysis_period_days: int = 14,
) -> Dict[str, Any]:
    """Analyze task history to detect work style patterns.

    Use this tool to understand the user's work habits and preferences by
    analyzing their task creation and completion patterns. Results are
    automatically stored in memory for future reference.

    Args:
        analysis_period_days: Days to analyze (default: 14, range: 7-90)

    Returns:
        Dict with detected patterns (early_bird, night_owl, etc.) and insights
    """
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")

    if not user_id or not db:
        return {"error": "Missing user_id or db in config"}

    # Validate and constrain parameters
    analysis_period_days = max(7, min(analysis_period_days, 90))

    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=analysis_period_days)

        # Fetch tasks created in the analysis period
        query = select(Task).where(
            Task.user_id == user_id,
            Task.created_at >= start_date,
            Task.created_at <= end_date,
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        if len(tasks) < 5:
            return {
                "error": "Not enough task history to detect patterns",
                "summary": f"Only {len(tasks)} tasks found in the last {analysis_period_days} days. Need at least 5.",
            }

        # Analyze creation times
        hour_counts = {hour: 0 for hour in range(24)}
        weekday_counts = {day: 0 for day in range(7)}  # 0 = Monday, 6 = Sunday
        completion_times = []

        for task in tasks:
            # Creation hour
            hour = task.created_at.hour
            hour_counts[hour] += 1

            # Day of week
            weekday = task.created_at.weekday()
            weekday_counts[weekday] += 1

            # Completion time (if completed)
            if task.status == TaskStatus.COMPLETED and task.updated_at and task.created_at:
                completion_duration = (task.updated_at - task.created_at).total_seconds() / 3600
                completion_times.append(completion_duration)

        # Detect patterns
        patterns = {}

        # Peak hour detection
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
        morning_tasks = sum(hour_counts[h] for h in range(6, 12))
        afternoon_tasks = sum(hour_counts[h] for h in range(12, 18))
        evening_tasks = sum(hour_counts[h] for h in range(18, 24))

        if morning_tasks > afternoon_tasks and morning_tasks > evening_tasks:
            time_pattern = "early_bird"
            patterns["time_preference"] = "morning"
        elif evening_tasks > morning_tasks and evening_tasks > afternoon_tasks:
            time_pattern = "night_owl"
            patterns["time_preference"] = "evening"
        else:
            time_pattern = "flexible"
            patterns["time_preference"] = "afternoon"

        # Work day pattern
        weekday_total = sum(weekday_counts[d] for d in range(5))  # Mon-Fri
        weekend_total = sum(weekday_counts[d] for d in range(5, 7))  # Sat-Sun

        if weekend_total > weekday_total * 0.3:
            patterns["work_schedule"] = "weekend_warrior"
        else:
            patterns["work_schedule"] = "weekday_focused"

        # Completion speed pattern
        if completion_times:
            avg_completion_hours = sum(completion_times) / len(completion_times)
            if avg_completion_hours < 24:
                patterns["completion_style"] = "fast_executor"
            elif avg_completion_hours < 72:
                patterns["completion_style"] = "steady_pace"
            else:
                patterns["completion_style"] = "thoughtful_planner"
        else:
            patterns["completion_style"] = "unknown"

        # Task volume pattern
        tasks_per_day = len(tasks) / analysis_period_days
        if tasks_per_day > 5:
            patterns["task_volume"] = "high_volume"
        elif tasks_per_day > 2:
            patterns["task_volume"] = "moderate"
        else:
            patterns["task_volume"] = "low_volume"

        # Store detected patterns in memory
        for key, value in patterns.items():
            memory_query = select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.namespace == "work_patterns",
                UserMemory.key == key,
            )
            memory_result = await db.execute(memory_query)
            existing = memory_result.scalar_one_or_none()

            if existing:
                existing.value = {"pattern": value}
                existing.updated_at = datetime.utcnow()
            else:
                new_memory = UserMemory(
                    user_id=user_id,
                    namespace="work_patterns",
                    key=key,
                    value={"pattern": value},
                )
                db.add(new_memory)

        await db.commit()

        logger.info(
            f"detect_work_pattern: user_id={user_id}, analyzed {len(tasks)} tasks, "
            f"detected {len(patterns)} patterns"
        )

        return {
            "patterns": patterns,
            "insights": {
                "peak_hour": peak_hour,
                "tasks_analyzed": len(tasks),
                "analysis_period_days": analysis_period_days,
                "tasks_per_day": round(tasks_per_day, 1),
                "completion_rate": round(
                    sum(1 for t in tasks if t.status == TaskStatus.COMPLETED) / len(tasks) * 100, 1
                ),
            },
            "recommendations": {
                "best_time_to_work": f"{peak_hour}:00 - {(peak_hour + 2) % 24}:00",
                "work_style_suggestion": time_pattern,
            },
            "summary": f"Detected {len(patterns)} work patterns from {len(tasks)} tasks",
        }

    except Exception as e:
        logger.error(f"detect_work_pattern failed for user_id={user_id}: {e}", exc_info=True)
        return {
            "error": str(e),
            "summary": f"Error detecting work patterns: {str(e)}",
        }
