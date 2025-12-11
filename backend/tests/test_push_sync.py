"""
Test suite for bi-directional sync (push to TickTick).

This test file validates:
1. TickTick push methods (update, create, delete)
2. Conflict resolution logic
3. Sync metadata management
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ticktick import TickTickService
from app.services.sync_service import SyncConflictResolver, SyncService
from app.models.task import Task, TaskStatus, EisenhowerQuadrant
from app.models.user import User


class TestTickTickPushMethods:
    """Test TickTick push sync methods"""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user with TickTick credentials"""
        user = User(
            id=1,
            email="test@example.com",
            ticktick_access_token="test_access_token",
            ticktick_refresh_token="test_refresh_token"
        )
        return user

    @pytest.fixture
    def ticktick_service(self, mock_user):
        """Create TickTickService instance with mock user"""
        return TickTickService(user=mock_user)

    @pytest.mark.asyncio
    async def test_update_task_success(self, ticktick_service):
        """Test successful task update to TickTick"""
        task_data = {
            "title": "Updated Task Title",
            "description": "Updated description",
            "ticktick_priority": 5,
        }

        with patch.object(ticktick_service.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "tt_task_123",
                "title": "Updated Task Title",
                "content": "Updated description",
                "priority": 5
            }
            mock_post.return_value = mock_response

            mock_db = AsyncMock()

            result = await ticktick_service.update_task(
                ticktick_task_id="tt_task_123",
                task_data=task_data,
                db=mock_db
            )

            # Verify API was called correctly
            mock_post.assert_called_once()
            assert result["id"] == "tt_task_123"
            assert result["title"] == "Updated Task Title"

    @pytest.mark.asyncio
    async def test_update_task_handles_401_and_refreshes(self, ticktick_service):
        """Test that update_task handles token expiry and refreshes"""
        task_data = {"title": "Test Task"}

        with patch.object(ticktick_service.client, 'post', new_callable=AsyncMock) as mock_post:
            # First call returns 401, second call succeeds
            mock_response_401 = MagicMock()
            mock_response_401.status_code = 401

            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.json.return_value = {"id": "tt_task_123"}

            mock_post.side_effect = [mock_response_401, mock_response_200]

            with patch.object(ticktick_service, 'refresh_user_token', new_callable=AsyncMock) as mock_refresh:
                mock_db = AsyncMock()

                result = await ticktick_service.update_task(
                    ticktick_task_id="tt_task_123",
                    task_data=task_data,
                    db=mock_db
                )

                # Verify token refresh was called
                mock_refresh.assert_called_once_with(mock_db)
                assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_create_task_success(self, ticktick_service):
        """Test successful task creation in TickTick"""
        task_data = {
            "title": "New Task",
            "description": "Task description",
            "ticktick_priority": 3,
        }

        with patch.object(ticktick_service.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "tt_task_new_123",
                "title": "New Task",
                "content": "Task description"
            }
            mock_post.return_value = mock_response

            mock_db = AsyncMock()

            result = await ticktick_service.create_task(task_data=task_data, db=mock_db)

            # Verify API was called correctly
            mock_post.assert_called_once()
            assert result["id"] == "tt_task_new_123"
            assert result["title"] == "New Task"

    @pytest.mark.asyncio
    async def test_delete_task_success(self, ticktick_service):
        """Test successful task deletion from TickTick"""
        with patch.object(ticktick_service.client, 'delete', new_callable=AsyncMock) as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_delete.return_value = mock_response

            mock_db = AsyncMock()

            result = await ticktick_service.delete_task(
                ticktick_task_id="tt_task_123",
                ticktick_project_id="tt_project_456",
                db=mock_db
            )

            # Verify API was called correctly
            mock_delete.assert_called_once()
            assert result is True


