"""
Agent SSE endpoints for tool-planning and execution.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import AgentDispatcher, AgentPlanner, ConfirmationRequired
from app.agent.tools import TOOL_REGISTRY
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


class StreamRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    user_id: int = Field(..., gt=0, description="User scope for the agent")
    context: Optional[Dict[str, Any]] = None
    dry_run: bool = False


class ExecuteRequest(BaseModel):
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    user_id: int = Field(..., gt=0)
    trace_id: Optional[str] = None


def _format_sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
async def stream_agent(payload: StreamRequest, db: AsyncSession = Depends(get_db)):
    """
    Stream agent events as Server-Sent Events.
    Events: thinking, step, tool_request, tool_result, message, done, error.
    """
    planner = AgentPlanner()

    async def event_generator():
        try:
            async for evt in planner.run(
                payload.goal,
                user_id=payload.user_id,
                db=db,
                context=payload.context,
                dry_run=payload.dry_run,
            ):
                yield _format_sse(evt["event"], evt.get("data", {}))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent stream failed")
            yield _format_sse("error", {"message": str(exc)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/execute")
async def execute_tool(payload: ExecuteRequest, db: AsyncSession = Depends(get_db)):
    """
    Execute a single tool without planning. Useful for confirmations.
    """
    dispatcher = AgentDispatcher()
    trace_id = payload.trace_id or str(uuid.uuid4())
    args = {**payload.args, "user_id": payload.user_id}

    if payload.tool not in TOOL_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {payload.tool}")

    try:
        result = await dispatcher.dispatch(payload.tool, args, db, trace_id)
        return {
            "trace_id": trace_id,
            "tool": payload.tool,
            "result": result,
        }
    except ConfirmationRequired as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Confirmation required for {payload.tool}",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tool execution failed (trace_id=%s)", trace_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

