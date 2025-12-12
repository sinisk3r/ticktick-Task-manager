"""
LangGraph Agent Implementation for Context Task Copilot.

This module provides the ReAct agent using LangGraph's prebuilt create_react_agent.
Replaces the custom planner.py in Phase 3 of the LangChain migration.

Key Features:
- ReAct (Reasoning + Acting) pattern for tool calling
- Built-in conversation memory via MemorySaver checkpointer
- Automatic tool binding with database injection
- Streaming support for real-time responses
- Thread-based conversation tracking

Architecture:
    User Query -> create_agent() -> ReAct Agent -> Tools (with db injection) -> Response

Usage:
    from app.agent.graph import create_agent
    from app.core.database import get_db

    async with get_db() as db:
        agent = create_agent(user_id=1, db=db)
        result = await agent.ainvoke(
            {"messages": [("user", "Create a task for team meeting")]},
            config={"configurable": {"thread_id": "user-1-session"}}
        )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_factory import get_llm, get_llm_for_user
from app.agent.tools import (
    fetch_tasks,
    fetch_task,
    create_task,
    update_task,
    complete_task,
    delete_task,
    quick_analyze_task,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# System Message - Agent Personality & Instructions
# -----------------------------------------------------------------------------

SYSTEM_MESSAGE = """You are Context, an agentic task copilot designed to help users manage their tasks efficiently.

**Your capabilities:**
- Create, update, complete, and delete tasks
- List and filter tasks by status or quadrant
- Analyze task urgency and importance
- Provide task management advice and insights

**When to call tools:**
- User wants to create/add a task → use `create_task`
- User wants to update/modify a task → use `update_task`
- User wants to complete/finish a task → use `complete_task`
- User wants to delete/remove a task → use `delete_task`
- User wants to list/show/view tasks → use `fetch_tasks`
- User asks about a specific task → use `fetch_task`
- User wants analysis on a task description → use `quick_analyze_task`

**Response style:**
- Keep responses concise (1-3 sentences) unless more detail is needed
- Be friendly and conversational
- Confirm actions clearly ("Created task 'X'", "Updated task Y")
- For greetings or general questions, respond naturally without calling tools
- If you need more information, ask clarifying questions

**Task creation guidelines:**
- Extract clear, concise titles (max 120 chars, no quotes)
- Only add description if it provides meaningful context beyond the title
- Infer priority from user's language (urgent → 5, important → 3, normal → 0)
- Extract due dates from natural language ("tomorrow", "next Friday", etc.)
- Suggest tags based on task type (e.g., "meeting", "bug", "review")

