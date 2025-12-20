"""
Wellbeing and workload intelligence service.

Provides analytics for work intensity, capacity, and rest recommendations.
Used by agent tools: get_workload_analytics, get_rest_recommendation
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, EisenhowerQuadrant


class WellbeingService:
    """Service for workload analytics and rest recommendations."""

    # Configuration constants
    DEFAULT_WORK_HOURS_PER_DAY = 8
    DEFAULT_WORK_DAYS_PER_WEEK = 5

    # Risk thresholds (percentage of capacity)
    RISK_LOW = 70
    RISK_MEDIUM = 85
    RISK_HIGH = 100
    RISK_CRITICAL = 120

    # Rest score factors
    REST_CONSECUTIVE_DAYS_WEIGHT = 10  # Penalty per consecutive work day
    REST_Q1_DENSITY_THRESHOLD = 3  # Q1 tasks per day threshold
    REST_OVERDUE_WEIGHT = 5  # Penalty per overdue task

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_period_bounds(self, period: str) -> Tuple[datetime, datetime]:
        """Get start and end datetime for a period."""
        now = datetime.utcnow()

        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif period == "this_week":
            # Start from Monday
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        elif period == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Calculate next month
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)
        else:
            raise ValueError(f"Invalid period: {period}. Use 'today', 'this_week', or 'this_month'")

        return start, end

    def _get_available_hours(self, period: str) -> float:
        """Calculate available work hours for a period."""
        if period == "today":
            return float(self.DEFAULT_WORK_HOURS_PER_DAY)
        elif period == "this_week":
            return float(self.DEFAULT_WORK_HOURS_PER_DAY * self.DEFAULT_WORK_DAYS_PER_WEEK)
        elif period == "this_month":
            # Approximate 4.3 weeks per month
            return float(self.DEFAULT_WORK_HOURS_PER_DAY * self.DEFAULT_WORK_DAYS_PER_WEEK * 4.3)
        return 40.0

    async def calculate_workload(self, period: str = "this_week") -> Dict[str, Any]:
        """
        Calculate detailed workload analytics for the user.

        Returns:
            Dict with capacity, risk_level, quadrant_breakdown, suggestions
        """
        period_start, period_end = self.get_period_bounds(period)
        available_hours = self._get_available_hours(period)

        # Query tasks by quadrant with time estimates
        quadrant_stats = {}
        total_hours = 0.0
        total_tasks = 0

        for quadrant in ["Q1", "Q2", "Q3", "Q4"]:
            try:
                quadrant_enum = EisenhowerQuadrant(quadrant)
            except ValueError:
                continue

            # Count and sum time for each quadrant
            query = select(
                func.count(Task.id).label("count"),
                func.coalesce(func.sum(Task.time_estimate), 0).label("total_minutes"),
                func.coalesce(func.sum(Task.effort_hours), 0).label("total_hours"),
            ).where(
                Task.user_id == self.user_id,
                Task.status == TaskStatus.ACTIVE,
                Task.eisenhower_quadrant == quadrant_enum,
            )

            result = await self.db.execute(query)
            row = result.one()

            count = row.count or 0
            # Use time_estimate (minutes) or effort_hours, convert to hours
            minutes = row.total_minutes or 0
            hours_from_minutes = minutes / 60 if minutes else 0
            hours_from_effort = row.total_hours or 0

            # Use the larger value (some tasks have time_estimate, others effort_hours)
            hours = max(hours_from_minutes, hours_from_effort)

            quadrant_stats[quadrant] = {
                "count": count,
                "hours": round(hours, 1),
            }
            total_hours += hours
            total_tasks += count

        # Count overdue tasks
        overdue_query = select(func.count(Task.id)).where(
            Task.user_id == self.user_id,
            Task.status == TaskStatus.ACTIVE,
            Task.due_date < datetime.utcnow(),
        )
        overdue_result = await self.db.execute(overdue_query)
        overdue_count = overdue_result.scalar() or 0

        # Count tasks due in period
        due_soon_query = select(func.count(Task.id)).where(
            Task.user_id == self.user_id,
            Task.status == TaskStatus.ACTIVE,
            Task.due_date.between(period_start, period_end),
        )
        due_soon_result = await self.db.execute(due_soon_query)
        due_soon_count = due_soon_result.scalar() or 0

        # Calculate utilization and risk
        utilization = (total_hours / available_hours * 100) if available_hours > 0 else 0
        risk_level, risk_factors = self._calculate_risk_level(
            utilization=utilization,
            overdue_count=overdue_count,
            q1_count=quadrant_stats.get("Q1", {}).get("count", 0),
        )

        # Generate suggestions
        suggestions = self._generate_workload_suggestions(
            utilization=utilization,
            risk_level=risk_level,
            quadrant_stats=quadrant_stats,
            overdue_count=overdue_count,
        )

        # Work intensity score (0-100)
        work_intensity = self._calculate_work_intensity(
            utilization=utilization,
            q1_count=quadrant_stats.get("Q1", {}).get("count", 0),
            overdue_count=overdue_count,
        )

        return {
            "period": period,
            "capacity": {
                "hours_scheduled": round(total_hours, 1),
                "hours_available": round(available_hours, 1),
                "utilization_percent": round(utilization, 1),
            },
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "work_intensity": work_intensity,
            "quadrant_breakdown": quadrant_stats,
            "overdue_tasks": overdue_count,
            "due_soon_tasks": due_soon_count,
            "suggestions": suggestions,
            "summary": self._generate_workload_summary(
                utilization=utilization,
                risk_level=risk_level,
                total_tasks=total_tasks,
                period=period,
            ),
        }

    def _calculate_risk_level(
        self,
        utilization: float,
        overdue_count: int,
        q1_count: int,
    ) -> Tuple[str, List[str]]:
        """Determine risk level and contributing factors."""
        factors = []

        if utilization > self.RISK_CRITICAL:
            factors.append(f"Significantly overcommitted ({utilization:.0f}% capacity)")
        elif utilization > self.RISK_HIGH:
            factors.append(f"At or above capacity ({utilization:.0f}%)")

        if overdue_count > 3:
            factors.append(f"{overdue_count} overdue tasks creating backlog pressure")
        elif overdue_count > 0:
            factors.append(f"{overdue_count} overdue task(s)")

        if q1_count > 5:
            factors.append(f"High Q1 load: {q1_count} urgent+important tasks")

        # Determine risk level
        if utilization >= self.RISK_CRITICAL or overdue_count > 5:
            return "critical", factors
        elif utilization >= self.RISK_HIGH or overdue_count > 3:
            return "high", factors
        elif utilization >= self.RISK_MEDIUM or overdue_count > 1:
            return "medium", factors
        else:
            return "low", factors

    def _calculate_work_intensity(
        self,
        utilization: float,
        q1_count: int,
        overdue_count: int,
    ) -> int:
        """Calculate work intensity score (0-100)."""
        # Base score from utilization (0-50 points)
        utilization_score = min(utilization / 2, 50)

        # Q1 pressure (0-30 points)
        q1_score = min(q1_count * 6, 30)

        # Overdue stress (0-20 points)
        overdue_score = min(overdue_count * 4, 20)

        total = utilization_score + q1_score + overdue_score
        return min(int(total), 100)

    def _generate_workload_suggestions(
        self,
        utilization: float,
        risk_level: str,
        quadrant_stats: Dict[str, Any],
        overdue_count: int,
    ) -> List[Dict[str, str]]:
        """Generate actionable suggestions based on workload."""
        suggestions = []

        if risk_level in ["high", "critical"]:
            # Suggest delegation for Q3 tasks
            q3_count = quadrant_stats.get("Q3", {}).get("count", 0)
            if q3_count > 0:
                suggestions.append({
                    "type": "delegate",
                    "message": f"Consider delegating {q3_count} Q3 (urgent but not important) tasks",
                    "priority": "high",
                })

            # Suggest rescheduling Q2 tasks
            q2_count = quadrant_stats.get("Q2", {}).get("count", 0)
            if q2_count > 2:
                suggestions.append({
                    "type": "reschedule",
                    "message": "Consider moving some Q2 tasks to next week to reduce immediate load",
                    "priority": "medium",
                })

        if overdue_count > 0:
            suggestions.append({
                "type": "prioritize",
                "message": f"Address {overdue_count} overdue task(s) to reduce stress",
                "priority": "high" if overdue_count > 3 else "medium",
            })

        if utilization > 90:
            suggestions.append({
                "type": "buffer",
                "message": "Block buffer time for unexpected tasks - you're near capacity",
                "priority": "medium",
            })

        # Q4 cleanup suggestion
        q4_count = quadrant_stats.get("Q4", {}).get("count", 0)
        if q4_count > 5:
            suggestions.append({
                "type": "eliminate",
                "message": f"Consider eliminating or archiving {q4_count} Q4 tasks that aren't urgent or important",
                "priority": "low",
            })

        return suggestions

    def _generate_workload_summary(
        self,
        utilization: float,
        risk_level: str,
        total_tasks: int,
        period: str,
    ) -> str:
        """Generate human-readable workload summary."""
        period_label = {
            "today": "Today",
            "this_week": "This week",
            "this_month": "This month",
        }.get(period, period)

        risk_emoji = {
            "low": "✅",
            "medium": "⚠️",
            "high": "🔴",
            "critical": "🚨",
        }.get(risk_level, "")

        return (
            f"{period_label}: {total_tasks} active tasks at {utilization:.0f}% capacity. "
            f"{risk_emoji} Risk level: {risk_level}"
        )

    async def calculate_rest_recommendation(self) -> Dict[str, Any]:
        """
        Calculate rest recommendation based on work patterns.

        Analyzes:
        - Recent task activity
        - Q1 task density
        - Overdue task stress
        - Estimated work intensity

        Returns:
            Dict with needs_rest, urgency, suggested_action, reasoning
        """
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)

        # Count completions in last 7 days (indicates activity level)
        completions_query = select(func.count(Task.id)).where(
            Task.user_id == self.user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.updated_at >= seven_days_ago,
        )
        completions_result = await self.db.execute(completions_query)
        recent_completions = completions_result.scalar() or 0

        # Count active Q1 tasks
        q1_query = select(func.count(Task.id)).where(
            Task.user_id == self.user_id,
            Task.status == TaskStatus.ACTIVE,
            Task.eisenhower_quadrant == EisenhowerQuadrant.Q1,
        )
        q1_result = await self.db.execute(q1_query)
        q1_count = q1_result.scalar() or 0

        # Count overdue tasks
        overdue_query = select(func.count(Task.id)).where(
            Task.user_id == self.user_id,
            Task.status == TaskStatus.ACTIVE,
            Task.due_date < now,
        )
        overdue_result = await self.db.execute(overdue_query)
        overdue_count = overdue_result.scalar() or 0

        # Get workload utilization
        workload = await self.calculate_workload("this_week")
        utilization = workload["capacity"]["utilization_percent"]

        # Calculate rest score factors
        q1_density = q1_count / 7  # Q1 tasks per day
        overdue_stress = min(overdue_count * self.REST_OVERDUE_WEIGHT, 30)

        # Estimate consecutive work days from activity
        # (Simplified - in production, could track actual login/activity)
        estimated_consecutive_days = min(recent_completions / 3, 7)

        # Calculate rest score (0-100, higher = more rest needed)
        rest_score = 0
        rest_score += min(estimated_consecutive_days * self.REST_CONSECUTIVE_DAYS_WEIGHT, 40)
        rest_score += min(q1_density * 15, 30)  # Q1 pressure
        rest_score += overdue_stress
        rest_score = min(int(rest_score), 100)

        # Determine urgency and recommendation
        if rest_score >= 70:
            urgency = "immediate"
            needs_rest = True
            if q1_count > 3:
                suggested_action = "Take a 30-minute break now. You have high Q1 pressure."
                suggested_duration = 30
            else:
                suggested_action = "Consider taking the rest of the day off or ending work early."
                suggested_duration = 240
        elif rest_score >= 50:
            urgency = "soon"
            needs_rest = True
            suggested_action = "Schedule a 1-2 hour break today or a rest period tomorrow."
            suggested_duration = 90
        else:
            urgency = "optional"
            needs_rest = False
            suggested_action = "You're managing well. Consider a short break if you feel tired."
            suggested_duration = 15

        # Build reasoning
        reasoning_parts = []
        if estimated_consecutive_days >= 5:
            reasoning_parts.append(f"High activity level ({recent_completions} tasks completed recently)")
        if q1_count > 3:
            reasoning_parts.append(f"{q1_count} urgent+important tasks (Q1 pressure)")
        if overdue_count > 0:
            reasoning_parts.append(f"{overdue_count} overdue tasks adding stress")
        if utilization > 85:
            reasoning_parts.append(f"At {utilization:.0f}% capacity")

        reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Workload appears manageable."

        return {
            "needs_rest": needs_rest,
            "urgency": urgency,
            "rest_score": rest_score,
            "factors": {
                "consecutive_work_days": round(estimated_consecutive_days, 1),
                "q1_task_density": round(q1_density, 2),
                "overdue_stress_factor": overdue_stress,
                "recent_completions": recent_completions,
            },
            "suggested_action": suggested_action,
            "suggested_duration_minutes": suggested_duration,
            "reasoning": reasoning,
            "summary": (
                f"Rest score: {rest_score}/100. "
                f"{'Rest recommended' if needs_rest else 'Doing okay'}. "
                f"{suggested_action}"
            ),
        }
