"""
Script to delete all tasks from the database.
Run this before re-syncing with TickTick to pull complete data.
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.task import Task


async def delete_all_tasks():
    """Delete all tasks from the database."""
    async with AsyncSessionLocal() as session:
        try:
            # First, get count of tasks to delete
            result = await session.execute(select(Task))
            tasks = result.scalars().all()
            task_count = len(tasks)

            print(f"Found {task_count} tasks to delete")

            if task_count == 0:
                print("No tasks to delete. Database is already clean.")
                return

            # Confirm deletion
            print("\nThis will delete all tasks from the database.")
            confirmation = input("Are you sure you want to continue? (yes/no): ")

            if confirmation.lower() != "yes":
                print("Deletion cancelled.")
                return

            # Delete all tasks
            await session.execute(delete(Task))
            await session.commit()

            print(f"\n✓ Successfully deleted {task_count} tasks from the database.")
            print("You can now re-sync with TickTick to pull complete task data.")

        except Exception as e:
            await session.rollback()
            print(f"Error deleting tasks: {e}")
            raise


async def main():
    """Main entry point."""
    print("=" * 60)
    print("DELETE ALL TASKS - Database Cleanup Script")
    print("=" * 60)
    print()

    await delete_all_tasks()


if __name__ == "__main__":
    asyncio.run(main())