class TestSyncConflictResolver:
    """Test conflict resolution logic"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_resolve_conflict_ticktick_newer(self, mock_db):
        """Test conflict resolution when TickTick data is newer"""
        # Create local task with older timestamp
        local_task = Task(
            id=1,
            user_id=1,
            title="Old Title",
            description="Old description",
            ticktick_priority=0,
            last_modified_at=datetime.utcnow() - timedelta(hours=2),
            created_at=datetime.utcnow() - timedelta(days=1)
        )

        # TickTick data with newer timestamp
        ticktick_data = {
            "title": "New Title from TickTick",
            "content": "New description from TickTick",
            "priority": 3,
            "modifiedTime": datetime.utcnow().isoformat() + "+0000"
        }

        resolver = SyncConflictResolver()
        resolved = await resolver.resolve_task_conflict(local_task, ticktick_data, mock_db)

        # TickTick data should win
        assert resolved.title == "New Title from TickTick"
        assert resolved.description == "New description from TickTick"
        assert resolved.ticktick_priority == 3

    @pytest.mark.asyncio
    async def test_resolve_conflict_local_newer(self, mock_db):
        """Test conflict resolution when local data is newer"""
        # Create local task with newer timestamp
        local_task = Task(
            id=1,
            user_id=1,
            title="Recent Local Title",
            description="Recent local description",
            ticktick_priority=5,
            last_modified_at=datetime.utcnow(),
            created_at=datetime.utcnow() - timedelta(days=1)
        )

        # TickTick data with older timestamp
        ticktick_data = {
            "title": "Old Title from TickTick",
            "content": "Old description from TickTick",
            "priority": 3,
            "modifiedTime": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "+0000"
        }

        resolver = SyncConflictResolver()
        resolved = await resolver.resolve_task_conflict(local_task, ticktick_data, mock_db)

        # Local data should win
        assert resolved.title == "Recent Local Title"
        assert resolved.description == "Recent local description"
        assert resolved.ticktick_priority == 5

    @pytest.mark.asyncio
    async def test_resolve_conflict_preserves_manual_overrides(self, mock_db):
        """Test that manual overrides are preserved during conflict resolution"""
        # Create local task with manual quadrant override
        local_task = Task(
            id=1,
            user_id=1,
            title="Task with override",
            eisenhower_quadrant=EisenhowerQuadrant.Q2,
            urgency_score=5.0,
            importance_score=8.0,
            manual_quadrant_override=EisenhowerQuadrant.Q1,  # Manual override
            last_modified_at=datetime.utcnow() - timedelta(hours=2),
            created_at=datetime.utcnow() - timedelta(days=1)
        )

        # TickTick data tries to change quadrant-related fields
        ticktick_data = {
            "title": "Updated Title",
            "modifiedTime": datetime.utcnow().isoformat() + "+0000"
        }

        resolver = SyncConflictResolver()
        resolved = await resolver.resolve_task_conflict(local_task, ticktick_data, mock_db)

        # Manual override should be preserved
        assert resolved.manual_quadrant_override == EisenhowerQuadrant.Q1
        # Title should update (not protected)
        assert resolved.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_should_sync_to_ticktick(self):
        """Test logic for determining if task should sync to TickTick"""
        resolver = SyncConflictResolver()

        # Task without TickTick ID should not sync
        task_no_id = Task(id=1, user_id=1, title="Local only")
        assert not await resolver.should_sync_to_ticktick(task_no_id)

        # Deleted task should not sync
        task_deleted = Task(
            id=2,
            user_id=1,
            title="Deleted",
            ticktick_task_id="tt_123",
            status=TaskStatus.DELETED
        )
        assert not await resolver.should_sync_to_ticktick(task_deleted)

        # Task with TickTick ID and recent changes should sync
        task_needs_sync = Task(
            id=3,
            user_id=1,
            title="Needs sync",
            ticktick_task_id="tt_456",
            status=TaskStatus.ACTIVE,
            last_modified_at=datetime.utcnow(),
            last_synced_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert await resolver.should_sync_to_ticktick(task_needs_sync)


class TestSyncService:
    """Test sync service functionality"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def sync_service(self, mock_db):
        """Create SyncService instance"""
        return SyncService(db=mock_db)

    def test_get_sync_status(self, sync_service):
        """Test sync status reporting"""
        # Task with pending changes
        task_pending = Task(
            id=1,
            user_id=1,
            title="Test",
            ticktick_task_id="tt_123",
            last_modified_at=datetime.utcnow(),
            last_synced_at=datetime.utcnow() - timedelta(hours=1),
            sync_version=2
        )

        status = sync_service.resolver.get_sync_status(task_pending)
        assert status["synced_to_ticktick"] is True
        assert status["has_pending_changes"] is True
        assert status["sync_version"] == 2

        # Task fully synced
        now = datetime.utcnow()
        task_synced = Task(
            id=2,
            user_id=1,
            title="Test",
            ticktick_task_id="tt_456",
            last_modified_at=now,
            last_synced_at=now,
            sync_version=1
        )

        status = sync_service.resolver.get_sync_status(task_synced)
        assert status["synced_to_ticktick"] is True
        assert status["has_pending_changes"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
