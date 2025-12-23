"""
Custom state schema for the Context agent.

This defines the state structure used by the LangGraph agent, extending
the base AgentState with user-specific context for personalization.
"""
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class CustomState(TypedDict):
    """
    State schema for the Context conversational agent.

    This extends the standard agent state with user-specific context:
    - messages: Conversation history (standard LangGraph)
    - user_id: Current user for database operations
    - user_preferences: Loaded from Profile and UserMemory
    - work_style: User's work approach (for task suggestions)
    """

    # Standard LangGraph message history with reducer
    # The add_messages reducer merges new messages into the list
    messages: Annotated[list[BaseMessage], add_messages]

    # User context for personalization
    user_id: int
    user_preferences: dict
    work_style: str
