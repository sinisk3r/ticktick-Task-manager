"""
Sync service for handling bi-directional synchronization between Context and TickTick.

This service handles:
1. Conflict resolution when tasks exist in both systems
2. Sync metadata management
3. Manual override preservation
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task import Task, EisenhowerQuadrant
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SyncConflictResolver:
    """Handles sync conflicts between local and TickTick tasks"""

    @staticmethod
    async def resolve_task_conflict(
        local_task: Task,
        ticktick_data: dict,
        db: AsyncSession
    ) -> Task:
        """
        Resolve conflicts when task exists both locally and in TickTick.

        Rules:
        1. Manual user overrides always win (protected fields)
        2. For non-override fields, use timestamps to determine which is newer
        3. Last write wins if versions are equal

        Args:
            local_task: Task from local database
            ticktick_data: Task data from TickTick API
            db: Database session

        Returns:
            Resolved Task object with merged data
        """
        # Rule 1: Preserve manual overrides
        protected_fields = []
        if local_task.manual_quadrant_override:
            protected_fields.extend(["eisenhower_quadrant", "urgency_score", "importance_score"])
            logger.info(f"Task {local_task.id}: Manual quadrant override in place, protecting quadrant fields")

        if local_task.manual_priority_override:
            protected_fields.append("ticktick_priority")
            logger.info(f"Task {local_task.id}: Manual priority override in place, protecting priority field")

        # Rule 2: Check timestamps for non-protected fields
        local_modified = local_task.last_modified_at or local_task.created_at
        ticktick_modified = None

        # Parse TickTick timestamp
        if ticktick_data.get("modifiedTime"):
            try:
                # TickTick returns timestamps like "2023-12-11T10:30:00.000+0000"
                mod_time_str = ticktick_data["modifiedTime"]
                # Remove 'Z' and handle different timezone formats
                mod_time_str = mod_time_str.replace('Z', '+00:00')
                # Handle +0000 format
                if '+0000' in mod_time_str:
                    mod_time_str = mod_time_str.replace('+0000', '+00:00')
                ticktick_modified = datetime.fromisoformat(mod_time_str)
                # Make timezone-naive to match local_modified
                ticktick_modified = ticktick_modified.replace(tzinfo=None)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse TickTick modifiedTime: {e}")

        # Determine which source is newer
        if ticktick_modified and local_modified:
            use_ticktick = ticktick_modified > local_modified
            logger.info(
                f"Task {local_task.id}: Local modified={local_modified.isoformat()}, "
                f"TickTick modified={ticktick_modified.isoformat()}, using={'TickTick' if use_ticktick else 'local'}"
            )
        else:
            use_ticktick = True  # Default to TickTick if timestamps unclear
            logger.info(f"Task {local_task.id}: Timestamps unclear, defaulting to TickTick data")

        # Apply non-protected changes
        if use_ticktick:
            logger.info(f"Task {local_task.id}: TickTick data is newer, updating non-protected fields")

            # Map TickTick fields to local task
            field_mappings = {
                "title": "title",
                "content": "description",
                "priority": "ticktick_priority",
                "dueDate": "due_date",
                "startDate": "start_date",
                "tags": "ticktick_tags",
                "isAllDay": "all_day",
                "status": "status",
                "projectId": "ticktick_project_id"
            }

            updated_fields = []
            for tt_field, local_field in field_mappings.items():
                if local_field not in protected_fields and tt_field in ticktick_data:
                    value = ticktick_data[tt_field]

                    # Convert date strings to datetime
                    if local_field in ["due_date", "start_date"] and value:
                        try:
                            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to parse {tt_field}: {e}")
                            continue

                    # Convert status (TickTick: 0=incomplete, 2=complete)
                    if local_field == "status":
                        from app.models.task import TaskStatus
                        value = TaskStatus.COMPLETED if value == 2 else TaskStatus.ACTIVE

                    # Only update if value changed
                    old_value = getattr(local_task, local_field)
                    if old_value != value:
                        setattr(local_task, local_field, value)
                        updated_fields.append(local_field)

            if updated_fields:
                logger.info(f"Task {local_task.id}: Updated fields from TickTick: {updated_fields}")

            local_task.last_synced_at = datetime.utcnow()
        else:
            logger.info(f"Task {local_task.id}: Local data is newer, keeping local changes")

        return local_task

    @staticmethod
    async def should_sync_to_ticktick(task: Task) -> bool:
        """
        Determine if a task should be synced to TickTick.

        Args:
            task: Task object to check

        Returns:
            True if task should be synced to TickTick, False otherwise
        """
        # Don't sync if task doesn't have a TickTick task ID
        if not task.ticktick_task_id:
            return False

        # Don't sync deleted tasks (they should be handled separately)
        from app.models.task import TaskStatus
        if task.status == TaskStatus.DELETED:
            return False

        # Check if local changes are newer than last sync
        if task.last_synced_at and task.last_modified_at:
            return task.last_modified_at > task.last_synced_at

        # If no sync timestamp, sync by default
        return True

    @staticmethod
    def get_sync_status(task: Task) -> dict:
        """
        Get sync status information for a task.

        Args:
            task: Task object

        Returns:
            Dictionary with sync status information
        """
        status = {
            "synced_to_ticktick": bool(task.ticktick_task_id),
            "last_synced_at": task.last_synced_at.isoformat() if task.last_synced_at else None,
            "last_modified_at": task.last_modified_at.isoformat() if task.last_modified_at else None,
            "sync_version": task.sync_version,
            "has_pending_changes": False
        }

        # Check if there are pending changes
        if task.last_modified_at and task.last_synced_at:
            status["has_pending_changes"] = task.last_modified_at > task.last_synced_at
        elif task.last_modified_at and not task.last_synced_at:
            status["has_pending_changes"] = True

        return status


class SyncService:
    """Service for managing bi-directional sync between Context and TickTick"""

    def __init__(self, db: AsyncSession):
        """
        Initialize sync service.

        Args:
            db: Database session
        """
        self.db = db
        self.resolver = SyncConflictResolver()

    async def sync_task_from_ticktick(
        self,
        local_task: Task,
        ticktick_data: dict
    ) -> Task:
        """
        Sync a task from TickTick to local database.

        Args:
            local_task: Existing local task (or None for new task)
            ticktick_data: Task data from TickTick API

        Returns:
            Updated or created Task object
        """
        if local_task:
            # Existing task - resolve conflicts
            logger.info(f"Resolving conflicts for existing task {local_task.id}")
            resolved_task = await self.resolver.resolve_task_conflict(
                local_task,
                ticktick_data,
                self.db
            )
            return resolved_task
        else:
            # New task - create from TickTick data
            logger.info(f"Creating new task from TickTick: {ticktick_data.get('title', 'Untitled')}")
            # This would be handled by the sync endpoint
            return None

    async def get_tasks_needing_sync(self, user_id: int) -> list[Task]:
        """
        Get all tasks that need to be synced to TickTick.

        Args:
            user_id: User ID to filter tasks

        Returns:
            List of Task objects that need sync
        """
        from sqlalchemy import select, and_, or_
        from app.models.task import TaskStatus

        # Query tasks that:
        # 1. Have a TickTick task ID
        # 2. Are not deleted
        # 3. Have been modified since last sync OR never synced
        query = select(Task).where(
            and_(
                Task.user_id == user_id,
                Task.ticktick_task_id.isnot(None),
                Task.status != TaskStatus.DELETED,
                or_(
                    Task.last_synced_at.is_(None),
                    Task.last_modified_at > Task.last_synced_at
                )
            )
        )

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        logger.info(f"Found {len(tasks)} tasks needing sync for user {user_id}")
        return tasks
