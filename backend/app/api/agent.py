"""
Agent SSE endpoints for tool-planning and execution.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage

from app.agent.graph import create_agent
from app.agent import tools as agent_tools
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


class StreamRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    user_id: int = Field(..., gt=0, description="User scope for the agent")
    context: Optional[Dict[str, Any]] = None
    dry_run: bool = False
    messages: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Conversation history (list of {role: 'user'|'assistant', content: str})"
    )


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
    Stream agent events as Server-Sent Events using LangGraph.
    Events: thinking, step, tool_request, tool_result, message, done, error.
    """
    trace_id = str(uuid.uuid4())

    async def event_generator():
        try:
            # Create LangGraph agent with conversation memory
            # The create_agent function handles:
            # - LLM provider initialization (via get_llm)
            # - Tool binding with user_id and db injection
            # - MemorySaver checkpointer for conversation history
            agent = create_agent(user_id=payload.user_id, db=db)

            # Build conversation history from frontend
            messages = []
            if payload.messages:
                for msg in payload.messages:
                    # Convert conversation history to LangChain messages
                    # Frontend sends: {role: 'user'|'assistant', content: str}
                    if msg.get("role") == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    # Note: Assistant messages will be reconstructed from checkpointer

            # Add current goal as new human message
            messages.append(HumanMessage(content=payload.goal))

            # Configuration for conversation memory (thread-based)
            config = {
                "configurable": {
                    "thread_id": f"user_{payload.user_id}",
                }
            }

            # Stream events from LangGraph and transform to our SSE format
            step_counter = 0
            current_tool = None
            accumulated_message = ""

            async for event in agent.astream_events(
                {"messages": messages},
                config=config,
                version="v2",
            ):
                event_type = event.get("event")
                event_name = event.get("name", "")
                data = event.get("data", {})

                # Map LangGraph events to our SSE format
                # Reference: https://python.langchain.com/docs/how_to/streaming/#event-reference

                if event_type == "on_chat_model_stream":
                    # LLM is streaming tokens (thinking/response)
                    chunk = data.get("chunk")
                    if chunk:
                        content = getattr(chunk, "content", "")
                        if content:
                            accumulated_message += content
                            # Stream as thinking event (shows reasoning)
                            yield _format_sse("thinking", {
                                "trace_id": trace_id,
                                "delta": content,
                            })

                elif event_type == "on_tool_start":
                    # Tool is about to be called
                    step_counter += 1
                    tool_name = event_name
                    current_tool = tool_name
                    tool_input = data.get("input", {})

                    # Emit step event
                    yield _format_sse("step", {
                        "trace_id": trace_id,
                        "step": step_counter,
                        "summary": f"Calling {tool_name}",
                    })

                    # Emit tool_request event
                    # 'db' is already bound via .bind(), so it's hidden from tool_input
                    yield _format_sse("tool_request", {
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "args": tool_input,
                        "confirmation_required": False,
                    })

                elif event_type == "on_tool_end":
                    # Tool execution completed
                    tool_output = data.get("output")

                    if current_tool:
                        yield _format_sse("tool_result", {
                            "trace_id": trace_id,
                            "tool": current_tool,
                            "result": tool_output,
                        })

                        # If tool result has a summary, emit as message
                        if isinstance(tool_output, dict) and tool_output.get("summary"):
                            yield _format_sse("message", {
                                "trace_id": trace_id,
                                "message": tool_output["summary"],
                                "payload": {k: v for k, v in tool_output.items() if k != "summary"},
                            })

                    current_tool = None

                elif event_type == "on_chain_end":
                    # Agent finished processing
                    # Emit final accumulated message if we have one
                    if accumulated_message.strip():
                        yield _format_sse("message", {
                            "trace_id": trace_id,
                            "message": accumulated_message.strip(),
                        })
                        accumulated_message = ""

            # Done
            yield _format_sse("done", {"trace_id": trace_id})

        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent stream failed (trace_id=%s)", trace_id)
            yield _format_sse("error", {
                "trace_id": trace_id,
                "message": str(exc),
            })

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/execute")
async def execute_tool(payload: ExecuteRequest, db: AsyncSession = Depends(get_db)):
    """
    Execute a single tool without planning. Useful for confirmations.
    Direct tool invocation using LangChain tools.
    """
    trace_id = payload.trace_id or str(uuid.uuid4())

    # Get tool by name from agent_tools module
    tool_map = {
        "fetch_tasks": agent_tools.fetch_tasks,
        "fetch_task": agent_tools.fetch_task,
        "create_task": agent_tools.create_task,
        "update_task": agent_tools.update_task,
        "complete_task": agent_tools.complete_task,
        "delete_task": agent_tools.delete_task,
        "quick_analyze_task": agent_tools.quick_analyze_task,
    }

    if payload.tool not in tool_map:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {payload.tool}")

    tool = tool_map[payload.tool]
    args = {**payload.args, "user_id": payload.user_id, "db": db}

    try:
        result = await tool.ainvoke(args)
        return {
            "trace_id": trace_id,
            "tool": payload.tool,
            "result": result,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tool execution failed (trace_id=%s, tool=%s)", trace_id, payload.tool)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

