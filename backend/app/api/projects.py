"""
Project CRUD API endpoints for TickTick project management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.services.ticktick import TickTickService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[dict])
async def get_projects(
    user_id: int = Query(1, description="User ID to get projects for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all projects for the specified user.

    Returns list of projects with:
    - id: Database project ID
    - ticktick_project_id: TickTick project ID
    - name: Project name
    - color: Hex color code
    - sort_order: Display order
    - is_archived: Archive status
    - created_at: Creation timestamp
    - updated_at: Last update timestamp

    Query parameters:
    - user_id: User ID to filter projects (default: 1)
    """
    stmt = select(Project).where(
        Project.user_id == user_id,
        Project.is_archived == False
    ).order_by(Project.sort_order, Project.name)

    result = await db.execute(stmt)
    projects = result.scalars().all()

    return [
        {
            "id": p.id,
            "ticktick_project_id": p.ticktick_project_id,
            "name": p.name,
            "color": p.color,
            "sort_order": p.sort_order,
            "is_archived": p.is_archived,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        }
        for p in projects
    ]


@router.post("/sync")
async def force_sync_projects(
    user_id: int = Query(1, description="User ID to sync projects for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Force sync projects from TickTick.

    This endpoint:
    1. Fetches all projects from TickTick API
    2. Updates existing projects or creates new ones
    3. Returns count and list of synced projects

    Query parameters:
    - user_id: User ID to sync projects for (default: 1)

    Raises:
        HTTPException: If user not found, TickTick not connected, or sync fails
    """
    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.ticktick_access_token:
        raise HTTPException(status_code=401, detail="TickTick not connected")

    ticktick_service = TickTickService(user)

    try:
        projects = await ticktick_service.sync_projects(db)
        return {
            "synced_count": len(projects),
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "ticktick_project_id": p.ticktick_project_id,
                    "color": p.color,
                    "sort_order": p.sort_order
                }
                for p in projects
            ]
        }
    except Exception as e:
        logger.error(f"Project sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
