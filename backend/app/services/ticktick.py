"""
TickTick API service for OAuth authentication and task synchronization.

This service handles:
1. OAuth2 authorization flow (authorize URL generation, token exchange, refresh)
2. Task fetching from TickTick API
3. Token management and storage
"""
import httpx
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User


class TickTickService:
    """TickTick API client for OAuth and task management."""

    # TickTick OAuth endpoints
    AUTHORIZE_URL = "https://ticktick.com/oauth/authorize"
    TOKEN_URL = "https://ticktick.com/oauth/token"
    API_BASE_URL = "https://api.ticktick.com/open/v1"

    # OAuth scope
    SCOPE = "tasks:read tasks:write"

    def __init__(self):
        """Initialize TickTick service with configuration."""
        self.client_id = settings.ticktick_client_id
        self.client_secret = settings.ticktick_client_secret
        self.redirect_uri = settings.ticktick_redirect_uri

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
        async with httpx.AsyncClient() as client:
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
        async with httpx.AsyncClient() as client:
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
            user = User(
                id=user_id,
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
        async with httpx.AsyncClient() as client:
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE_URL}/project/{project_id}/data",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def get_tasks(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Fetch all tasks from TickTick API across all projects.

        This method:
        1. Fetches all projects
        2. For each project, fetches project data with tasks
        3. Returns consolidated list of all tasks

        Args:
            access_token: Valid TickTick access token

        Returns:
            List of task dictionaries with fields:
            - id: Task ID
            - title: Task title
            - content: Task description/content
            - project_id: Project ID
            - due_date: Due date (ISO 8601 format)
            - priority: Priority level (0-5)
            - status: Completion status (0=incomplete, 2=complete)
            - created_time: Creation timestamp
            - modified_time: Last modification timestamp

        Raises:
            httpx.HTTPError: If API request fails
        """
        all_tasks = []

        # Get all projects
        projects = await self.get_projects(access_token)

        # Fetch tasks from each project
        for project in projects:
            try:
                project_data = await self.get_project_data(
                    access_token,
                    project["id"]
                )

                # Extract tasks from project data
                tasks = project_data.get("tasks", [])
                all_tasks.extend(tasks)

            except httpx.HTTPError as e:
                # Log error but continue with other projects
                print(f"Error fetching tasks for project {project['id']}: {e}")
                continue

        return all_tasks

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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE_URL}/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()


# Global service instance
ticktick_service = TickTickService()
