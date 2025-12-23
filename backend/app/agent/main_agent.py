"""
LangGraph Agent with Middleware and Persistent Memory for Context.

This is the new Chat UX v2 agent that replaces graph.py with:
- Personalized system prompts via middleware
- Cross-session memory persistence (AsyncPostgresStore)
- Adaptive tone based on user preferences
- All existing tools from tools.py

For backward compatibility, graph.py remains unchanged and can be used
by legacy endpoints. New endpoints should use this module.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import create_react_agent
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_factory import get_llm_for_user
from app.agent.middleware import load_user_preferences, create_personalized_system_message
from app.agent.tools import (
    # Core task tools
    fetch_tasks,
    fetch_task,
    create_task,
    update_task,
    complete_task,
    delete_task,
    quick_analyze_task,
    # V1 MVP + Phase 2 tools
    detect_stale_tasks,
    breakdown_task,
    draft_email,
    get_workload_analytics,
    get_rest_recommendation,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_base_system_message() -> str:
    """
    Generate base system message with current date/time context.

    This is the non-personalized base prompt. Middleware will enhance it
    with user-specific preferences.
    """
    now = datetime.now()
    current_date = now.strftime("%A, %B %d, %Y")
    current_time = now.strftime("%I:%M %p")

    return f"""You are Context, an agentic task copilot designed to help users manage their tasks efficiently.

**Current Date & Time:**
Today is {current_date} at {current_time}.

**Your capabilities:**
- Create, update, complete, and delete tasks
- List and filter tasks by status or quadrant
- Analyze task urgency and importance
- Detect stale tasks and suggest prioritization
- Break down complex tasks into subtasks
- Draft emails about tasks
- Analyze workload and provide rest recommendations
- Provide task management advice and insights

**When to call tools:**
- User wants to create/add a task → use `create_task`
- User wants to update/modify a task → use `update_task`
- User wants to complete/finish a task → use `complete_task`
- User wants to delete/remove a task → use `delete_task`
- User wants to list/show/view tasks → use `fetch_tasks` (defaults to ACTIVE tasks only)
- User asks about a specific task → use `fetch_task`
- User wants analysis on a task description → use `quick_analyze_task`
- User asks about stale/forgotten tasks → use `detect_stale_tasks`
- User wants to break down a complex task → use `breakdown_task`
- User wants to draft an email about a task → use `draft_email`
- User asks about workload/capacity → use `get_workload_analytics`
- User feels overwhelmed or asks about rest → use `get_rest_recommendation`

**Task status filtering:**
- `fetch_tasks` defaults to returning only ACTIVE tasks
- To see completed tasks, set status="completed" or status=None
- Before completing a task, check its current status to avoid duplicates

**Task display in responses:**
- When mentioning tasks, use format [TASK:{{id}}] where {{id}} is the task ID
- Example: "I found these tasks: [TASK:123] and [TASK:456]"
- Always include task ID references when discussing specific tasks

**Task creation guidelines:**
- Extract clear, concise titles (max 120 chars, no quotes)
- Only add description if it provides meaningful context beyond the title
- Infer priority from user's language (urgent → 5, important → 3, normal → 0)
- Extract due dates from natural language based on current date
- Format dates as ISO 8601: YYYY-MM-DDTHH:MM:SS
- Suggest relevant tags (e.g., "meeting", "bug", "review")

