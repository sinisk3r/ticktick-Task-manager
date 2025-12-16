"""
Quadrant Calculator Service

Rule-based Eisenhower Matrix quadrant assignment using priority and due date.
"""

from datetime import datetime, timezone
from typing import Optional


class QuadrantCalculator:
    """
    Calculate Eisenhower Matrix quadrants based on priority and due date.

    Uses rule-based logic to determine urgency and importance scores,
    then assigns tasks to Q1/Q2/Q3/Q4 based on threshold (7).
    """

    URGENCY_THRESHOLD = 7
    IMPORTANCE_THRESHOLD = 7

    @staticmethod
    def calculate_quadrant(
        ticktick_priority: Optional[int] = 0,
        due_date: Optional[datetime] = None,
        urgency_score: Optional[float] = None,
        importance_score: Optional[float] = None,
    ) -> str:
        """
        Calculate Eisenhower quadrant using priority + date with LLM fallback.

        Args:
            ticktick_priority: TickTick priority (0=None, 1=Low, 3=Medium, 5=High)
            due_date: Task due date
            urgency_score: LLM-generated urgency (1-10) for fallback
            importance_score: LLM-generated importance (1-10) for fallback

        Returns:
            str: "Q1", "Q2", "Q3", or "Q4"
        """
        # Calculate urgency from priority and date
        urgency_from_priority = QuadrantCalculator.priority_to_urgency(ticktick_priority or 0)
        urgency_from_date = QuadrantCalculator.calculate_urgency_from_date(due_date)

        # Take maximum urgency
        urgency_combined = max(urgency_from_priority, urgency_from_date)

        # Calculate importance from priority
        importance = QuadrantCalculator.priority_to_importance(ticktick_priority or 0)

        # Fallback to LLM scores if no priority/date provided
        if urgency_combined == 0 and importance == 0:
            if urgency_score is not None and importance_score is not None:
                urgency_combined = int(urgency_score)
                importance = int(importance_score)

        # Apply threshold to determine quadrant
        return QuadrantCalculator._calculate_quadrant_from_scores(
            urgency_combined, importance
        )

    @staticmethod
    def priority_to_urgency(ticktick_priority: int) -> int:
        """
        Map TickTick priority to urgency score (1-10 scale).

        Args:
            ticktick_priority: 0 (None), 1 (Low), 3 (Medium), 5 (High)

        Returns:
            int: Urgency score 0-10
        """
        priority_map = {
            5: 8,  # High priority → high urgency
            3: 6,  # Medium priority → medium urgency
            1: 4,  # Low priority → low urgency
            0: 0,  # No priority → no urgency from priority
        }
        return priority_map.get(ticktick_priority, 0)

    @staticmethod
    def priority_to_importance(ticktick_priority: int) -> int:
        """
        Map TickTick priority to importance score (1-10 scale).

        Priority indicates importance more than urgency in most systems.

        Args:
            ticktick_priority: 0 (None), 1 (Low), 3 (Medium), 5 (High)

        Returns:
            int: Importance score 0-10
        """
        importance_map = {
            5: 9,  # High priority → high importance
            3: 7,  # Medium priority → medium importance (above threshold)
            1: 5,  # Low priority → low importance
            0: 0,  # No priority → no importance from priority
        }
        return importance_map.get(ticktick_priority, 0)

    @staticmethod
    def calculate_urgency_from_date(due_date: Optional[datetime]) -> int:
        """
        Calculate urgency score (1-10) based on due date proximity.

        Args:
            due_date: Task due date (timezone-aware or naive)

        Returns:
            int: Urgency score 0-10
        """
        if not due_date:
            return 0

        # Ensure timezone-aware datetime
        now = datetime.now(timezone.utc)
        if due_date.tzinfo is None:
            # Assume UTC if naive
            due_date = due_date.replace(tzinfo=timezone.utc)

        # Calculate time until due
        time_until_due = (due_date - now).total_seconds()
        days_until_due = time_until_due / 86400  # seconds to days

        # Map days to urgency score
        if days_until_due < 0:  # Overdue
            return 10
        elif days_until_due < 1:  # Due today
            return 9
        elif days_until_due < 3:  # Due within 3 days
            return 8
        elif days_until_due < 7:  # Due within 1 week
            return 6
        elif days_until_due < 14:  # Due within 2 weeks
            return 4
        else:  # Due far future
            return 2

    @staticmethod
    def _calculate_quadrant_from_scores(urgency: int, importance: int) -> str:
        """
        Determine quadrant from urgency and importance scores.

        Args:
            urgency: Urgency score (1-10)
            importance: Importance score (1-10)

        Returns:
            str: "Q1", "Q2", "Q3", or "Q4"
        """
        threshold_u = QuadrantCalculator.URGENCY_THRESHOLD
        threshold_i = QuadrantCalculator.IMPORTANCE_THRESHOLD

        if urgency >= threshold_u and importance >= threshold_i:
            return "Q1"  # Do First (Urgent & Important)
        elif urgency < threshold_u and importance >= threshold_i:
            return "Q2"  # Schedule (Not Urgent, Important)
        elif urgency >= threshold_u and importance < threshold_i:
            return "Q3"  # Delegate (Urgent, Not Important)
        else:
            return "Q4"  # Eliminate (Neither)

    @staticmethod
    def should_recalculate(
        old_priority: Optional[int],
        new_priority: Optional[int],
        old_due_date: Optional[datetime],
        new_due_date: Optional[datetime],
    ) -> bool:
        """
        Determine if quadrant should be recalculated based on changes.

        Args:
            old_priority: Previous TickTick priority
            new_priority: New TickTick priority
            old_due_date: Previous due date
            new_due_date: New due date

        Returns:
            bool: True if priority or due date changed
        """
        priority_changed = old_priority != new_priority

        # Handle date comparison (both None is not a change)
        if old_due_date is None and new_due_date is None:
            date_changed = False
        elif old_due_date is None or new_due_date is None:
            date_changed = True
        else:
            # Compare dates (ignore microseconds)
            date_changed = old_due_date.replace(microsecond=0) != new_due_date.replace(microsecond=0)

        return priority_changed or date_changed
