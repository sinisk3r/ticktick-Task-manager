"""Simple planner that turns a goal into tool calls and streams events."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx  # type: ignore
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.agent.dispatcher import AgentDispatcher, ConfirmationRequired
from app.agent.tools import TOOL_REGISTRY
from app.services import OllamaService

logger = logging.getLogger(__name__)


class CleanResponse(BaseModel):
    """Structured output model for final assistant messages."""

    message: str = Field(
        ...,
        max_length=240,
        description="User-facing message, 1-2 sentences max, no internal reasoning",
    )


class AgentPlanner:
    """Plan and execute tool calls with a small step budget."""

    def __init__(
        self,
        dispatcher: Optional[AgentDispatcher] = None,
        max_steps: int = 5,
        max_runtime_seconds: int = 20,
        parallel_cap: int = 2,
    ):
        self.dispatcher = dispatcher or AgentDispatcher()
        self.max_steps = max_steps
        self.max_runtime_seconds = max_runtime_seconds
        self.parallel_cap = parallel_cap

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _call_llm_with_retry(self, url: str, payload: dict) -> dict:
        """Call Ollama API with automatic retry on transient errors."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    async def run(
        self,
        goal: str,
        *,
        user_id: int,
        db,
        context: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        trace_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield agent events as a stream for SSE."""
        trace_id = trace_id or str(uuid.uuid4())

        # Emit an initial thinking event (no hardcoded goal text) so the UI shows activity immediately
        yield {"event": "thinking", "data": {"trace_id": trace_id, "text": ""}}

        plan = await self._build_plan(goal, context=context, user_id=user_id)
        steps = plan.get("steps", []) if plan else []
        message = plan.get("message") if plan else None
        user_summaries: List[str] = []

        if not steps:
            # No tool calls needed: stream conversational LLM reply (thinking + final message)
            async for evt in self._llm_reply_stream(goal, context, trace_id):
                yield evt
            yield {"event": "done", "data": {"trace_id": trace_id}}
            return

        # Enforce step budget
        steps = steps[: self.max_steps]

        for idx, step in enumerate(steps, start=1):
            tool_name = step.get("tool")
            raw_args = step.get("args") or {}
            summary = step.get("summary") or f"Step {idx}: {tool_name}"

            # Ensure user scope
            raw_args.setdefault("user_id", user_id)

            yield {
                "event": "step",
                "data": {"trace_id": trace_id, "step": idx, "summary": summary},
            }

            yield {
                "event": "tool_request",
                "data": {
                    "trace_id": trace_id,
                    "tool": tool_name,
                    "args": raw_args,
                    "confirmation_required": step.get("confirmation_required", False),
                },
            }

            if dry_run:
                yield {
                    "event": "tool_result",
                    "data": {
                        "trace_id": trace_id,
                        "tool": tool_name,
                        "result": {"dry_run": True, "summary": summary},
                    },
                }
                continue

            # Schema validators and hooks now handle all input validation and cleaning
            try:
                hook_context = {"user_id": user_id, "context": context}
                result = await self.dispatcher.dispatch(tool_name, raw_args, db, trace_id, hook_context)
            except ConfirmationRequired:
                # Confirmations disabled for now; proceed is not expected
                yield {
                    "event": "error",
                    "data": {"trace_id": trace_id, "message": "Unexpected confirmation request."},
                }
                return
            except Exception as exc:  # noqa: BLE001
                logger.exception("Agent step failed (trace_id=%s)", trace_id)
                yield {
                    "event": "error",
                    "data": {"trace_id": trace_id, "message": str(exc)},
                }
                return

            yield {
                "event": "tool_result",
                "data": {
                    "trace_id": trace_id,
                    "tool": tool_name,
                    "result": result,
                },
            }

            if result.get("summary"):
                user_summaries.append(str(result["summary"]))
                yield {
                    "event": "message",
                    "data": {
                        "trace_id": trace_id,
                        "message": result["summary"],
                        "payload": {k: v for k, v in result.items() if k not in {"summary"}},
                    },
                }

        # Final wrap-up: ask the LLM to summarize outcomes conversationally
        if user_summaries:
            final_message = await self._build_final_message(goal, user_summaries)
            yield {
                "event": "message",
                "data": {
                    "trace_id": trace_id,
                    "message": final_message,
                },
            }

        yield {"event": "done", "data": {"trace_id": trace_id}}

    async def _build_plan(
        self, goal: str, *, context: Optional[Dict[str, Any]], user_id: int
    ) -> Dict[str, Any]:
        """
        Ask the model for a short plan. If unavailable, fall back to heuristics.
        """
        heuristic = self._heuristic_plan(goal, user_id=user_id, context=context)
        # If environment or health check disables LLM, stick to heuristic
        if os.getenv("AGENT_DISABLE_LLM") == "1":
            return heuristic

        ollama = OllamaService()
        if not await ollama.health_check():
            return heuristic

        # Build tool descriptions with examples
        tool_info = []
        for name, meta in TOOL_REGISTRY.items():
            desc = f"{name}: {meta['description']}"
            if examples := meta.get("examples"):
                desc += f"\n  Examples: {json.dumps(examples[0])}"
            tool_info.append(desc)

        system_prompt = """You are Context, an agentic task copilot. Plan minimal steps (1-3 max).

