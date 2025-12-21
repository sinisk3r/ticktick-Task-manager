"""
Agent SSE endpoints for tool-planning and execution.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage

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
            # - LLM provider initialization (via get_llm_for_user with user settings)
            # - Tool binding with user_id and db injection
            # - MemorySaver checkpointer for conversation history
            agent = await create_agent(user_id=payload.user_id, db=db)

            # Build conversation history from frontend
            messages = []
            if payload.messages:
                for msg in payload.messages:
                    # Convert conversation history to LangChain messages
                    # Frontend sends: {role: 'user'|'assistant', content: str}
                    role = msg.get("role")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
                    # Skip other roles or invalid messages

            # Add current goal as new human message
            messages.append(HumanMessage(content=payload.goal))

            # Configuration for conversation memory (thread-based)
            # IMPORTANT: user_id and db must be injected in configurable for tools to work
            config = {
                "configurable": {
                    "thread_id": f"user_{payload.user_id}",
                    "user_id": payload.user_id,
                    "db": db,
                },
            }

            # Stream events from LangGraph and transform to our SSE format
            step_counter = 0
            current_tool = None
            accumulated_message = ""
            is_tool_phase = False  # Track if we're in tool calling phase (reasoning)

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
                    # LLM is streaming tokens
                    chunk = data.get("chunk")
                    if chunk:
                        content = getattr(chunk, "content", "")
                        if content:
                            # Handle case where content is a list of content blocks (e.g., Anthropic)
                            # Some providers return list of dicts like [{"type": "text", "text": "..."}]
                            if isinstance(content, list):
                                text_content = ""
                                for block in content:
                                    if isinstance(block, dict) and block.get("type") == "text":
                                        text_content += block.get("text", "")
                                    elif isinstance(block, str):
                                        text_content += block
                                content = text_content

                            if content:  # Check again after potential list conversion
                                accumulated_message += content
                                # Always emit as "message" - cloud APIs don't have separate thinking
                                # Tool calls will be shown inline chronologically
                                yield _format_sse("message", {
                                    "trace_id": trace_id,
                                    "delta": content,
                                })

                elif event_type == "on_tool_start":
                    # Tool is about to be called - enter tool/reasoning phase
                    is_tool_phase = True
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
                    # Tool execution completed - exit tool/reasoning phase
                    is_tool_phase = False
                    tool_output = data.get("output")

                    if current_tool:
                        # Serialize tool output properly
                        # LangChain may return ToolMessage objects that need to be converted
                        serializable_output = tool_output
                        if hasattr(tool_output, "content"):
                            # It's a LangChain message object
                            serializable_output = tool_output.content

                        yield _format_sse("tool_result", {
                            "trace_id": trace_id,
                            "tool": current_tool,
                            "result": serializable_output,
                        })

                        # If tool result has a summary, emit as message
                        if isinstance(serializable_output, dict) and serializable_output.get("summary"):
                            yield _format_sse("message", {
                                "trace_id": trace_id,
                                "message": serializable_output["summary"],
                                "payload": {k: v for k, v in serializable_output.items() if k != "summary"},
                            })

                    current_tool = None

                elif event_type == "on_chain_end":
                    # Agent finished processing
                    # Don't emit accumulated message - deltas already streamed everything
                    # This prevents duplicate content in the frontend
                    pass

            # Done
            yield _format_sse("done", {"trace_id": trace_id})

        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent stream failed (trace_id=%s)", trace_id)
            
            # Try to extract structured error information
            error_message = str(exc)
            error_data: Dict[str, Any] = {
                "trace_id": trace_id,
                "message": error_message,
                "type": type(exc).__name__,
            }
            
            # Try to parse JSON error messages (common with API errors)
            try:
                # Check if the error message contains JSON
                if "{" in error_message and "}" in error_message:
                    # Try to extract JSON from the error message
                    json_match = re.search(r'\{.*\}', error_message, re.DOTALL)
                    if json_match:
                        parsed_json = json.loads(json_match.group())
                        error_data["parsed_error"] = parsed_json
                        # Extract user-friendly message if available
                        if isinstance(parsed_json, dict):
                            if parsed_json.get("error", {}).get("message"):
                                error_data["user_message"] = parsed_json["error"]["message"]
                            elif parsed_json.get("message"):
                                error_data["user_message"] = parsed_json["message"]
            except (json.JSONDecodeError, AttributeError):
                # Not JSON, use the error message as-is
                pass
            
            yield _format_sse("error", error_data)

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
        # Core task tools
        "fetch_tasks": agent_tools.fetch_tasks,
        "fetch_task": agent_tools.fetch_task,
        "create_task": agent_tools.create_task,
        "update_task": agent_tools.update_task,
        "complete_task": agent_tools.complete_task,
        "delete_task": agent_tools.delete_task,
        "quick_analyze_task": agent_tools.quick_analyze_task,
        # V1 MVP + Phase 2 tools
        "detect_stale_tasks": agent_tools.detect_stale_tasks,
        "breakdown_task": agent_tools.breakdown_task,
        "draft_email": agent_tools.draft_email,
        "get_workload_analytics": agent_tools.get_workload_analytics,
        "get_rest_recommendation": agent_tools.get_rest_recommendation,
    }

    if payload.tool not in tool_map:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {payload.tool}")

    tool = tool_map[payload.tool]

    # Build config with injected parameters
    config = {
        "configurable": {
            "user_id": payload.user_id,
            "db": db,
        }
    }

    try:
        result = await tool.ainvoke(payload.args, config=config)
        return {
            "trace_id": trace_id,
            "tool": payload.tool,
            "result": result,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tool execution failed (trace_id=%s, tool=%s)", trace_id, payload.tool)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