**Remember:**
- You have access to the user's full task list - use it when relevant
- Ask for confirmation before destructive actions (delete)
- Be proactive about suggesting task organization
- Learn from conversation context (previous messages)
"""


# -----------------------------------------------------------------------------
# Agent Factory
# -----------------------------------------------------------------------------


async def create_agent(
    user_id: int,
    db: AsyncSession,
    llm: Optional[BaseChatModel] = None,
    enable_memory: bool = True,
) -> Any:
    """
    Create a LangGraph ReAct agent with tool calling and conversation memory.

    This function instantiates a LangGraph agent that can:
    1. Understand user intent from natural language
    2. Call appropriate tools to fulfill requests
    3. Maintain conversation context across messages
    4. Stream responses in real-time

    Args:
        user_id: User ID for tool execution context (required)
        db: Database session for tool access (required)
        llm: Optional LLM instance (defaults to get_llm() from factory)
        enable_memory: Whether to enable conversation memory (default: True)

    Returns:
        Configured LangGraph agent (CompiledStateGraph)

    Raises:
        ValueError: If user_id is invalid or db is None
        RuntimeError: If LLM initialization fails

    Example:
        >>> from app.core.database import get_db
        >>> from app.agent.graph import create_agent
        >>>
        >>> async with get_db() as db:
        ...     agent = create_agent(user_id=1, db=db)
        ...
        ...     # Invoke with conversation tracking
        ...     result = await agent.ainvoke(
        ...         {"messages": [("user", "Create a task for team sync")]},
        ...         config={"configurable": {"thread_id": "user-1"}}
        ...     )
        ...
        ...     # Stream responses
        ...     async for event in agent.astream_events(
        ...         {"messages": [("user", "List my tasks")]},
        ...         config={"configurable": {"thread_id": "user-1"}},
        ...         version="v2"
        ...     ):
        ...         print(event)

    Thread Management:
        The agent uses thread_id in the config to maintain conversation state.
        Use a consistent thread_id for the same conversation:
        - Format: "user-{user_id}" for default session
        - Format: "user-{user_id}-{session_id}" for multiple sessions

    Tool Injection:
        The user_id and db parameters are automatically injected into all tool
        calls via RunnableConfig. Tools receive these via InjectedToolArg, but
        the LLM only sees the visible parameters in tool schemas.

        IMPORTANT: When invoking the agent, you must pass user_id and db in the
        config dict for tool injection to work correctly.
    """

    # Validate inputs
    if not user_id or user_id <= 0:
        raise ValueError(f"Invalid user_id: {user_id}. Must be a positive integer.")

    if db is None:
        raise ValueError("Database session (db) cannot be None")

    # Get LLM instance (use provided or create from user settings)
    if llm is None:
        try:
            llm = await get_llm_for_user(user_id=user_id, db=db)
            logger.info(f"Created LLM instance from user settings (user_id={user_id})")
        except Exception as e:
            logger.error(f"Failed to create LLM instance: {e}")
            raise RuntimeError(f"LLM initialization failed: {e}") from e

    # Import and prepare tools
    # Note: user_id and db will be injected at runtime via RunnableConfig
    # The @tool decorator with InjectedToolArg ensures these params are hidden from LLM
    tools_list = [
        fetch_tasks,
        fetch_task,
        create_task,
        update_task,
        complete_task,
        delete_task,
        quick_analyze_task,
    ]

    logger.info(
        f"Configured {len(tools_list)} tools for agent (user_id={user_id}): "
        f"{[t.name for t in tools_list]}"
    )

    # Create checkpointer for conversation memory
    checkpointer = MemorySaver() if enable_memory else None

    if enable_memory:
        logger.debug(f"Agent memory enabled for user_id={user_id}")
    else:
        logger.debug(f"Agent memory disabled for user_id={user_id}")

    # Create ReAct agent with LangGraph
    try:
        agent = create_react_agent(
            model=llm,
            tools=tools_list,
            state_modifier=SYSTEM_MESSAGE,
            checkpointer=checkpointer,
        )

        # Store user_id and db on agent for helper functions
        # This allows invoke_agent and stream_agent to inject them automatically
        agent._user_id = user_id  # type: ignore
        agent._db = db  # type: ignore

        logger.info(
            f"Successfully created LangGraph agent for user_id={user_id} "
            f"with {len(tools_list)} tools and memory={'enabled' if enable_memory else 'disabled'}"
        )

        return agent

    except Exception as e:
        logger.error(f"Failed to create LangGraph agent for user_id={user_id}: {e}")
        raise RuntimeError(f"Agent creation failed: {e}") from e


# -----------------------------------------------------------------------------
# Agent Invocation Helpers
# -----------------------------------------------------------------------------


async def invoke_agent(
    agent: Any,
    user_message: str,
    thread_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Invoke the agent with a user message and return the response.

    This is a convenience wrapper around agent.ainvoke() that handles
    message formatting, config setup, and parameter injection.

    Args:
        agent: LangGraph agent instance from create_agent()
        user_message: User's input message
        thread_id: Conversation thread ID for memory tracking
        config: Optional additional config (merged with thread_id)

    Returns:
        Agent response dict with messages and metadata

    Example:
        >>> agent = create_agent(user_id=1, db=db)
        >>> response = await invoke_agent(
        ...     agent=agent,
        ...     user_message="Create a task for code review",
        ...     thread_id="user-1"
        ... )
        >>> print(response["messages"][-1].content)
    """

    # Merge config with thread_id and tool injection params
    invoke_config = config or {}
    invoke_config.setdefault("configurable", {})["thread_id"] = thread_id

    # Inject user_id and db for tools (if stored on agent)
    if hasattr(agent, "_user_id"):
        invoke_config["user_id"] = agent._user_id
    if hasattr(agent, "_db"):
        invoke_config["db"] = agent._db

    # Format input for agent
    agent_input = {"messages": [("user", user_message)]}

    try:
        result = await agent.ainvoke(agent_input, config=invoke_config)
        logger.debug(f"Agent invoked successfully (thread={thread_id})")
        return result
    except Exception as e:
        logger.error(f"Agent invocation failed (thread={thread_id}): {e}")
        raise


async def stream_agent(
    agent: Any,
    user_message: str,
    thread_id: str,
    config: Optional[Dict[str, Any]] = None,
):
    """
    Stream agent responses in real-time.

    This generator yields events as the agent processes the request,
    allowing for real-time UI updates (e.g., SSE endpoints).

    Args:
        agent: LangGraph agent instance from create_agent()
        user_message: User's input message
        thread_id: Conversation thread ID for memory tracking
        config: Optional additional config (merged with thread_id)

    Yields:
        Agent events (tool calls, messages, state updates)

    Example:
        >>> agent = create_agent(user_id=1, db=db)
        >>> async for event in stream_agent(
        ...     agent=agent,
        ...     user_message="List my urgent tasks",
        ...     thread_id="user-1"
        ... ):
        ...     print(f"Event: {event['event']}, Data: {event.get('data')}")
    """

    # Merge config with thread_id and tool injection params
    stream_config = config or {}
    stream_config.setdefault("configurable", {})["thread_id"] = thread_id

    # Inject user_id and db for tools (if stored on agent)
    if hasattr(agent, "_user_id"):
        stream_config["user_id"] = agent._user_id
    if hasattr(agent, "_db"):
        stream_config["db"] = agent._db

    # Format input for agent
    agent_input = {"messages": [("user", user_message)]}

    try:
        async for event in agent.astream_events(
            agent_input,
            config=stream_config,
            version="v2",  # Use v2 for better streaming support
        ):
            yield event

        logger.debug(f"Agent stream completed (thread={thread_id})")

    except Exception as e:
        logger.error(f"Agent streaming failed (thread={thread_id}): {e}")
        raise


# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------

__all__ = [
    "create_agent",
    "invoke_agent",
    "stream_agent",
    "SYSTEM_MESSAGE",
]
