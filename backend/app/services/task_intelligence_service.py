"""
Task Intelligence Service - Handles stale task detection, task breakdown, and email drafting.

This service provides intelligent analysis and automation features:
- Stale task detection with actionable insights
- Task breakdown into manageable subtasks
- Email drafting for task-related communications
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, EisenhowerQuadrant
from app.agent.llm_factory import get_llm_for_user

logger = logging.getLogger(__name__)


class TaskIntelligenceService:
    """
    Service for intelligent task analysis and automation.

    Provides:
    - Stale task detection with severity-based recommendations
    - AI-powered task breakdown into subtasks
    - Context-aware email drafting for task communications
    """

    def __init__(self, db: AsyncSession, user_id: int):
        """
        Initialize the service.

        Args:
            db: Database session
            user_id: User ID for LLM configuration and task access
        """
        self.db = db
        self.user_id = user_id

    async def detect_stale_tasks(
        self,
        days_threshold: int = 14,
        include_completed: bool = False,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Detect stale tasks that haven't been updated in a while.

        Args:
            days_threshold: Number of days without update to consider stale (default: 14)
            include_completed: Whether to include completed tasks (default: False)
            limit: Maximum number of tasks to return (default: 20)

        Returns:
            Dictionary with:
            - stale_tasks: List of stale tasks with staleness analysis
            - summary: Overall statistics
            - insights_by_quadrant: Breakdown by Eisenhower quadrant

        Example:
            >>> service = TaskIntelligenceService(db, user_id=1)
            >>> result = await service.detect_stale_tasks(days_threshold=7)
            >>> print(f"Found {len(result['stale_tasks'])} stale tasks")
        """
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

            # Build query
            query = select(Task).where(
                Task.user_id == self.user_id,
                Task.updated_at < cutoff_date
            )

            # Filter by status
            if not include_completed:
                query = query.where(Task.status == TaskStatus.ACTIVE)

            # Order by updated_at ascending (oldest first)
            query = query.order_by(Task.updated_at.asc()).limit(limit)

            # Execute query
            result = await self.db.execute(query)
            tasks = result.scalars().all()

            # Analyze each task
            stale_tasks = []
            quadrant_counts = {q.value: 0 for q in EisenhowerQuadrant}

            now = datetime.now(timezone.utc)

            for task in tasks:
                # Calculate days stale
                days_stale = (now - task.updated_at).days

                # Determine staleness reason and severity
                staleness_reason, severity = self._analyze_staleness(task, days_stale, days_threshold)

                # Generate suggested action
                suggested_action = self._suggest_action(task, severity, days_stale)

                # Get effective quadrant
                effective_quadrant = task.manual_quadrant_override or task.eisenhower_quadrant
                if effective_quadrant:
                    quadrant_counts[effective_quadrant.value] += 1

                stale_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status.value if hasattr(task.status, "value") else task.status,
                    "eisenhower_quadrant": effective_quadrant.value if effective_quadrant else None,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "days_stale": days_stale,
                    "staleness_reason": staleness_reason,
                    "severity": severity,
                    "suggested_action": suggested_action,
                    "urgency_score": task.urgency_score,
                    "importance_score": task.importance_score,
                })

            # Build insights by quadrant
            insights_by_quadrant = {}
            for quadrant, count in quadrant_counts.items():
                if count > 0:
                    insights_by_quadrant[quadrant] = {
                        "count": count,
                        "insight": self._quadrant_insight(quadrant, count)
                    }

            # Summary statistics
            summary = {
                "total_stale": len(stale_tasks),
                "days_threshold": days_threshold,
                "cutoff_date": cutoff_date.isoformat(),
                "high_severity_count": sum(1 for t in stale_tasks if t["severity"] == "high"),
                "medium_severity_count": sum(1 for t in stale_tasks if t["severity"] == "medium"),
                "low_severity_count": sum(1 for t in stale_tasks if t["severity"] == "low"),
            }

            logger.info(
                f"Detected {len(stale_tasks)} stale tasks for user {self.user_id} "
                f"(threshold: {days_threshold} days)"
            )

            return {
                "stale_tasks": stale_tasks,
                "summary": summary,
                "insights_by_quadrant": insights_by_quadrant,
            }

        except Exception as e:
            logger.error(f"Error detecting stale tasks for user {self.user_id}: {e}", exc_info=True)
            return {
                "stale_tasks": [],
                "summary": {"total_stale": 0, "error": str(e)},
                "insights_by_quadrant": {},
            }

    def _analyze_staleness(self, task: Task, days_stale: int, threshold: int) -> tuple[str, str]:
        """
        Analyze why a task is stale and determine severity.

        Returns:
            Tuple of (staleness_reason, severity)
        """
        # Severity levels based on multiples of threshold
        if days_stale >= threshold * 3:
            severity = "high"
            reason = f"No activity for {days_stale} days (3x threshold)"
        elif days_stale >= threshold * 2:
            severity = "high"
            reason = f"No activity for {days_stale} days (2x threshold)"
        elif days_stale >= threshold * 1.5:
            severity = "medium"
            reason = f"No activity for {days_stale} days (1.5x threshold)"
        else:
            severity = "low"
            reason = f"No activity for {days_stale} days"

        # Upgrade severity if task has high urgency/importance
        effective_quadrant = task.manual_quadrant_override or task.eisenhower_quadrant
        if effective_quadrant == EisenhowerQuadrant.Q1 and severity == "low":
            severity = "medium"
            reason += " (Q1 task requires attention)"

        # Check if overdue
        if task.due_date and task.due_date < datetime.now(timezone.utc):
            overdue_days = (datetime.now(timezone.utc) - task.due_date).days
            severity = "high"
            reason += f" and overdue by {overdue_days} days"

        return reason, severity

    def _suggest_action(self, task: Task, severity: str, days_stale: int) -> str:
        """Generate suggested action based on task staleness."""
        effective_quadrant = task.manual_quadrant_override or task.eisenhower_quadrant

        if severity == "high":
            if task.status == TaskStatus.ACTIVE:
                if effective_quadrant == EisenhowerQuadrant.Q1:
                    return "Complete immediately or escalate if blocked"
                elif effective_quadrant == EisenhowerQuadrant.Q2:
                    return "Schedule dedicated time this week or delegate"
                elif effective_quadrant == EisenhowerQuadrant.Q3:
                    return "Delegate or defer if no longer urgent"
                else:
                    return "Consider deleting if no longer relevant"
            else:
                return "Review if task should be reopened or archived"

        elif severity == "medium":
            if effective_quadrant in [EisenhowerQuadrant.Q1, EisenhowerQuadrant.Q2]:
                return "Schedule time to work on this or break it down into smaller tasks"
            else:
                return "Review priority - consider deleting if no longer needed"

        else:  # low severity
            return "Review and update status if still relevant"

    def _quadrant_insight(self, quadrant: str, count: int) -> str:
        """Generate insight for quadrant stale task count."""
        insights = {
            "Q1": f"{count} urgent+important task(s) need immediate attention",
            "Q2": f"{count} important task(s) may need scheduling or delegation",
            "Q3": f"{count} urgent task(s) could be delegated or eliminated",
            "Q4": f"{count} low-priority task(s) should be reviewed for deletion",
        }
        return insights.get(quadrant, f"{count} stale task(s)")

    async def breakdown_task(
        self,
        task_id: Optional[int] = None,
        description: Optional[str] = None,
        max_subtasks: int = 5,
    ) -> Dict[str, Any]:
        """
        Break down a complex task into smaller, actionable subtasks using LLM.

        Args:
            task_id: ID of existing task to break down (optional)
            description: Task description if not using task_id (optional)
            max_subtasks: Maximum number of subtasks to generate (default: 5)

        Returns:
            Dictionary with:
            - subtasks: List of subtask objects with title, description, estimated_minutes
            - total_estimated_minutes: Total time estimate
            - approach_notes: Explanation of breakdown strategy

        Example:
            >>> service = TaskIntelligenceService(db, user_id=1)
            >>> result = await service.breakdown_task(
            ...     task_id=42,
            ...     max_subtasks=4
            ... )
            >>> for subtask in result['subtasks']:
            ...     print(f"- {subtask['title']}")
        """
        try:
            task_title = None
            task_description = description

            # Load task if task_id provided
            if task_id:
                result = await self.db.execute(
                    select(Task).where(Task.id == task_id, Task.user_id == self.user_id)
                )
                task = result.scalar_one_or_none()
                if not task:
                    return {
                        "error": f"Task {task_id} not found or not owned by user",
                        "subtasks": [],
                    }
                task_title = task.title
                task_description = task.description or task.title

            if not task_description:
                return {
                    "error": "Either task_id or description must be provided",
                    "subtasks": [],
                }

            # Load prompt template
            prompt_template = self._load_prompt("task_breakdown_v1.txt")

            # Build prompt
            prompt = prompt_template.format(
                task_title=task_title or "Untitled Task",
                task_description=task_description,
                max_subtasks=max_subtasks,
            )

            # Get LLM for user
            llm = await get_llm_for_user(self.user_id, self.db)

            # Call LLM
            response = await llm.ainvoke(prompt)

            # Parse response
            response_text = response.content if hasattr(response, "content") else str(response)

            # Try to extract JSON
            breakdown_data = self._parse_json_response(response_text)

            # Validate structure
            if "subtasks" not in breakdown_data:
                raise ValueError("LLM response missing 'subtasks' key")

            logger.info(
                f"Generated {len(breakdown_data.get('subtasks', []))} subtasks for user {self.user_id}"
            )

            return {
                "subtasks": breakdown_data.get("subtasks", []),
                "total_estimated_minutes": breakdown_data.get("total_estimated_minutes", 0),
                "approach_notes": breakdown_data.get("approach_notes", ""),
            }

        except Exception as e:
            logger.error(f"Error breaking down task for user {self.user_id}: {e}", exc_info=True)
            return {
                "error": str(e),
                "subtasks": [],
                "total_estimated_minutes": 0,
                "approach_notes": "",
            }

    async def draft_email(
        self,
        task_id: int,
        email_type: str = "status_update",
        recipient_context: Optional[str] = None,
        tone: str = "professional",
    ) -> Dict[str, Any]:
        """
        Draft an email related to a task using LLM.

        Args:
            task_id: ID of the task to draft email about (required)
            email_type: Type of email - "status_update", "request", "escalation", "completion"
            recipient_context: Who is receiving the email (e.g., "team lead", "client")
            tone: Email tone - "professional", "friendly", "formal", "urgent"

        Returns:
            Dictionary with:
            - subject: Email subject line
            - body: Email body with proper formatting
            - suggested_ccs: List of suggested CC recipients

        Example:
            >>> service = TaskIntelligenceService(db, user_id=1)
            >>> email = await service.draft_email(
            ...     task_id=42,
            ...     email_type="status_update",
            ...     recipient_context="project manager",
            ...     tone="professional"
            ... )
            >>> print(email['subject'])
            >>> print(email['body'])
        """
        try:
            # Load task by ID
            result = await self.db.execute(
                select(Task).where(Task.id == task_id, Task.user_id == self.user_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                return {
                    "error": f"Task {task_id} not found or not owned by user",
                    "subject": "",
                    "body": "",
                    "suggested_ccs": [],
                }

            # Load prompt template
            prompt_template = self._load_prompt("email_draft_v1.txt")

            # Get effective quadrant
            effective_quadrant = task.manual_quadrant_override or task.eisenhower_quadrant
            quadrant_str = effective_quadrant.value if effective_quadrant else "Unknown"

            # Build prompt
            prompt = prompt_template.format(
                task_title=task.title,
                task_description=task.description or "No description provided",
                task_status=task.status.value if hasattr(task.status, "value") else task.status,
                due_date=task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date",
                quadrant=quadrant_str,
                email_type=email_type,
                recipient_context=recipient_context or "recipient",
                tone=tone,
            )

            # Get LLM for user
            llm = await get_llm_for_user(self.user_id, self.db)

            # Call LLM
            response = await llm.ainvoke(prompt)

            # Parse response
            response_text = response.content if hasattr(response, "content") else str(response)

            # Try to extract JSON
            email_data = self._parse_json_response(response_text)

            # Validate structure
            if "subject" not in email_data or "body" not in email_data:
                raise ValueError("LLM response missing required email fields")

            logger.info(
                f"Drafted {email_type} email for task {task_id}, user {self.user_id}"
            )

            return {
                "subject": email_data.get("subject", ""),
                "body": email_data.get("body", ""),
                "suggested_ccs": email_data.get("suggested_ccs", []),
            }

        except Exception as e:
            logger.error(f"Error drafting email for task {task_id}: {e}", exc_info=True)
            return {
                "error": str(e),
                "subject": "",
                "body": "",
                "suggested_ccs": [],
            }

    def _load_prompt(self, filename: str) -> str:
        """Load prompt template from app/prompts/ directory."""
        prompt_path = Path(__file__).parent.parent / "prompts" / filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text()

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling various formats.

        Tries:
        1. Direct JSON parsing
        2. Extracting JSON from code blocks
        3. Finding JSON pattern in text
        """
        # Try direct parsing
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try extracting from code block
        import re

        # Look for JSON in code blocks (```json ... ```)
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Look for JSON object pattern
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from LLM response: {response_text[:200]}")


# Convenience function for creating service instance
async def get_task_intelligence_service(
    db: AsyncSession,
    user_id: int
) -> TaskIntelligenceService:
    """
    Factory function to create TaskIntelligenceService instance.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Configured TaskIntelligenceService instance

    Example:
        >>> service = await get_task_intelligence_service(db, user_id=1)
        >>> stale_tasks = await service.detect_stale_tasks()
    """
    return TaskIntelligenceService(db, user_id)