**Remember:**
- Use the user's full task list when relevant
- Ask for confirmation before destructive actions
- Be proactive about suggesting task organization
- Learn from conversation context
"""


async def create_context_agent(
    user_id: int,
    db: AsyncSession,
    llm: Optional[BaseChatModel] = None,
    checkpointer: Optional[Any] = None,  # AsyncPostgresSaver instance
    store: Optional[Any] = None,  # AsyncPostgresStore instance
) -> Any:
    """
    Create a personalized LangGraph agent with middleware and persistent memory.

    This is the Chat UX v2 agent that:
    1. Loads user preferences from Profile and UserMemory
    2. Generates personalized system prompt via middleware
    3. Uses AsyncPostgresStore for cross-session memory
    4. Uses AsyncPostgresSaver for conversation checkpointing
    5. Maintains all existing tools from tools.py

    Args:
        user_id: User ID for tool execution and preference loading
        db: Database session for tool access
        llm: Optional LLM instance (defaults to user settings)
        checkpointer: Optional AsyncPostgresSaver instance for conversation persistence
        store: Optional AsyncPostgresStore instance for cross-session memory

    Returns:
        Configured LangGraph agent with personalization

    Raises:
        ValueError: If user_id is invalid or db is None
        RuntimeError: If LLM or memory initialization fails

    Example:
        >>> from app.core.database import get_db
        >>> from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        >>> from app.agent.main_agent import create_context_agent
        >>> from app.core.config import settings
        >>>
        >>> # Initialize checkpointer/store at application level (once)
        >>> pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        >>> async with AsyncPostgresSaver.from_conn_string(pg_url) as checkpointer:
        ...     await checkpointer.setup()
        ...
        ...     # Create agent with pre-initialized instances
        ...     async with get_db() as db:
        ...         agent = await create_context_agent(
        ...             user_id=1,
        ...             db=db,
        ...             checkpointer=checkpointer
        ...         )
        ...
        ...         # Invoke with conversation tracking
        ...         result = await agent.ainvoke(
        ...             {"messages": [("user", "Create a task for team sync")]},
        ...             config={"configurable": {"thread_id": "user-1", "user_id": 1, "db": db}}
        ...         )
    """
    # Validate inputs
    if not user_id or user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}. Must be a positive integer.")

    if db is None:
        raise ValueError("Database session (db) cannot be None")

    # Get LLM instance
    if llm is None:
        try:
            llm = await get_llm_for_user(user_id=user_id, db=db)
            logger.info(f"Created LLM instance from user settings (user_id={user_id})")
        except Exception as e:
            logger.error(f"Failed to create LLM instance: {e}")
            raise RuntimeError(f"LLM initialization failed: {e}") from e

    # Load user preferences from Profile and UserMemory
    try:
        user_preferences = await load_user_preferences(user_id, db)
        logger.info(
            f"Loaded user preferences (user_id={user_id}): "
            f"tone={user_preferences.get('preferred_tone')}, "
            f"work_style={user_preferences.get('work_style')}"
        )
    except Exception as e:
        logger.warning(f"Failed to load user preferences, using defaults: {e}")
        user_preferences = {"preferred_tone": "friendly"}

    # Generate personalized system prompt
    personalized_message = create_personalized_system_message(user_preferences)
    base_message = get_base_system_message()

    # Combine base and personalized prompts
    full_system_prompt = f"{base_message}\n\n{personalized_message.content}"

    # Prepare tools (same as graph.py)
    tools_list = [
        # Core task tools
        fetch_tasks,
        fetch_task,
        create_task,
        update_task,
        complete_task,
        delete_task,
        quick_analyze_task,
        # V1 MVP + Phase 2 tools
        detect_stale_tasks,
        breakdown_task,
        draft_email,
        get_workload_analytics,
        get_rest_recommendation,
    ]

    logger.info(
        f"Configured {len(tools_list)} tools for agent (user_id={user_id}): "
        f"{[t.name for t in tools_list]}"
    )

    # Use provided checkpointer and store instances (already initialized by caller)
    # Agent works fine without them, just no persistence across sessions
    logger.info(
        f"Agent memory config for user_id={user_id}: "
        f"checkpointer={'provided' if checkpointer else 'disabled'}, "
        f"store={'provided' if store else 'disabled'}"
    )

    # Create ReAct agent
    try:
        # Verify tool schemas
        logger.debug(f"Verifying tool schemas for {len(tools_list)} tools...")
        for tool in tools_list:
            try:
                schema = tool.get_input_schema()
                logger.debug(f"✓ Tool '{tool.name}' schema validated")
            except Exception as schema_error:
                logger.error(f"✗ Tool '{tool.name}' schema generation failed: {schema_error}")
                raise ValueError(f"Tool '{tool.name}' has invalid schema") from schema_error

        agent = create_react_agent(
            model=llm,
            tools=tools_list,
            prompt=full_system_prompt,
            checkpointer=checkpointer,
            # Note: LangGraph v1 doesn't have middleware support in create_react_agent yet
            # We handle personalization by injecting it into the system prompt
            # Future: Use middleware hooks when available
        )

        # Store metadata on agent for helper functions
        agent._user_id = user_id  # type: ignore
        agent._db = db  # type: ignore
        agent._store = store  # type: ignore

        logger.info(
            f"Successfully created personalized agent for user_id={user_id} "
            f"with {len(tools_list)} tools, memory={'enabled' if checkpointer else 'disabled'}, "
            f"store={'enabled' if store else 'disabled'}"
        )

        return agent

    except Exception as e:
        logger.error(f"Failed to create agent for user_id={user_id}: {e}", exc_info=True)
        raise RuntimeError(f"Agent creation failed: {e}") from e


__all__ = ["create_context_agent", "get_base_system_message"]
