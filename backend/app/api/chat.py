"""
Chat streaming endpoints for the assistant side panel.
"""
import json
import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services import OllamaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Single chat message."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """Request payload for streaming chat."""

    messages: List[ChatMessage] = Field(
        ...,
        description="Conversation history to ground the assistant.",
        min_length=1,
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Optional structured context (tasks, email, calendar)."
    )
    user_id: Optional[int] = Field(
        None, description="Optional user id for logging/guardrails."
    )


@router.post("/stream")
async def stream_chat(payload: ChatRequest):
    """
    Stream chat responses as Server-Sent Events.

    SSE events:
    - event: message  data: {"delta": "<partial text>"}
    - event: done     data: {}
    - event: error    data: {"error": "<message>"}
    """
    ollama = OllamaService()

    if not await ollama.health_check():
        raise HTTPException(
            status_code=503,
            detail=f"Ollama not available. Ensure it's running at {ollama.base_url}",
        )

    async def event_generator():
        try:
            async for chunk in ollama.stream_chat(
                [m.model_dump() for m in payload.messages],
                context=payload.context,
                user_id=payload.user_id,
            ):
                event_type = "message" if chunk.get("type") == "content" else "thinking"
                yield f"event: {event_type}\ndata: {json.dumps({'delta': chunk.get('delta', '')})}\n\n"

            yield "event: done\ndata: {}\n\n"
        except Exception as e:  # noqa: BLE001
            logger.error(f"Chat stream failed: {e}")
            error_payload = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

