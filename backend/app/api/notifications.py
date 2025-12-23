"""
Notifications API for SSE-based real-time notifications.

Provides Server-Sent Events (SSE) endpoint for pushing notifications to clients:
- Overdue task alerts
- Upcoming deadline reminders
- Custom reminders

Frontend connects to /api/notifications/stream and receives events in real-time.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _format_sse(event: str, data: Dict[str, Any]) -> str:
    """Format data as Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/stream")
async def notification_stream(
    user_id: int = Query(..., gt=0, description="User ID for notifications"),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE endpoint for real-time notifications.

    Opens a persistent connection and streams notification events to the client.
    The client should reconnect if the connection drops.

    Events:
    - overdue: Tasks past due date
    - deadline: Tasks approaching deadline (within 24 hours)
    - reminder: Custom reminders

    Query Parameters:
        user_id: User ID to fetch notifications for

    Event Format:
        event: overdue
        data: {
            "count": 3,
            "tasks": [
                {"id": 123, "title": "Review PR", "due_date": "2025-12-20T10:00:00"},
                ...
            ]
        }

    Example Usage (Frontend):
        const eventSource = new EventSource('/api/notifications/stream?user_id=1');
        eventSource.addEventListener('overdue', (event) => {
            const data = JSON.parse(event.data);
            showToast(`${data.count} overdue tasks`, {tasks: data.tasks});
        });

    Notes:
        - Connection stays open indefinitely
        - Frontend should handle reconnection on disconnect
        - Server sends keepalive comments every 30 seconds
    """
    logger.info(f"Notification stream opened for user_id={user_id}")

    async def event_generator():
        try:
            # Initialize reminder service
            reminder_service = ReminderService(db, user_id)

            # Send initial connection confirmation
            yield _format_sse("connected", {"user_id": user_id, "timestamp": asyncio.get_event_loop().time()})

            # Main event loop
            while True:
                try:
                    # Check for overdue tasks
                    overdue = await reminder_service.check_overdue_tasks()
                    if overdue.get("overdue_tasks"):
                        yield _format_sse("overdue", {
                            "count": len(overdue["overdue_tasks"]),
                            "tasks": overdue["overdue_tasks"][:5],  # Limit to 5
                        })

                    # Check for upcoming deadlines (within 24 hours)
                    deadlines = await reminder_service.check_upcoming_deadlines(hours=24)
                    if deadlines.get("upcoming_tasks"):
                        yield _format_sse("deadline", {
                            "count": len(deadlines["upcoming_tasks"]),
                            "tasks": deadlines["upcoming_tasks"][:5],  # Limit to 5
                        })

                    # Keepalive: Send comment every 30 seconds to keep connection alive
                    yield ": keepalive\n\n"

                    # Wait 30 seconds before next check
                    await asyncio.sleep(30)

                except asyncio.CancelledError:
                    logger.info(f"Notification stream cancelled for user_id={user_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in notification loop for user_id={user_id}: {e}", exc_info=True)
                    # Send error event and continue (don't break connection)
                    yield _format_sse("error", {
                        "message": "Error fetching notifications",
                        "details": str(e)
                    })
                    await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info(f"Notification stream closed for user_id={user_id}")
        except Exception as e:
            logger.error(f"Fatal error in notification stream for user_id={user_id}: {e}", exc_info=True)
            yield _format_sse("error", {
                "message": "Notification stream failed",
                "details": str(e)
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )


@router.get("/test")
async def test_notifications(
    user_id: int = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Test endpoint to check notification data without SSE.

    Returns current overdue and upcoming deadline tasks for debugging.

    Query Parameters:
        user_id: User ID to check

    Returns:
        {
            "overdue": {...},
            "upcoming_deadlines": {...}
        }
    """
    try:
        reminder_service = ReminderService(db, user_id)

        overdue = await reminder_service.check_overdue_tasks()
        deadlines = await reminder_service.check_upcoming_deadlines(hours=24)

        return {
            "user_id": user_id,
            "overdue": overdue,
            "upcoming_deadlines": deadlines,
        }

    except Exception as e:
        logger.error(f"Test notifications failed for user_id={user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
