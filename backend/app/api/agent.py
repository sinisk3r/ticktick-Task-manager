"""
Agent SSE endpoints for tool-planning and execution.

Chat UX v2: Supports both legacy agent (graph.py) and new personalized agent (main_agent.py).
Use 'use_v2_agent' flag in request to enable Chat UX v2 features.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore

from app.agent.graph import create_agent
from app.agent.main_agent import create_context_agent
from app.agent import tools as agent_tools
from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Global instances for Chat UX v2 persistent memory
# Created once at first use, reused across requests to prevent connection leaks
_checkpointer: Optional[AsyncPostgresSaver] = None
_store: Optional[AsyncPostgresStore] = None
_checkpointer_cm: Optional[Any] = None  # Store the context manager to keep it alive
_store_cm: Optional[Any] = None  # Store the context manager to keep it alive
_checkpointer_lock = asyncio.Lock()
_store_lock = asyncio.Lock()
_checkpointer_init_failed = False
_store_init_failed = False

# Configuration: Set to True to disable persistent memory if initialization fails
DISABLE_MEMORY_ON_INIT_FAILURE = True

# Configuration: Disable persistent memory entirely (avoids connection issues with AsyncPostgresSaver)
# Set to False to re-enable persistent memory when connection issues are resolved
DISABLE_PERSISTENT_MEMORY_TEMPORARILY = True


async def _check_checkpoint_tables_exist(pg_url: str) -> bool:
    """
    Check if checkpoint tables already exist in the database.
    
    This allows us to skip setup() if tables exist, avoiding hangs
    on stuck index creation operations.
    """
    try:
        import psycopg
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('checkpoints', 'checkpoint_writes', 'checkpoint_blobs', 'checkpoint_migrations')
                """)
                result = await cur.fetchone()
                if result and result[0] is not None:
                    return result[0] >= 4  # All 4 tables should exist
                return False
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Failed to check checkpoint tables: {e}, will try setup()")
        return False


