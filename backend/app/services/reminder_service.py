"""
Reminder Service for proactive task notifications.

This service checks for overdue tasks and upcoming deadlines,
providing data for the notifications SSE endpoint.

Used by /api/notifications/stream to push real-time alerts to the frontend.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class ReminderService:
    """
    Service for checking task reminders and deadlines.

    Provides methods to:
    - Check for overdue tasks (past due_date)
    - Check for upcoming deadlines (within X hours)
    - Calculate reminder urgency
    """

    def __init__(self, db: AsyncSession, user_id: int):
        """
        Initialize reminder service for a specific user.

        Args:
            db: Database session
            user_id: User ID to check reminders for
        """
        self.db = db
        self.user_id = user_id

    async def check_overdue_tasks(self) -> Dict[str, Any]:
        """
        Find tasks that are past their due date.

        Returns only ACTIVE tasks (not completed or deleted) where
        due_date is in the past.

        Returns:
            {
                "overdue_count": int,
                "overdue_tasks": [
                    {
                        "id": int,
                        "title": str,
                        "due_date": str (ISO),
                        "days_overdue": int,
                        "quadrant": str,
                        "urgency_score": int
                    },
                    ...
                ]
            }
        """
        try:
            now = datetime.utcnow()

            # Query for overdue active tasks
            query = select(Task).where(
                Task.user_id == self.user_id,
                Task.status == TaskStatus.ACTIVE,
                Task.due_date.isnot(None),
                Task.due_date < now,
            ).order_by(Task.due_date.asc())

            result = await self.db.execute(query)
            tasks = result.scalars().all()

            # Build overdue task list with metadata
            overdue_tasks = []
            for task in tasks:
                days_overdue = (now - task.due_date).days if task.due_date else 0

                overdue_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "days_overdue": days_overdue,
                    "quadrant": (
                        task.eisenhower_quadrant.value
                        if task.eisenhower_quadrant
                        else "unassigned"
                    ),
                    "urgency_score": task.urgency_score or 0,
                    "project_name": task.project_name,
                })

            logger.info(
                f"check_overdue_tasks: user_id={self.user_id}, "
                f"found {len(overdue_tasks)} overdue tasks"
            )

            return {
                "overdue_count": len(overdue_tasks),
                "overdue_tasks": overdue_tasks,
            }

        except Exception as e:
            logger.error(
                f"check_overdue_tasks failed for user_id={self.user_id}: {e}",
                exc_info=True
            )
            return {
                "overdue_count": 0,
                "overdue_tasks": [],
                "error": str(e),
            }

    async def check_upcoming_deadlines(self, hours: int = 24) -> Dict[str, Any]:
        """
        Find tasks with deadlines approaching within the next X hours.

        Returns only ACTIVE tasks with due_date between now and now + hours.

        Args:
            hours: How many hours ahead to look (default: 24)

        Returns:
            {
                "upcoming_count": int,
                "upcoming_tasks": [
                    {
                        "id": int,
                        "title": str,
                        "due_date": str (ISO),
                        "hours_until_due": float,
                        "quadrant": str
                    },
                    ...
                ]
            }
        """
        try:
            now = datetime.utcnow()
            cutoff = now + timedelta(hours=hours)

            # Query for upcoming deadlines
            query = select(Task).where(
                Task.user_id == self.user_id,
                Task.status == TaskStatus.ACTIVE,
                Task.due_date.isnot(None),
                Task.due_date >= now,
                Task.due_date <= cutoff,
            ).order_by(Task.due_date.asc())

            result = await self.db.execute(query)
            tasks = result.scalars().all()

            # Build upcoming task list with metadata
            upcoming_tasks = []
            for task in tasks:
                if task.due_date:
                    time_until_due = task.due_date - now
                    hours_until_due = time_until_due.total_seconds() / 3600

                    upcoming_tasks.append({
                        "id": task.id,
                        "title": task.title,
                        "due_date": task.due_date.isoformat(),
                        "hours_until_due": round(hours_until_due, 1),
                        "quadrant": (
                            task.eisenhower_quadrant.value
                            if task.eisenhower_quadrant
                            else "unassigned"
                        ),
                        "urgency_score": task.urgency_score or 0,
                        "project_name": task.project_name,
                    })

            logger.info(
                f"check_upcoming_deadlines: user_id={self.user_id}, "
                f"found {len(upcoming_tasks)} tasks due within {hours}h"
            )

            return {
                "upcoming_count": len(upcoming_tasks),
                "upcoming_tasks": upcoming_tasks,
                "hours_ahead": hours,
            }

        except Exception as e:
            logger.error(
                f"check_upcoming_deadlines failed for user_id={self.user_id}: {e}",
                exc_info=True
            )
            return {
                "upcoming_count": 0,
                "upcoming_tasks": [],
                "hours_ahead": hours,
                "error": str(e),
            }

    async def get_reminder_summary(self) -> Dict[str, Any]:
        """
        Get combined summary of overdue and upcoming tasks.

        This is a convenience method that combines both checks into one call.

        Returns:
            {
                "overdue": {...},
                "upcoming": {...},
                "total_alerts": int
            }
        """
        try:
            overdue = await self.check_overdue_tasks()
            upcoming = await self.check_upcoming_deadlines(hours=24)

            total_alerts = (
                overdue.get("overdue_count", 0) +
                upcoming.get("upcoming_count", 0)
            )

            return {
                "overdue": overdue,
                "upcoming": upcoming,
                "total_alerts": total_alerts,
            }

        except Exception as e:
            logger.error(
                f"get_reminder_summary failed for user_id={self.user_id}: {e}",
                exc_info=True
            )
            return {
                "overdue": {"overdue_count": 0, "overdue_tasks": []},
                "upcoming": {"upcoming_count": 0, "upcoming_tasks": []},
                "total_alerts": 0,
                "error": str(e),
            }
