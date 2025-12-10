#!/usr/bin/env python3
"""
Backfill manual_order for existing tasks.
Sets manual_order based on created_at within each quadrant.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.task import Task, EisenhowerQuadrant


def _effective_quadrant_expression(target: EisenhowerQuadrant):
    """SQL expression matching effective quadrant (manual override wins)."""
    return or_(
        Task.manual_quadrant_override == target,
        and_(
            Task.manual_quadrant_override.is_(None),
            Task.eisenhower_quadrant == target
        )
    )


async def backfill_manual_order():
    """Backfill manual_order for all tasks without it."""
    async with AsyncSessionLocal() as db:
        print("Starting manual_order backfill...")

        # Process each quadrant separately
        quadrants = [EisenhowerQuadrant.Q1, EisenhowerQuadrant.Q2,
                     EisenhowerQuadrant.Q3, EisenhowerQuadrant.Q4]

        total_updated = 0

        for quadrant in quadrants:
            # Get all tasks in this quadrant without manual_order
            query = select(Task).where(
                _effective_quadrant_expression(quadrant),
                Task.manual_order.is_(None)
            ).order_by(Task.created_at.asc())

            result = await db.execute(query)
            tasks = result.scalars().all()

            if not tasks:
                print(f"  {quadrant.value}: No tasks to update")
                continue

            # Assign sequential manual_order starting from 1
            for idx, task in enumerate(tasks, start=1):
                task.manual_order = idx

            await db.commit()
            total_updated += len(tasks)
            print(f"  {quadrant.value}: Updated {len(tasks)} tasks")

        print(f"\nTotal tasks updated: {total_updated}")
        print("Backfill complete!")


if __name__ == "__main__":
    asyncio.run(backfill_manual_order())