async def _check_store_tables_exist(pg_url: str) -> bool:
    """
    Check if store tables already exist in the database.
    
    This allows us to skip setup() if tables exist, avoiding hangs
    on stuck index creation operations.
    """
    try:
        import psycopg
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('store', 'store_migrations')
                """)
                result = await cur.fetchone()
                if result and result[0] is not None:
                    return result[0] >= 2  # Both tables should exist
                return False
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Failed to check store tables: {e}, will try setup()")
        return False


def _format_pg_url_for_langgraph(db_url: str) -> str:
    """
    Convert SQLAlchemy asyncpg URL to PostgreSQL URL format expected by LangGraph.
    
    LangGraph uses psycopg3 which expects:
    - postgresql:// (not postgresql+asyncpg://)
    - SSL parameters in query string (sslmode=disable for local dev)
    
    Args:
        db_url: SQLAlchemy database URL (e.g., postgresql+asyncpg://user:pass@host:port/db)
        
    Returns:
        PostgreSQL connection string for LangGraph
    """
    # Replace asyncpg driver
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Parse URL to add SSL parameters if not present
    parsed = urlparse(pg_url)
    query_params = parse_qs(parsed.query)
    
    # Add sslmode=disable for local development if not specified
    if "sslmode" not in query_params:
        query_params["sslmode"] = ["disable"]
    
    # Reconstruct URL with updated query
    new_query = urlencode(query_params, doseq=True)
    formatted_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    logger.debug(f"Formatted DB URL for LangGraph: {formatted_url.replace(parsed.password if parsed.password else '', '***')}")
    return formatted_url


async def get_checkpointer() -> Optional[AsyncPostgresSaver]:
    """
    Get or create global AsyncPostgresSaver instance.

    This singleton pattern ensures we reuse database connections instead of
    creating new ones for each request, preventing connection pool exhaustion.

    Returns:
        Initialized AsyncPostgresSaver instance with tables created, or None if initialization failed
    """
    global _checkpointer, _checkpointer_init_failed

    # If initialization previously failed and we're disabling memory, return None immediately
    if _checkpointer_init_failed and DISABLE_MEMORY_ON_INIT_FAILURE:
        logger.warning("AsyncPostgresSaver initialization previously failed, returning None")
        return None

    if _checkpointer is None:
        async with _checkpointer_lock:
            # Double-check after acquiring lock
            if _checkpointer is None and not _checkpointer_init_failed:
                try:
                    logger.info("Step 1: Starting AsyncPostgresSaver initialization...")
                    
                    # Format connection string for LangGraph (add SSL params)
                    pg_url = _format_pg_url_for_langgraph(settings.database_url)
                    logger.info("Step 2: Connection string formatted")
                    
                    # Create context manager
                    logger.info("Step 3: Creating AsyncPostgresSaver context manager...")
                    cm = AsyncPostgresSaver.from_conn_string(pg_url)
                    logger.info("Step 4: Context manager created, entering...")
                    
                    # Enter async context manager and keep it open
                    # Store both the context manager and the instance to keep connection alive
                    _checkpointer_cm = cm
                    _checkpointer = await cm.__aenter__()
                    logger.info("Step 5: Context manager entered successfully")
                    
                    # Check if tables already exist before calling setup()
                    # This avoids hanging on stuck index creation operations
                    logger.info("Step 6: Checking if checkpoint tables exist...")
                    tables_exist = await _check_checkpoint_tables_exist(pg_url)
                    
                    if tables_exist:
                        logger.info("Step 7: Checkpoint tables already exist, skipping setup()")
                        logger.info("   (If indexes are missing, they will be created on-demand)")
                    else:
                        # Create database tables if they don't exist
                        # Add timeout to prevent indefinite hanging
                        logger.info("Step 7: Tables don't exist, calling setup() to create them...")
                        try:
                            await asyncio.wait_for(_checkpointer.setup(), timeout=30.0)
                            logger.info("Step 8: setup() completed successfully")
                        except asyncio.TimeoutError:
                            logger.error("Step 8: setup() timed out after 30 seconds!")
                            logger.warning("   This may be due to stuck index creation operations.")
                            logger.warning("   Run: python scripts/fix_index_locks.py to fix stuck operations")
                            # Clean up the context manager
                            try:
                                if _checkpointer_cm:
                                    await _checkpointer_cm.__aexit__(None, None, None)
                            except Exception as cleanup_error:
                                logger.error(f"Error during cleanup: {cleanup_error}")
                            _checkpointer = None
                            _checkpointer_cm = None
                            _checkpointer_init_failed = True
                            if DISABLE_MEMORY_ON_INIT_FAILURE:
                                logger.warning("AsyncPostgresSaver initialization failed, continuing without persistent memory")
                                return None
                            raise RuntimeError("AsyncPostgresSaver.setup() timed out after 30 seconds")
                    
                    logger.info("AsyncPostgresSaver initialized and ready")
                    
                except Exception as e:
                    logger.exception(f"Failed to initialize AsyncPostgresSaver: {e}")
                    _checkpointer = None
                    _checkpointer_cm = None
                    _checkpointer_init_failed = True
                    if DISABLE_MEMORY_ON_INIT_FAILURE:
                        logger.warning("AsyncPostgresSaver initialization failed, continuing without persistent memory")
                        return None
                    raise RuntimeError(f"AsyncPostgresSaver initialization failed: {e}") from e

    return _checkpointer


async def get_store() -> Optional[AsyncPostgresStore]:
    """
    Get or create global AsyncPostgresStore instance.

    This singleton pattern ensures we reuse database connections instead of
    creating new ones for each request, preventing connection pool exhaustion.

    Returns:
        Initialized AsyncPostgresStore instance with tables created, or None if initialization failed
    """
    global _store, _store_init_failed

    # If initialization previously failed and we're disabling memory, return None immediately
    if _store_init_failed and DISABLE_MEMORY_ON_INIT_FAILURE:
        logger.warning("AsyncPostgresStore initialization previously failed, returning None")
        return None

    if _store is None:
        async with _store_lock:
            # Double-check after acquiring lock
            if _store is None and not _store_init_failed:
                try:
                    logger.info("Step 1: Starting AsyncPostgresStore initialization...")
                    
                    # Format connection string for LangGraph (add SSL params)
                    pg_url = _format_pg_url_for_langgraph(settings.database_url)
                    logger.info("Step 2: Connection string formatted")
                    
                    # Create context manager
                    logger.info("Step 3: Creating AsyncPostgresStore context manager...")
                    cm = AsyncPostgresStore.from_conn_string(pg_url)
                    logger.info("Step 4: Context manager created, entering...")
                    
                    # Enter async context manager and keep it open
                    # Store both the context manager and the instance to keep connection alive
                    _store_cm = cm
                    _store = await cm.__aenter__()
                    logger.info("Step 5: Context manager entered successfully")
                    
                    # Check if tables already exist before calling setup()
                    # This avoids hanging on stuck index creation operations
                    logger.info("Step 6: Checking if store tables exist...")
                    tables_exist = await _check_store_tables_exist(pg_url)
                    
                    if tables_exist:
                        logger.info("Step 7: Store tables already exist, skipping setup()")
                        logger.info("   (If indexes are missing, they will be created on-demand)")
                    else:
                        # Create database tables if they don't exist
                        # Add timeout to prevent indefinite hanging
                        logger.info("Step 7: Tables don't exist, calling setup() to create them...")
                        try:
                            await asyncio.wait_for(_store.setup(), timeout=30.0)
                            logger.info("Step 8: setup() completed successfully")
                        except asyncio.TimeoutError:
                            logger.error("Step 8: setup() timed out after 30 seconds!")
                            logger.warning("   This may be due to stuck index creation operations.")
                            logger.warning("   Run: python scripts/fix_index_locks.py to fix stuck operations")
                            # Clean up the context manager
                            try:
                                if _store_cm:
                                    await _store_cm.__aexit__(None, None, None)
                            except Exception as cleanup_error:
                                logger.error(f"Error during cleanup: {cleanup_error}")
                            _store = None
                            _store_cm = None
                            _store_init_failed = True
                            if DISABLE_MEMORY_ON_INIT_FAILURE:
                                logger.warning("AsyncPostgresStore initialization failed, continuing without persistent memory")
                                return None
                            raise RuntimeError("AsyncPostgresStore.setup() timed out after 30 seconds")
                    
                    logger.info("AsyncPostgresStore initialized and ready")
                    
                except Exception as e:
                    logger.exception(f"Failed to initialize AsyncPostgresStore: {e}")
                    _store = None
                    _store_cm = None
                    _store_init_failed = True
                    if DISABLE_MEMORY_ON_INIT_FAILURE:
                        logger.warning("AsyncPostgresStore initialization failed, continuing without persistent memory")
                        return None
                    raise RuntimeError(f"AsyncPostgresStore initialization failed: {e}") from e

    return _store


class StreamRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    user_id: int = Field(..., gt=0, description="User scope for the agent")
    context: Optional[Dict[str, Any]] = None
    dry_run: bool = False
    messages: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Conversation history (list of {role: 'user'|'assistant', content: str})"
    )
    use_v2_agent: bool = Field(
        default=False,
        description="Use Chat UX v2 agent with personalization and persistent memory"
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
            # Choose between legacy agent (graph.py) or Chat UX v2 agent (main_agent.py)
            if payload.use_v2_agent:
                # Chat UX v2: Personalized agent with AsyncPostgresStore memory
                logger.info(f"Using Chat UX v2 agent for user_id={payload.user_id}")

                # Get or create global checkpointer/store instances
                # These may return None if initialization failed (with DISABLE_MEMORY_ON_INIT_FAILURE=True)
                # TEMPORARY: Disable persistent memory until connection issue is fixed
                if DISABLE_PERSISTENT_MEMORY_TEMPORARILY:
                    logger.warning("Persistent memory temporarily disabled due to connection issues")
                    checkpointer = None
                    store = None
                else:
                    logger.info("Getting checkpointer instance...")
                    checkpointer = await get_checkpointer()
                    logger.info(f"Checkpointer: {'available' if checkpointer else 'disabled (init failed)'}")
                    
                    logger.info("Getting store instance...")
                    store = await get_store()
                    logger.info(f"Store: {'available' if store else 'disabled (init failed)'}")

                agent = await create_context_agent(
                    user_id=payload.user_id,
                    db=db,
                    checkpointer=checkpointer,
                    store=store,
                )
            else:
                # Legacy agent: MemorySaver checkpointer (in-memory)
                logger.info(f"Using legacy agent for user_id={payload.user_id}")
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
    config: RunnableConfig = {
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

