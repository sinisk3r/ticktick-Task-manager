"""Dispatcher that validates tool inputs and invokes tool callables."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.hooks import run_hooks
from app.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


class ConfirmationRequired(Exception):
    """Raised when a destructive tool is invoked without confirmation."""

    def __init__(self, tool_name: str, message: str = "Confirmation required", payload: Optional[dict] = None):
        super().__init__(message)
        self.tool_name = tool_name
        self.payload = payload or {}


class AgentDispatcher:
    """Map tool names to callables with validation and safety checks."""

    def __init__(self, registry: dict[str, dict[str, Any]] | None = None):
        self.registry = registry or TOOL_REGISTRY

    async def dispatch(
        self,
        tool_name: str,
        raw_payload: Dict[str, Any],
        db: AsyncSession,
        trace_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if tool_name not in self.registry:
            raise ValueError(f"Unknown tool: {tool_name}")

        entry = self.registry[tool_name]
        model_cls = entry["model"]
        callable_fn = entry["callable"]
        requires_confirmation = entry.get("requires_confirmation", False)

        # Run pre-tool hooks for validation and auto-fixes
        hook_context = context or {}
        hook_result = await run_hooks(tool_name, raw_payload, hook_context)

        if hook_result.action == "deny":
            error_msg = hook_result.reason or "Tool execution denied by hook"
            logger.warning("Hook denied tool %s (trace %s): %s", tool_name, trace_id, error_msg)
            return {"error": error_msg, "summary": f"Cannot execute: {error_msg}"}

        # Use modified args if hook modified them
        if hook_result.action == "modify" and hook_result.modified_args:
            logger.info("Hook modified args for %s: %s", tool_name, hook_result.reason)
            raw_payload = hook_result.modified_args

        # Phase 2 compatibility: Handle both old (Pydantic) and new (@tool) formats
        if model_cls is None:
            # New @tool format: callable is a LangChain tool, call directly with db injected
            logger.info("Executing tool %s (LangChain @tool format, trace_id=%s)", tool_name, trace_id)
            # Add db to raw_payload for injection
            raw_payload_with_db = {**raw_payload, "db": db}
            result = await callable_fn.ainvoke(raw_payload_with_db)
            return result
        else:
            # Old format: Validate with Pydantic schema
            try:
                payload = model_cls(**raw_payload)
            except ValidationError as exc:
                logger.warning("Validation failed for tool %s (trace %s): %s", tool_name, trace_id, exc)
                # Return error instead of raising to keep stream alive
                return {
                    "error": f"Invalid input: {str(exc)}",
                    "summary": f"Tool {tool_name} failed validation",
                }

            if requires_confirmation and not getattr(payload, "confirm", False):
                raise ConfirmationRequired(
                    tool_name,
                    message="Confirmation required for destructive action",
                    payload=raw_payload,
                )

            logger.info("Executing tool %s (old format, trace_id=%s)", tool_name, trace_id)
            result = await callable_fn(payload, db)
            return result


__all__ = ["AgentDispatcher", "ConfirmationRequired"]

