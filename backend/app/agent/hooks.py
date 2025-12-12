"""
Pre-tool execution hooks for validation and safety.

Hooks run before tool dispatch and can:
- Allow: Continue with tool execution
- Deny: Block execution with a reason
- Modify: Change tool arguments before execution
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HookResult(BaseModel):
    """Result from a pre-tool hook."""

    action: Literal["allow", "deny", "modify"] = "allow"
    reason: Optional[str] = None
    modified_args: Optional[Dict[str, Any]] = None


async def validate_no_duplicate_title_desc(
    tool_name: str, args: Dict[str, Any], context: Dict[str, Any]
) -> HookResult:
    """
    Prevent create_task from having identical title and description.
    The Pydantic validator should catch this, but this hook provides extra safety.
    """
    if tool_name != "create_task":
        return HookResult(action="allow")

    title = args.get("title", "").strip()
    description = args.get("description", "")

    if not description:
        return HookResult(action="allow")

    # Check for exact match
    if description.strip() == title:
        return HookResult(
            action="deny",
            reason="Description cannot be identical to title. Omit description if no additional context.",
        )

    # Check for case-insensitive match
    if description.strip().lower() == title.lower():
        # Auto-fix by removing description
        modified = args.copy()
        modified["description"] = None
        return HookResult(
            action="modify",
            modified_args=modified,
            reason="Removed description that only differs by case from title",
        )

    return HookResult(action="allow")


async def auto_clean_inputs(
    tool_name: str, args: Dict[str, Any], context: Dict[str, Any]
) -> HookResult:
    """
    Automatically clean common input issues:
    - Strip whitespace
    - Remove surrounding quotes from title
    - Normalize empty strings to None
    """
    modified = False
    cleaned_args = args.copy()

    # Clean title field if present
    if "title" in cleaned_args and isinstance(cleaned_args["title"], str):
        original = cleaned_args["title"]
        cleaned = original.strip().strip('"').strip("'")
        if cleaned != original:
            cleaned_args["title"] = cleaned
            modified = True

    # Clean description field if present
    if "description" in cleaned_args and isinstance(cleaned_args["description"], str):
        original = cleaned_args["description"]
        cleaned = original.strip()
        if not cleaned or cleaned == "":
            cleaned_args["description"] = None
            modified = True
        elif cleaned != original:
            cleaned_args["description"] = cleaned
            modified = True

    if modified:
        return HookResult(
            action="modify",
            modified_args=cleaned_args,
            reason="Auto-cleaned whitespace and quotes from inputs",
        )

    return HookResult(action="allow")


async def require_confirmation(
    tool_name: str, args: Dict[str, Any], context: Dict[str, Any]
) -> HookResult:
    """
    Require explicit confirmation for destructive operations.
    Currently disabled per project policy, but structure is in place.
    """
    # Destructive tools that would require confirmation
    requires_confirm = {"delete_task", "send_email", "create_focus_block"}

    if tool_name not in requires_confirm:
        return HookResult(action="allow")

    # For now, confirmations are disabled, so allow
    # In future, check for args.get("confirm") == True
    return HookResult(action="allow")


async def validate_task_ownership(
    tool_name: str, args: Dict[str, Any], context: Dict[str, Any]
) -> HookResult:
    """
    Ensure user_id is present and matches the authenticated user.
    This prevents agents from accessing other users' data.
    """
    if "user_id" not in args:
        return HookResult(
            action="deny",
            reason="Missing user_id in tool arguments - required for all tools",
        )

    # Get authenticated user from context
    auth_user_id = context.get("user_id")
    if not auth_user_id:
        logger.warning("No user_id in context for ownership validation")
        return HookResult(action="allow")  # Let dispatcher handle

    # Ensure tool user_id matches authenticated user
    if args["user_id"] != auth_user_id:
        return HookResult(
            action="deny",
            reason=f"User ID mismatch: cannot access data for user {args['user_id']}",
        )

    return HookResult(action="allow")


# Registry of hooks to run for each tool
# Hooks run in order; first deny/modify wins
HOOK_REGISTRY: Dict[str, list] = {
    "create_task": [
        auto_clean_inputs,
        validate_no_duplicate_title_desc,
        validate_task_ownership,
    ],
    "complete_task": [
        validate_task_ownership,
    ],
    "delete_task": [
        validate_task_ownership,
        require_confirmation,
    ],
    "fetch_tasks": [
        validate_task_ownership,
    ],
    "fetch_task": [
        validate_task_ownership,
    ],
    "quick_analyze_task": [
        validate_task_ownership,
    ],
}


async def run_hooks(
    tool_name: str, args: Dict[str, Any], context: Optional[Dict[str, Any]] = None
) -> HookResult:
    """
    Run all hooks for a tool in order.
    Returns first deny/modify result, or allow if all pass.
    """
    context = context or {}
    hooks = HOOK_REGISTRY.get(tool_name, [])

    for hook in hooks:
        try:
            result = await hook(tool_name, args, context)
            if result.action in ("deny", "modify"):
                logger.info(
                    "Hook %s for %s returned %s: %s",
                    hook.__name__,
                    tool_name,
                    result.action,
                    result.reason,
                )
                return result
        except Exception as exc:  # noqa: BLE001
            logger.exception("Hook %s failed for %s", hook.__name__, tool_name)
            # On hook failure, deny to be safe
            return HookResult(
                action="deny",
                reason=f"Hook {hook.__name__} failed: {str(exc)}",
            )

    return HookResult(action="allow")


__all__ = [
    "HookResult",
    "run_hooks",
    "HOOK_REGISTRY",
    "validate_no_duplicate_title_desc",
    "auto_clean_inputs",
    "require_confirmation",
    "validate_task_ownership",
]
