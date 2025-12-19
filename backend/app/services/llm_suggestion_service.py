"""
LangChain-based LLM Suggestion Service for multi-provider support.

This service replaces the Ollama-specific suggestion service with a provider-agnostic
implementation using LangChain. Supports all providers: Ollama, Claude, GPT-4, OpenRouter.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from pydantic import BaseModel

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm_factory import get_llm_for_user

logger = logging.getLogger(__name__)


class TaskAnalysis(BaseModel):
    """Result of analyzing a task"""
    urgency: int  # 1-10
    importance: int  # 1-10
    quadrant: str  # Q1, Q2, Q3, Q4
    reasoning: str


def load_prompt_template(version: str = "v1") -> str:
    """Load versioned prompt template from file"""
    prompt_path = Path(__file__).parent.parent / "prompts" / f"task_analysis_suggestions_{version}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text()


class LLMSuggestionService:
    """
    Multi-provider LLM suggestion service using LangChain.

    Supports: Ollama, Claude (Anthropic), GPT-4 (OpenAI), OpenRouter
    """

    def __init__(self, llm: Optional[BaseChatModel] = None):
        """
        Initialize suggestion service with a LangChain chat model.

        Args:
            llm: Pre-configured LangChain chat model. If None, will need to be provided per-request.
        """
        self.llm = llm

    @classmethod
    async def for_user(cls, user_id: int, db: AsyncSession) -> "LLMSuggestionService":
        """
        Create a suggestion service configured for a specific user.

        Args:
            user_id: User ID to fetch LLM configuration for
            db: Database session

        Returns:
            LLMSuggestionService instance with user's configured LLM
        """
        llm = await get_llm_for_user(user_id, db)
        logger.info(f"Created LLMSuggestionService for user {user_id} with model: {llm.__class__.__name__}")
        return cls(llm=llm)

    async def analyze_task(
        self,
        description: str,
        profile_context: Optional[str] = None
    ) -> TaskAnalysis:
        """
        Analyze a task description and return urgency/importance scores.

        Uses Eisenhower Matrix quadrants:
        - Q1: Urgent & Important (Do First)
        - Q2: Not Urgent & Important (Schedule)
        - Q3: Urgent & Not Important (Delegate)
        - Q4: Not Urgent & Not Important (Eliminate)
        """
        if not self.llm:
            raise ValueError("LLM not configured. Use for_user() to create service instance.")

        system_message = (
            "You are a task analysis assistant. "
            "Respond ONLY with JSON containing integer fields "
            "urgency (1-10) and importance (1-10), plus a brief reasoning string "
            "under 200 characters. Consider provided user context if present."
        )

        context_block = f"User context: {profile_context}\n\n" if profile_context else ""
        user_message = (
            f"""{context_block}Analyze this task:
{description}

