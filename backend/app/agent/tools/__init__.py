"""
Agent tools package - core task tools, planning, and memory tools.
"""

# Core task tools (from original tools.py)
from .core_tools import (
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
    # Helper
    task_to_payload,
)

# New planning tools
from .planning_tools import prioritize_day, suggest_task_order

# New memory tools
from .memory_tools import store_user_preference, get_user_context, detect_work_pattern

__all__ = [
    # Core task tools
    "fetch_tasks",
    "fetch_task",
    "create_task",
    "update_task",
    "complete_task",
    "delete_task",
    "quick_analyze_task",
    # V1 MVP + Phase 2 tools
    "detect_stale_tasks",
    "breakdown_task",
    "draft_email",
    "get_workload_analytics",
    "get_rest_recommendation",
    # Planning tools
    "prioritize_day",
    "suggest_task_order",
    # Memory tools
    "store_user_preference",
    "get_user_context",
    "detect_work_pattern",
    # Helper
    "task_to_payload",
]
