"""
Tests for Suggestion API endpoints (Phase 5).

Tests all 5 suggestion endpoints:
1. POST /api/tasks/{task_id}/analyze - Generate suggestions
2. POST /api/tasks/analyze/batch - Batch generate suggestions
3. GET /api/tasks/{task_id}/suggestions - Get pending suggestions
4. POST /api/tasks/{task_id}/suggestions/approve - Approve suggestions
5. POST /api/tasks/{task_id}/suggestions/reject - Reject suggestions
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.task import Task, TaskStatus, EisenhowerQuadrant
from app.models.project import Project
from app.models.task_suggestion import TaskSuggestion, SuggestionStatus


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user = User(
        email="test@example.com",
        name="Test User",
        ticktick_access_token="test_token"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_project(db_session: AsyncSession, test_user: User):
    """Create a test project."""
    project = Project(
        user_id=test_user.id,
        name="Test Project",
        ticktick_project_id="test_proj_123"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_task(db_session: AsyncSession, test_user: User, test_project: Project):
    """Create a test task with full metadata."""
    task = Task(
        user_id=test_user.id,
        project_id=test_project.id,
        title="Complete quarterly report",
        description="Finish Q4 financial report and submit to management by end of week",
        status=TaskStatus.ACTIVE,
        due_date=datetime.utcnow() + timedelta(days=3),
        ticktick_task_id="task_123",
        ticktick_project_id="test_proj_123",
        ticktick_priority=0,  # No priority set
        ticktick_tags=["work"],
        is_sorted=False
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.fixture
async def test_task_with_suggestions(db_session: AsyncSession, test_task: Task):
    """Create a task with pending suggestions."""
    suggestions = [
        TaskSuggestion(
            task_id=test_task.id,
            suggestion_type="priority",
            current_value=0,
            suggested_value=5,
            reason="Task is urgent and important",
            confidence=0.9,
            status=SuggestionStatus.PENDING
        ),
        TaskSuggestion(
            task_id=test_task.id,
            suggestion_type="tags",
            current_value=["work"],
            suggested_value=["work", "urgent", "finance"],
            reason="Add tags for better organization",
            confidence=0.85,
            status=SuggestionStatus.PENDING
        ),
        TaskSuggestion(
            task_id=test_task.id,
            suggestion_type="quadrant",
            current_value=None,
            suggested_value="Q1",
            reason="High urgency and importance",
            confidence=0.95,
            status=SuggestionStatus.PENDING
        )
    ]

    for suggestion in suggestions:
        db_session.add(suggestion)

    await db_session.commit()

    return test_task


class TestAnalyzeTaskEndpoint:
    """Tests for POST /api/tasks/{task_id}/analyze"""

    @pytest.mark.asyncio
    async def test_analyze_task_success(
        self,
        client: AsyncClient,
        test_task: Task,
        test_user: User,
        db_session: AsyncSession,
        monkeypatch
    ):
        """Test successful task analysis."""
        # Mock LLM service response
        mock_suggestions = {
            "analysis": {
                "urgency": 8,
                "importance": 7,
                "quadrant": "Q1",
                "reasoning": "Urgent deadline with high business impact"
            },
            "suggestions": [
                {
                    "type": "priority",
                    "current": 0,
                    "suggested": 5,
                    "reason": "Task is urgent and important",
                    "confidence": 0.9
                },
                {
                    "type": "quadrant",
                    "current": None,
                    "suggested": "Q1",
                    "reason": "High urgency and importance",
                    "confidence": 0.95
                }
            ]
        }

        async def mock_generate_suggestions(*args, **kwargs):
            return mock_suggestions

        from app.services import llm_ollama
        monkeypatch.setattr(
            llm_ollama.OllamaService,
            "generate_suggestions",
            mock_generate_suggestions
        )

        # Call analyze endpoint
        response = await client.post(
            f"/api/tasks/{test_task.id}/analyze?user_id={test_user.id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == test_task.id
        assert "analysis" in data
        assert "suggestions" in data
        assert len(data["suggestions"]) == 2

        # Verify suggestions stored in database
        stmt = select(TaskSuggestion).where(
            TaskSuggestion.task_id == test_task.id,
            TaskSuggestion.status == SuggestionStatus.PENDING
        )
        result = await db_session.execute(stmt)
        suggestions = result.scalars().all()
        assert len(suggestions) == 2

    @pytest.mark.asyncio
    async def test_analyze_task_not_found(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test analysis of non-existent task."""
        response = await client.post(
            f"/api/tasks/99999/analyze?user_id={test_user.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_analyze_task_llm_failure(
        self,
        client: AsyncClient,
        test_task: Task,
        test_user: User,
        monkeypatch
    ):
        """Test handling of LLM service failure."""
        async def mock_generate_suggestions_fail(*args, **kwargs):
            raise Exception("LLM service unavailable")

        from app.services import llm_ollama
        monkeypatch.setattr(
            llm_ollama.OllamaService,
            "generate_suggestions",
            mock_generate_suggestions_fail
        )

        response = await client.post(
            f"/api/tasks/{test_task.id}/analyze?user_id={test_user.id}"
        )
        assert response.status_code == 500
        assert "Analysis failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_analyze_task_replaces_old_suggestions(
        self,
        client: AsyncClient,
        test_task_with_suggestions: Task,
        test_user: User,
        db_session: AsyncSession,
        monkeypatch
    ):
        """Test that new analysis replaces old pending suggestions."""
        # Count initial suggestions
        stmt = select(TaskSuggestion).where(
            TaskSuggestion.task_id == test_task_with_suggestions.id,
            TaskSuggestion.status == SuggestionStatus.PENDING
        )
        result = await db_session.execute(stmt)
        initial_suggestions = result.scalars().all()
        assert len(initial_suggestions) == 3

        # Mock new suggestions
        mock_suggestions = {
            "analysis": {"urgency": 9, "importance": 8, "quadrant": "Q1"},
            "suggestions": [
                {
                    "type": "priority",
                    "current": 0,
                    "suggested": 5,
                    "reason": "Updated analysis",
                    "confidence": 0.92
                }
            ]
        }

        async def mock_generate_suggestions(*args, **kwargs):
            return mock_suggestions

        from app.services import llm_ollama
        monkeypatch.setattr(
            llm_ollama.OllamaService,
            "generate_suggestions",
            mock_generate_suggestions
        )

        # Re-analyze
        response = await client.post(
            f"/api/tasks/{test_task_with_suggestions.id}/analyze?user_id={test_user.id}"
        )
        assert response.status_code == 200

        # Verify old suggestions deleted, new ones added
        result = await db_session.execute(stmt)
        new_suggestions = result.scalars().all()
        assert len(new_suggestions) == 1
        assert new_suggestions[0].reason == "Updated analysis"