Return strictly valid JSON in this shape:
{{"urgency": <int 1-10>, "importance": <int 1-10>, "reasoning": "<brief explanation>"}}"""
        )

        try:
            # Try to bind response format if supported (OpenAI, Anthropic)
            # Fall back to string parsing for Ollama
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message),
            ]

            response = await self.llm.ainvoke(messages)
            llm_text = response.content

            logger.debug(f"LLM response for task analysis: {llm_text[:200]}")

            # Parse JSON response
            try:
                llm_output = json.loads(llm_text)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it has extra text
                import re
                json_match = re.search(r'\{[^{}]*"urgency"[^{}]*\}', llm_text, re.DOTALL)
                if json_match:
                    llm_output = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse LLM response as JSON: {llm_text}")

            # Extract and validate scores
            urgency = int(llm_output.get("urgency", 5))
            importance = int(llm_output.get("importance", 5))
            reasoning = llm_output.get("reasoning", "No reasoning provided")

            # Clamp to valid range
            urgency = max(1, min(10, urgency))
            importance = max(1, min(10, importance))

            # Calculate Eisenhower quadrant
            quadrant = self._calculate_quadrant(urgency, importance)

            return TaskAnalysis(
                urgency=urgency,
                importance=importance,
                quadrant=quadrant,
                reasoning=reasoning
            )

        except Exception as e:
            logger.error(f"Failed to analyze task: {e}")
            raise

    def _calculate_quadrant(self, urgency: int, importance: int) -> str:
        """
        Determine Eisenhower Matrix quadrant.

        Threshold is 7 (scores >= 7 are considered high)
        """
        if urgency >= 7 and importance >= 7:
            return "Q1"  # Do First
        elif urgency < 7 and importance >= 7:
            return "Q2"  # Schedule
        elif urgency >= 7 and importance < 7:
            return "Q3"  # Delegate
        else:
            return "Q4"  # Eliminate

    async def generate_suggestions(
        self,
        task_data: dict,
        project_context: Optional[dict] = None,
        related_tasks: Optional[List[dict]] = None,
        user_workload: Optional[dict] = None,
        stream: bool = False,
    ) -> dict:
        """
        Generate AI suggestions for a task (not direct changes).

        Args:
            task_data: Task details (title, description, due_date, current priority, etc.)
            project_context: Project info (name, other tasks in project)
            related_tasks: Similar or related tasks for context
            user_workload: User's current task load and capacity
            stream: Whether to stream the response (not supported yet)

        Returns:
            dict with "analysis" and "suggestions" keys
        """
        if not self.llm:
            raise ValueError("LLM not configured. Use for_user() to create service instance.")

        if stream:
            raise NotImplementedError("Streaming not yet supported for LangChain-based suggestions")

        # Load prompt template
        prompt_template = load_prompt_template("v1")

        # Build context JSON
        task_context = {
            "title": task_data.get("title"),
            "description": task_data.get("description", ""),
            "due_date": task_data.get("due_date").isoformat() if task_data.get("due_date") else None,
            "ticktick_priority": task_data.get("ticktick_priority", 0),
            "project_name": project_context.get("name") if project_context else None,
            "ticktick_tags": task_data.get("ticktick_tags", []),
            "start_date": task_data.get("start_date").isoformat() if task_data.get("start_date") else None,
            "repeat_flag": task_data.get("repeat_flag"),
            "reminder_time": task_data.get("reminder_time").isoformat() if task_data.get("reminder_time") else None,
            "time_estimate": task_data.get("time_estimate"),
            "all_day": task_data.get("all_day", False),
            "related_tasks_in_project": related_tasks or [],
            "user_workload": user_workload or {}
        }

        # Substitute into prompt
        final_prompt = prompt_template.replace("{task_json}", json.dumps(task_context, indent=2))

        try:
            system_message = (
                "You are a task analysis assistant that generates suggestions for task organization. "
                "Respond ONLY with valid JSON in the exact format requested. "
                "Do NOT echo back the input data."
            )

            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=final_prompt)
            ]

            logger.debug(f"Generating suggestions with {self.llm.__class__.__name__}")

            response = await self.llm.ainvoke(messages)
            llm_text = response.content

            logger.debug(f"LLM response (first 500 chars): {llm_text[:500]}")

            # Parse JSON response
            try:
                suggestion_data = json.loads(llm_text)
            except json.JSONDecodeError:
                # Try to extract JSON from the response if it has extra text
                import re
                json_match = re.search(r'\{.*"analysis".*\}', llm_text, re.DOTALL)
                if json_match:
                    suggestion_data = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse LLM response as JSON: {llm_text[:500]}")

            # Validate structure
            if "analysis" not in suggestion_data or "suggestions" not in suggestion_data:
                raise ValueError(
                    f"Invalid suggestion format. Expected 'analysis' and 'suggestions' keys. "
                    f"Got: {list(suggestion_data.keys())}"
                )

            return suggestion_data

        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            raise

    async def stream_suggestions(
        self,
        task_data: dict,
        project_context: Optional[dict] = None,
        related_tasks: Optional[List[dict]] = None,
        user_workload: Optional[dict] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream AI suggestions as NDJSON lines.

        Note: Streaming support for LangChain providers is limited.
        This is a placeholder for future implementation.
        """
        raise NotImplementedError(
            "Streaming suggestions not yet implemented for LangChain-based service. "
            "Use generate_suggestions() with stream=False instead."
        )