CRITICAL: ALWAYS return valid JSON with this exact structure:
{
  "message": "brief planning note",
  "steps": [array of tool calls OR empty array]
}

DECISION TREE - When to call tools:
1. User says "create", "add task", "make task" → MUST call create_task
2. User says "complete", "finish", "done", "mark done" → MUST call complete_task
3. User says "show", "list", "what tasks", "my tasks" → MUST call fetch_tasks
4. User says "how should I", "advice", "what do you think" → return empty steps array
5. Ambiguous or unclear → return empty steps array

CRITICAL RULES:
1. If user mentions creating a task, ALWAYS include create_task in steps
2. For create_task args:
   - title: max 120 chars, NO quotes, concise, descriptive
   - description: MUST differ from title OR be null (don't duplicate)
   - Extract due_date from text (ISO 8601 format if mentioned)
   - Extract priority (0/1/3/5) if user mentions urgency
   - Extract tags from context
3. Always include user_id in ALL tool args
4. Keep steps array minimal (usually 1-2 tools max)
5. Respond with ONLY valid JSON, no extra text

EXAMPLE TOOL CALL:
{"tool": "create_task", "args": {"user_id": 1, "title": "Review PR #456", "description": "Full code review focusing on security", "ticktick_tags": ["code-review"]}}

EXAMPLE BAD (description duplicates title):
{"tool": "create_task", "args": {"title": "Review PR", "description": "Review PR"}}"""

        user_prompt = {
            "goal": goal,
            "context": context or {},
            "tools": tool_info,
            "required_shape": {
                "message": "short planning note",
                "steps": [
                    {
                        "tool": "name from tools list",
                        "summary": "why this tool",
                        "confirmation_required": False,
                        "args": {"user_id": user_id},
                    }
                ],
            },
        }

        payload = {
            "model": ollama.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_prompt),
                },
            ],
            "stream": False,
            "format": "json",
            "think": False,
            "options": {"temperature": 0.2, "num_predict": 1000},  # Increased for complete JSON
        }

        try:
            data = await self._call_llm_with_retry(f"{ollama.base_url}/api/chat", payload)
            message = data.get("message", {}) if isinstance(data, dict) else {}
            content = message.get("content") or message.get("thinking") or ""
            if not content:
                return heuristic
            parsed = json.loads(content)
            # Log what we successfully parsed for debugging
            steps = parsed.get("steps") or []
            logger.debug(
                "LLM plan parsed successfully: message=%s, num_steps=%d",
                parsed.get("message", "")[:100],
                len(steps)
            )
            normalized_steps = []
            for step in steps:
                tool = step.get("tool")
                args = step.get("args") or {}
                args.setdefault("user_id", user_id)
                normalized_steps.append(
                    {
                        "tool": tool,
                        "args": args,
                        "summary": step.get("summary"),
                        "confirmation_required": step.get("confirmation_required", False),
                    }
                )

            return {"message": parsed.get("message"), "steps": normalized_steps}
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM planning failed; falling back to heuristic: %s", exc)
            # Log the actual response for debugging
            if 'data' in locals():
                logger.debug("Failed LLM response data: %s", str(data)[:500])
            if 'content' in locals():
                logger.debug("Failed to parse content: %s", str(content)[:500])
            return heuristic

    def _heuristic_plan(
        self, goal: str, *, user_id: int, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Very small deterministic planner used when LLM is unavailable.
        """
        goal_lower = goal.lower()
        steps: List[Dict[str, Any]] = []

        if "delete" in goal_lower or "remove" in goal_lower:
            task_id = context.get("task_id") if context else None
            if task_id:
                steps.append(
                    {
                        "tool": "delete_task",
                        "summary": "Request deletion of the task (confirmation required).",
                        "confirmation_required": True,
                        "args": {"task_id": task_id, "confirm": False},
                    }
                )
        elif "complete" in goal_lower:
            task_id = context.get("task_id") if context else None
            if task_id:
                steps.append(
                    {
                        "tool": "complete_task",
                        "summary": "Complete the selected task.",
                        "args": {"task_id": task_id},
                    }
                )
        elif "create" in goal_lower or "add task" in goal_lower or "make a task" in goal_lower:
            title = (context or {}).get("title") if context else None
            safe_title = title or goal or "New task"
            steps.append(
                {
                    "tool": "create_task",
                    "summary": "Create a new task from the goal.",
                    "args": {"title": safe_title[:500], "description": None},
                }
            )
        # else: pure advice / no tools

        return {
            "message": "Using fallback heuristic plan.",
            "steps": steps,
        }

    async def _build_final_message(self, goal: str, summaries: List[str]) -> str:
        """
        Let the LLM craft the final user-facing wrap-up instead of hardcoding text.
        """
        ollama = OllamaService()
        if await ollama.health_check():
            system_prompt = (
                "You are Context, a helpful copilot. "
                "Summarize the completed actions in one concise, plain-English sentence. "
                "Be brief and confirm what was done. End by inviting next steps. "
                "Put all reasoning in thinking; keep the final content short. "
                "If the model is small (e.g., qwen3:4b), keep thinking extremely brief."
            )
            user_content = json.dumps(
                {
                    "goal": goal,
                    "actions_completed": summaries,
                },
                ensure_ascii=False,
            )
            payload = {
                "model": ollama.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "stream": False,
                "think": False if self._is_small_model(ollama.model) else True,
                "format": None,
                "options": {"temperature": 0.3, "num_predict": 200},
            }
            try:
                async with httpx.AsyncClient(timeout=ollama.timeout) as client:
                    resp = await client.post(f"{ollama.base_url}/api/chat", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    message = data.get("message", {}) if isinstance(data, dict) else {}
                    content = message.get("content") or message.get("thinking") or ""
                    if content:
                        return content.strip()
            except Exception:
                pass

        # Fallback if LLM unavailable
        return " ".join(summaries) + " What else should we work on today?"

    async def _llm_reply_stream(
        self, goal: str, context: Optional[Dict[str, Any]], trace_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream conversational reply with thinking tokens (as 'thinking' events) and final message.
        Uses structured output to enforce brief, reasoning-free responses.
        """
        ollama = OllamaService()
        use_stream = await ollama.health_check()
        system_prompt = """You are Context, a helpful life assistant.

Respond naturally about tasks, schedule, or wellbeing.
- Simple greetings: 1-2 sentences
- Questions needing context: 2-4 sentences with helpful details
- Complex planning requests: Be thorough but concise

RULES:
1. Never include meta-reasoning or thinking process in final message
2. Be specific and actionable
3. Provide helpful details when relevant"""
        user_payload = {
            "goal": goal,
            "context": context or {},
        }

        if use_stream:
            # Stream using Ollama chat for conversational replies
            # Use think: False to keep responses concise without verbose reasoning
            payload = {
                "model": ollama.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
                "stream": True,
                "think": False,  # Keep thinking internal, show only final reply
                "format": None,
                "options": {"temperature": 0.4, "num_predict": 600},  # Increased for fuller responses
            }
            try:
                async with httpx.AsyncClient(timeout=ollama.timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{ollama.base_url}/api/chat",
                        json=payload,
                    ) as response:
                        response.raise_for_status()
                        buffer = ""
                        content_accum = ""
                        async for chunk in response.aiter_text():
                            buffer += chunk
                            while "\n" in buffer:
                                raw_line, buffer = buffer.split("\n", 1)
                                raw_line = raw_line.strip()
                                if not raw_line:
                                    continue
                                try:
                                    outer_obj = json.loads(raw_line)
                                except json.JSONDecodeError:
                                    continue
                                message = outer_obj.get("message", {})
                                thinking_delta = message.get("thinking", "")
                                content_delta = message.get("content", "")
                                if thinking_delta:
                                    yield {
                                        "event": "thinking",
                                        "data": {"trace_id": trace_id, "delta": thinking_delta},
                                    }
                                if content_delta:
                                    content_accum += content_delta
                        # Flush final message (allow full response, up to 1200 chars)
                        final_msg = content_accum.strip()[:1200]
                        if not final_msg:
                            # If LLM returned no content, provide default helpful message
                            final_msg = "I'm here to help. What would you like to do?"
                        yield {"event": "message", "data": {"trace_id": trace_id, "message": final_msg}}
                        return
            except Exception:
                pass

        # Fallback non-streaming or if LLM unavailable
        # Don't echo user's goal - provide helpful error message instead
        fallback_msg = "I'm having trouble processing that request. Could you rephrase or try a simpler command?"
        yield {"event": "message", "data": {"trace_id": trace_id, "message": fallback_msg}}

    def _is_small_model(self, model_name: str) -> bool:
        lower = (model_name or "").lower()
        return "qwen3:4b" in lower or "qwen-3" in lower


__all__ = ["AgentPlanner", "CleanResponse"]