class TestBatchAnalyzeEndpoint:
    """Tests for POST /api/tasks/analyze/batch"""

    @pytest.mark.asyncio
    async def test_batch_analyze_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_project: Project,
        monkeypatch
    ):
        """Test successful batch analysis."""
        # Create multiple tasks
        tasks = []
        for i in range(3):
            task = Task(
                user_id=test_user.id,
                project_id=test_project.id,
                title=f"Task {i+1}",
                description=f"Description {i+1}",
                status=TaskStatus.ACTIVE
            )
            db_session.add(task)
            tasks.append(task)

        await db_session.commit()
        for task in tasks:
            await db_session.refresh(task)

        # Mock LLM service
        mock_suggestions = {
            "analysis": {"urgency": 7, "importance": 6, "quadrant": "Q2"},
            "suggestions": [
                {
                    "type": "priority",
                    "current": 0,
                    "suggested": 3,
                    "reason": "Medium priority",
                    "confidence": 0.8
                }
            ]
        }

        async def mock_generate_suggestions(*args, **kwargs):
            return mock_suggestions

        from app.services import llm_ollama
        monkeypatch.setattr(
            llm_ollama.OllamaService,
            "generate_suggestions",
            mock_generate_suggestions
        )

        # Batch analyze
        task_ids = [task.id for task in tasks]
        response = await client.post(
            f"/api/tasks/analyze/batch?user_id={test_user.id}",
            json={"task_ids": task_ids}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert data["successful"] == 3
        assert data["failed"] == 0
        assert len(data["results"]) == 3

    @pytest.mark.asyncio
    async def test_batch_analyze_partial_failure(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_project: Project,
        monkeypatch
    ):
        """Test batch analysis with some tasks failing."""
        # Create one valid task
        task = Task(
            user_id=test_user.id,
            project_id=test_project.id,
            title="Valid Task",
            description="Valid description",
            status=TaskStatus.ACTIVE
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Mock LLM service
        mock_suggestions = {
            "analysis": {"urgency": 7, "importance": 6, "quadrant": "Q2"},
            "suggestions": []
        }

        async def mock_generate_suggestions(*args, **kwargs):
            return mock_suggestions

        from app.services import llm_ollama
        monkeypatch.setattr(
            llm_ollama.OllamaService,
            "generate_suggestions",
            mock_generate_suggestions
        )

        # Batch analyze with one invalid task ID
        task_ids = [task.id, 99999]
        response = await client.post(
            f"/api/tasks/analyze/batch?user_id={test_user.id}",
            json={"task_ids": task_ids}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert data["successful"] == 1
        assert data["failed"] == 1


class TestGetSuggestionsEndpoint:
    """Tests for GET /api/tasks/{task_id}/suggestions"""

    @pytest.mark.asyncio
    async def test_get_suggestions_success(
        self,
        client: AsyncClient,
        test_task_with_suggestions: Task,
        test_user: User
    ):
        """Test retrieving pending suggestions."""
        response = await client.get(
            f"/api/tasks/{test_task_with_suggestions.id}/suggestions?user_id={test_user.id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == test_task_with_suggestions.id
        assert len(data["suggestions"]) == 3

        # Verify suggestion structure
        suggestion = data["suggestions"][0]
        assert "id" in suggestion
        assert "type" in suggestion
        assert "current" in suggestion
        assert "suggested" in suggestion
        assert "reason" in suggestion
        assert "confidence" in suggestion
        assert "created_at" in suggestion

    @pytest.mark.asyncio
    async def test_get_suggestions_empty(
        self,
        client: AsyncClient,
        test_task: Task,
        test_user: User
    ):
        """Test retrieving suggestions for task with none."""
        response = await client.get(
            f"/api/tasks/{test_task.id}/suggestions?user_id={test_user.id}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == test_task.id
        assert len(data["suggestions"]) == 0

    @pytest.mark.asyncio
    async def test_get_suggestions_task_not_found(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test retrieving suggestions for non-existent task."""
        response = await client.get(
            f"/api/tasks/99999/suggestions?user_id={test_user.id}"
        )
        assert response.status_code == 404


class TestApproveSuggestionsEndpoint:
    """Tests for POST /api/tasks/{task_id}/suggestions/approve"""

    @pytest.mark.asyncio
    async def test_approve_specific_suggestions(
        self,
        client: AsyncClient,
        test_task_with_suggestions: Task,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test approving specific suggestion types."""
        response = await client.post(
            f"/api/tasks/{test_task_with_suggestions.id}/suggestions/approve?user_id={test_user.id}",
            json={"suggestion_types": ["priority", "tags"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == test_task_with_suggestions.id
        assert data["approved_count"] == 2
        assert "priority" in data["approved_types"]
        assert "tags" in data["approved_types"]

        # Verify task updated
        await db_session.refresh(test_task_with_suggestions)
        assert test_task_with_suggestions.ticktick_priority == 5
        assert "urgent" in test_task_with_suggestions.ticktick_tags

        # Verify suggestions marked as approved
        stmt = select(TaskSuggestion).where(
            TaskSuggestion.task_id == test_task_with_suggestions.id,
            TaskSuggestion.suggestion_type.in_(["priority", "tags"])
        )
        result = await db_session.execute(stmt)
        suggestions = result.scalars().all()

        for suggestion in suggestions:
            assert suggestion.status == SuggestionStatus.APPROVED
            assert suggestion.resolved_at is not None
            assert suggestion.resolved_by_user is True

    @pytest.mark.asyncio
    async def test_approve_all_suggestions(
        self,
        client: AsyncClient,
        test_task_with_suggestions: Task,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test approving all suggestions."""
        response = await client.post(
            f"/api/tasks/{test_task_with_suggestions.id}/suggestions/approve?user_id={test_user.id}",
            json={"suggestion_types": ["all"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["approved_count"] == 3

        # Verify task updated with quadrant suggestion
        await db_session.refresh(test_task_with_suggestions)
        assert test_task_with_suggestions.eisenhower_quadrant == EisenhowerQuadrant.Q1
        assert test_task_with_suggestions.is_sorted is True

    @pytest.mark.asyncio
    async def test_approve_no_pending_suggestions(
        self,
        client: AsyncClient,
        test_task: Task,
        test_user: User
    ):
        """Test approving when no pending suggestions exist."""
        response = await client.post(
            f"/api/tasks/{test_task.id}/suggestions/approve?user_id={test_user.id}",
            json={"suggestion_types": ["priority"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "No pending suggestions to approve"

    @pytest.mark.asyncio
    async def test_approve_start_date_suggestion(
        self,
        client: AsyncClient,
        test_task: Task,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test approving start_date suggestion."""
        # Create start_date suggestion
        suggestion = TaskSuggestion(
            task_id=test_task.id,
            suggestion_type="start_date",
            current_value=None,
            suggested_value=(datetime.utcnow() + timedelta(days=1)).isoformat(),
            reason="Start tomorrow",
            confidence=0.8,
            status=SuggestionStatus.PENDING
        )
        db_session.add(suggestion)
        await db_session.commit()

        response = await client.post(
            f"/api/tasks/{test_task.id}/suggestions/approve?user_id={test_user.id}",
            json={"suggestion_types": ["start_date"]}
        )

        assert response.status_code == 200

        # Verify start_date updated
        await db_session.refresh(test_task)
        assert test_task.start_date is not None


class TestRejectSuggestionsEndpoint:
    """Tests for POST /api/tasks/{task_id}/suggestions/reject"""

    @pytest.mark.asyncio
    async def test_reject_specific_suggestions(
        self,
        client: AsyncClient,
        test_task_with_suggestions: Task,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test rejecting specific suggestion types."""
        response = await client.post(
            f"/api/tasks/{test_task_with_suggestions.id}/suggestions/reject?user_id={test_user.id}",
            json={"suggestion_types": ["priority"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["task_id"] == test_task_with_suggestions.id
        assert data["rejected_count"] == 1
        assert "priority" in data["rejected_types"]

        # Verify task NOT updated (rejection doesn't apply changes)
        await db_session.refresh(test_task_with_suggestions)
        assert test_task_with_suggestions.ticktick_priority == 0

        # Verify suggestion marked as rejected
        stmt = select(TaskSuggestion).where(
            TaskSuggestion.task_id == test_task_with_suggestions.id,
            TaskSuggestion.suggestion_type == "priority"
        )
        result = await db_session.execute(stmt)
        suggestion = result.scalar_one()

        assert suggestion.status == SuggestionStatus.REJECTED
        assert suggestion.resolved_at is not None
        assert suggestion.resolved_by_user is True

    @pytest.mark.asyncio
    async def test_reject_all_suggestions(
        self,
        client: AsyncClient,
        test_task_with_suggestions: Task,
        test_user: User,
        db_session: AsyncSession
    ):
        """Test rejecting all suggestions."""
        response = await client.post(
            f"/api/tasks/{test_task_with_suggestions.id}/suggestions/reject?user_id={test_user.id}",
            json={"suggestion_types": ["all"]}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["rejected_count"] == 3

        # Verify all suggestions rejected
        stmt = select(TaskSuggestion).where(
            TaskSuggestion.task_id == test_task_with_suggestions.id,
            TaskSuggestion.status == SuggestionStatus.REJECTED
        )
        result = await db_session.execute(stmt)
        rejected_suggestions = result.scalars().all()
        assert len(rejected_suggestions) == 3

    @pytest.mark.asyncio
    async def test_reject_no_pending_suggestions(
        self,
        client: AsyncClient,
        test_task: Task,
        test_user: User
    ):
        """Test rejecting when no pending suggestions exist."""
        response = await client.post(
            f"/api/tasks/{test_task.id}/suggestions/reject?user_id={test_user.id}",
            json={"suggestion_types": ["tags"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "No pending suggestions to reject"


class TestSuggestionWorkflow:
    """Integration tests for full suggestion workflow."""

    @pytest.mark.asyncio
    async def test_full_suggestion_workflow(
        self,
        client: AsyncClient,
        test_task: Task,
        test_user: User,
        db_session: AsyncSession,
        monkeypatch
    ):
        """Test complete workflow: analyze → get → approve → verify."""
        # Step 1: Analyze task
        mock_suggestions = {
            "analysis": {"urgency": 8, "importance": 7, "quadrant": "Q1"},
            "suggestions": [
                {
                    "type": "priority",
                    "current": 0,
                    "suggested": 5,
                    "reason": "High priority task",
                    "confidence": 0.9
                },
                {
                    "type": "quadrant",
                    "current": None,
                    "suggested": "Q1",
                    "reason": "Urgent and important",
                    "confidence": 0.95
                }
            ]
        }

        async def mock_generate_suggestions(*args, **kwargs):
            return mock_suggestions

        from app.services import llm_ollama
        monkeypatch.setattr(
            llm_ollama.OllamaService,
            "generate_suggestions",
            mock_generate_suggestions
        )

        analyze_response = await client.post(
            f"/api/tasks/{test_task.id}/analyze?user_id={test_user.id}"
        )
        assert analyze_response.status_code == 200

        # Step 2: Get suggestions
        get_response = await client.get(
            f"/api/tasks/{test_task.id}/suggestions?user_id={test_user.id}"
        )
        assert get_response.status_code == 200
        suggestions = get_response.json()["suggestions"]
        assert len(suggestions) == 2

        # Step 3: Approve priority suggestion, reject quadrant
        approve_response = await client.post(
            f"/api/tasks/{test_task.id}/suggestions/approve?user_id={test_user.id}",
            json={"suggestion_types": ["priority"]}
        )
        assert approve_response.status_code == 200

        reject_response = await client.post(
            f"/api/tasks/{test_task.id}/suggestions/reject?user_id={test_user.id}",
            json={"suggestion_types": ["quadrant"]}
        )
        assert reject_response.status_code == 200

        # Step 4: Verify no pending suggestions remain
        final_response = await client.get(
            f"/api/tasks/{test_task.id}/suggestions?user_id={test_user.id}"
        )
        assert len(final_response.json()["suggestions"]) == 0

        # Step 5: Verify task updated correctly
        await db_session.refresh(test_task)
        assert test_task.ticktick_priority == 5
        assert test_task.eisenhower_quadrant is None  # Rejected suggestion not applied
