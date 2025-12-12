"""
TickTick API service for OAuth authentication and task synchronization.

This service handles:
1. OAuth2 authorization flow (authorize URL generation, token exchange, refresh)
2. Task fetching from TickTick API
3. Token management and storage
4. Bi-directional sync (push updates to TickTick)
"""
import httpx
import logging
import ssl
import certifi
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# SSL verification setting for TickTick API
# NOTE: Temporarily disabled due to macOS SSL certificate issues
# TODO: Re-enable once proper certificate configuration is resolved
_SSL_VERIFY = False  # Set to False to disable SSL verification (development only)


class TickTickService:
    """TickTick API client for OAuth and task management."""

    # TickTick OAuth endpoints
    AUTHORIZE_URL = "https://ticktick.com/oauth/authorize"
    TOKEN_URL = "https://ticktick.com/oauth/token"
    API_BASE_URL = "https://api.ticktick.com/open/v1"

    # OAuth scope
    SCOPE = "tasks:read tasks:write"

    def __init__(self, user: Optional[User] = None):
        """
        Initialize TickTick service with configuration.

        Args:
            user: Optional User object for authenticated API calls
        """
        self.client_id = settings.ticktick_client_id
        self.client_secret = settings.ticktick_client_secret
        self.redirect_uri = settings.ticktick_redirect_uri
        self.user = user
        self.base_url = self.API_BASE_URL
        # Create client with SSL verification disabled (temporary workaround)
        self.client = httpx.AsyncClient(verify=_SSL_VERIFY)

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate TickTick OAuth authorization URL for user to visit.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Complete authorization URL
        """
        params = {
            "client_id": self.client_id,
            "scope": self.SCOPE,
            "state": state or "none",
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code_for_token(
        self,
        code: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access/refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            db: Database session for storing tokens

        Returns:
            Dictionary with token information:
            {
                "access_token": str,
                "token_type": str,
                "expires_in": int,
                "refresh_token": str,
                "scope": str
            }

        Raises:
            httpx.HTTPError: If token exchange fails
        """
        async with httpx.AsyncClient(verify=_SSL_VERIFY) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "scope": self.SCOPE,
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(
        self,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh an expired access token using refresh token.

        Args:
            refresh_token: The refresh token from previous authentication

        Returns:
            Dictionary with new token information

        Raises:
            httpx.HTTPError: If token refresh fails
        """
        async with httpx.AsyncClient(verify=_SSL_VERIFY) as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                    "scope": self.SCOPE,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def store_tokens(
        self,
        db: AsyncSession,
        user_id: int,
        token_data: Dict[str, Any]
    ) -> User:
        """
        Store TickTick OAuth tokens in database for a user.

        Args:
            db: Database session
            user_id: User ID to store tokens for
            token_data: Token response from TickTick

        Returns:
            Updated User object
        """
        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            # Create new user if doesn't exist
            # Use a default email for now (will be updated with real email if available)
            user = User(
                id=user_id,
                email=f"user{user_id}@ticktick.local",  # Default email
                ticktick_access_token=token_data["access_token"],
                ticktick_refresh_token=token_data.get("refresh_token"),
                ticktick_user_id=None,  # Will be populated on first sync
            )
            db.add(user)
        else:
            # Update existing user
            user.ticktick_access_token = token_data["access_token"]
            user.ticktick_refresh_token = token_data.get("refresh_token")

        await db.commit()
        await db.refresh(user)
        return user

    async def get_projects(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Fetch all projects from TickTick API.

        Args:
            access_token: Valid TickTick access token

        Returns:
            List of project dictionaries

        Raises:
            httpx.HTTPError: If API request fails
        """
        async with httpx.AsyncClient(verify=_SSL_VERIFY) as client:
            response = await client.get(
                f"{self.API_BASE_URL}/project",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def get_project_data(
        self,
        access_token: str,
        project_id: str
    ) -> Dict[str, Any]:
        """
        Fetch project data including tasks from TickTick API.

        Args:
            access_token: Valid TickTick access token
            project_id: TickTick project ID

        Returns:
            Project data dictionary with tasks

        Raises:
            httpx.HTTPError: If API request fails
        """
        async with httpx.AsyncClient(verify=_SSL_VERIFY) as client:
            response = await client.get(
                f"{self.API_BASE_URL}/project/{project_id}/data",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    def _parse_datetime(self, iso_string: Optional[str]) -> Optional[Any]:
        """
        Convert ISO datetime string to datetime object.

        Args:
            iso_string: ISO 8601 datetime string

        Returns:
            datetime object or None if invalid/empty
        """
        from datetime import datetime as dt

        if not iso_string:
            return None
        try:
            # Handle both 'Z' and '+00:00' timezone formats
            cleaned = iso_string.replace('Z', '+00:00')
            return dt.fromisoformat(cleaned)
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{iso_string}': {e}")
            return None

    def _calculate_time_estimate(self, pomodoro_summaries: list) -> Optional[int]:
        """
        Calculate total estimated time in minutes from Pomodoro summaries.

        Args:
            pomodoro_summaries: List of Pomodoro summary dictionaries

        Returns:
            Total minutes or None if no estimate
        """
        if not pomodoro_summaries:
            return None
        total_minutes = sum(
            summary.get("estimatedPomo", 0) * 25
            for summary in pomodoro_summaries
        )
        return total_minutes if total_minutes > 0 else None

    def _calculate_focus_time(self, focus_summaries: list) -> Optional[int]:
        """
        Calculate total focus time in minutes.

        Args:
            focus_summaries: List of focus summary dictionaries

        Returns:
            Total minutes or None if no focus time
        """
        if not focus_summaries:
            return None
        total_minutes = sum(
            summary.get("focusTime", 0) // 60  # Convert seconds to minutes
            for summary in focus_summaries
        )
        return total_minutes if total_minutes > 0 else None

    async def get_tasks(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Fetch all tasks from TickTick API with COMPLETE metadata.

        This method:
        1. Fetches all projects
        2. For each project, fetches project data with tasks
        3. Extracts comprehensive metadata from each task
        4. Returns consolidated list ready for database insertion

        Args:
            access_token: Valid TickTick access token

        Returns:
            List of task dictionaries with comprehensive metadata including:
            - Basic: ticktick_task_id, title, description, status
            - Project: ticktick_project_id, project_name
            - Priority: ticktick_priority (0/1/3/5)
            - Dates: due_date, start_date, all_day
            - Reminders: reminder_time
            - Recurrence: repeat_flag
            - Organization: parent_task_id, sort_order, column_id
            - Tags: ticktick_tags
            - Time: time_estimate, focus_time

        Raises:
            httpx.HTTPError: If API request fails
        """
        all_tasks = []

        # Get all projects
        projects = await self.get_projects(access_token)

        # Fetch tasks from each project
        for project in projects:
            try:
                project_id = project.get("id")
                project_name = project.get("name")

                project_data = await self.get_project_data(
                    access_token,
                    project_id
                )

                # Extract tasks from project data with full metadata
                for task_json in project_data.get("tasks", []):
                    # Extract COMPLETE metadata
                    task_data = {
                        # Core fields
                        "ticktick_task_id": task_json.get("id"),
                        "title": task_json.get("title", "Untitled"),
                        "description": task_json.get("content", ""),
                        "ticktick_project_id": project_id,
                        "project_name": project_name,
                        "status": "completed" if task_json.get("status") == 2 else "active",

                        # TickTick Priority (0=None, 1=Low, 3=Medium, 5=High)
                        "ticktick_priority": task_json.get("priority", 0),

                        # Dates (ISO format)
                        "due_date": self._parse_datetime(task_json.get("dueDate")),
                        "start_date": self._parse_datetime(task_json.get("startDate")),

                        # All-day flag
                        "all_day": task_json.get("isAllDay", False),

                        # Reminders (take first reminder if exists)
                        "reminder_time": self._parse_datetime(
                            task_json.get("reminders", [{}])[0].get("trigger")
                        ) if task_json.get("reminders") else None,

                        # Recurrence
                        "repeat_flag": task_json.get("repeatFlag"),

                        # Organization
                        "parent_task_id": task_json.get("parentId"),
                        "sort_order": task_json.get("sortOrder", 0),
                        "column_id": task_json.get("columnId"),

                        # Tags (TickTick native tags)
                        "ticktick_tags": task_json.get("tags", []),

                        # Time tracking
                        "time_estimate": self._calculate_time_estimate(
                            task_json.get("pomodoroSummaries", [])
                        ),
                        "focus_time": self._calculate_focus_time(
                            task_json.get("focusSummaries", [])
                        ),
                    }

                    all_tasks.append(task_data)

            except httpx.HTTPError as e:
                # Log error but continue with other projects
                logger.error(f"Error fetching tasks for project {project.get('id')}: {e}")
                continue

        return all_tasks

    async def sync_projects(self, db: AsyncSession) -> List[Any]:
        """
        Fetch all projects from TickTick and upsert into local database.

        This method:
        1. Fetches projects from TickTick API
        2. For each project, checks if it exists in database
        3. Updates existing or creates new project records
        4. Returns list of Project objects

        Args:
            db: Database session for queries and commits

        Returns:
            List of Project objects (synced from TickTick)

        Raises:
            HTTPException: If user not connected to TickTick
        """
        from app.models.project import Project
        from datetime import datetime

        if not self.user or not self.user.ticktick_access_token:
            raise HTTPException(status_code=401, detail="TickTick not connected")

        # Fetch projects from TickTick
        projects_data = await self.get_projects(self.user.ticktick_access_token)

        synced_projects = []

        for proj_data in projects_data:
            ticktick_project_id = proj_data.get("id")

            # Check if project already exists
            stmt = select(Project).where(
                Project.user_id == self.user.id,
                Project.ticktick_project_id == ticktick_project_id
            )
            result = await db.execute(stmt)
            existing_project = result.scalar_one_or_none()

            if existing_project:
                # Update existing project
                existing_project.name = proj_data.get("name")
                existing_project.color = proj_data.get("color")
                existing_project.sort_order = proj_data.get("sortOrder", 0)
                existing_project.is_archived = proj_data.get("closed", False)
                existing_project.updated_at = datetime.utcnow()
                synced_projects.append(existing_project)
            else:
                # Create new project
                new_project = Project(
                    user_id=self.user.id,
                    ticktick_project_id=ticktick_project_id,
                    name=proj_data.get("name"),
                    color=proj_data.get("color"),
                    sort_order=proj_data.get("sortOrder", 0),
                    is_archived=proj_data.get("closed", False)
                )
                db.add(new_project)
                synced_projects.append(new_project)

        await db.commit()

        # Refresh all projects to get their IDs
        for proj in synced_projects:
            await db.refresh(proj)

        logger.info(f"Synced {len(synced_projects)} projects for user {self.user.id}")
        return synced_projects

    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch authenticated user information from TickTick.

        Args:
            access_token: Valid TickTick access token

        Returns:
            User info dictionary

        Raises:
            httpx.HTTPError: If API request fails
        """
        async with httpx.AsyncClient(verify=_SSL_VERIFY) as client:
            response = await client.get(
                f"{self.API_BASE_URL}/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def refresh_user_token(self, db: AsyncSession) -> None:
        """
        Refresh the user's access token using the refresh token.

        Updates the user object with the new tokens.

        Args:
            db: Database session for updating user tokens

        Raises:
            HTTPException: If token refresh fails
        """
        if not self.user or not self.user.ticktick_refresh_token:
            raise HTTPException(status_code=401, detail="No refresh token available")

        try:
            token_data = await self.refresh_access_token(self.user.ticktick_refresh_token)
            self.user.ticktick_access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                self.user.ticktick_refresh_token = token_data["refresh_token"]
            await db.commit()
            logger.info(f"Successfully refreshed token for user {self.user.id}")
        except Exception as e:
            logger.error(f"Failed to refresh token for user {self.user.id}: {e}")
            raise HTTPException(status_code=401, detail="Token refresh failed")

    async def update_task(self, ticktick_task_id: str, task_data: dict, db: AsyncSession) -> dict:
        """
        Update a task in TickTick.

        Args:
            ticktick_task_id: TickTick's task ID
            task_data: Dictionary with fields to update (title, content, priority, dueDate, etc.)
            db: Database session for token refresh if needed

        Returns:
            Updated task data from TickTick API

        Raises:
            HTTPException if update fails
        """
        if not self.user or not self.user.ticktick_access_token:
            raise HTTPException(status_code=401, detail="TickTick not connected")

        # Prepare TickTick-compatible data
        ticktick_payload = {}

        if "title" in task_data:
            ticktick_payload["title"] = task_data["title"]

        if "description" in task_data:
            ticktick_payload["content"] = task_data["description"]

        if "ticktick_priority" in task_data and task_data["ticktick_priority"] is not None:
            ticktick_payload["priority"] = task_data["ticktick_priority"]  # 0/1/3/5

        if "due_date" in task_data and task_data["due_date"]:
            ticktick_payload["dueDate"] = task_data["due_date"].isoformat()

        if "start_date" in task_data and task_data["start_date"]:
            ticktick_payload["startDate"] = task_data["start_date"].isoformat()

        if "ticktick_tags" in task_data and task_data["ticktick_tags"]:
            ticktick_payload["tags"] = task_data["ticktick_tags"]

        if "all_day" in task_data:
            ticktick_payload["isAllDay"] = task_data["all_day"]

        if "ticktick_project_id" in task_data and task_data["ticktick_project_id"]:
            ticktick_payload["projectId"] = task_data["ticktick_project_id"]

        # Make API request
        try:
            response = await self.client.post(
                f"{self.base_url}/task/{ticktick_task_id}",
                headers={"Authorization": f"Bearer {self.user.ticktick_access_token}"},
                json=ticktick_payload,
                timeout=10.0
            )

            if response.status_code == 401:
                # Token expired, try refresh
                await self.refresh_user_token(db)
                response = await self.client.post(
                    f"{self.base_url}/task/{ticktick_task_id}",
                    headers={"Authorization": f"Bearer {self.user.ticktick_access_token}"},
                    json=ticktick_payload,
                    timeout=10.0
                )

            response.raise_for_status()
            logger.info(f"Successfully updated TickTick task {ticktick_task_id}")
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to update TickTick task {ticktick_task_id}: {e}")
            raise HTTPException(status_code=500, detail=f"TickTick sync failed: {str(e)}")

    async def create_task(self, task_data: dict, db: AsyncSession) -> dict:
        """
        Create a new task in TickTick.

        Args:
            task_data: Task details (title, content, priority, dueDate, projectId, etc.)
            db: Database session for token refresh if needed

        Returns:
            Created task data from TickTick API with task ID
        """
        if not self.user or not self.user.ticktick_access_token:
            raise HTTPException(status_code=401, detail="TickTick not connected")

        # Prepare payload (similar to update_task but for creation)
        ticktick_payload = {
            "title": task_data.get("title", "Untitled Task"),
            "content": task_data.get("description", ""),
            "priority": task_data.get("ticktick_priority", 0),
        }

        if task_data.get("due_date"):
            ticktick_payload["dueDate"] = task_data["due_date"].isoformat()

        if task_data.get("ticktick_project_id"):
            ticktick_payload["projectId"] = task_data["ticktick_project_id"]

        if task_data.get("ticktick_tags"):
            ticktick_payload["tags"] = task_data["ticktick_tags"]

        try:
            response = await self.client.post(
                f"{self.base_url}/task",
                headers={"Authorization": f"Bearer {self.user.ticktick_access_token}"},
                json=ticktick_payload,
                timeout=10.0
            )

            if response.status_code == 401:
                await self.refresh_user_token(db)
                response = await self.client.post(
                    f"{self.base_url}/task",
                    headers={"Authorization": f"Bearer {self.user.ticktick_access_token}"},
                    json=ticktick_payload,
                    timeout=10.0
                )

            response.raise_for_status()
            logger.info(f"Successfully created TickTick task: {ticktick_payload['title']}")
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to create TickTick task: {e}")
            raise HTTPException(status_code=500, detail=f"TickTick task creation failed: {str(e)}")

    async def delete_task(self, ticktick_task_id: str, ticktick_project_id: str, db: AsyncSession) -> bool:
        """
        Delete a task from TickTick.

        Args:
            ticktick_task_id: Task ID in TickTick
            ticktick_project_id: Project ID in TickTick (required by API)
            db: Database session for token refresh if needed

        Returns:
            True if deleted successfully
        """
        if not self.user or not self.user.ticktick_access_token:
            raise HTTPException(status_code=401, detail="TickTick not connected")

        try:
            response = await self.client.delete(
                f"{self.base_url}/project/{ticktick_project_id}/task/{ticktick_task_id}",
                headers={"Authorization": f"Bearer {self.user.ticktick_access_token}"},
                timeout=10.0
            )

            if response.status_code == 401:
                await self.refresh_user_token(db)
                response = await self.client.delete(
                    f"{self.base_url}/project/{ticktick_project_id}/task/{ticktick_task_id}",
                    headers={"Authorization": f"Bearer {self.user.ticktick_access_token}"},
                    timeout=10.0
                )

            response.raise_for_status()
            logger.info(f"Successfully deleted TickTick task {ticktick_task_id}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to delete TickTick task {ticktick_task_id}: {e}")
            raise HTTPException(status_code=500, detail=f"TickTick task deletion failed: {str(e)}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global service instance (for OAuth flows without user context)
ticktick_service = TickTickService()
