# New Agent Tools Implementation Guide

This guide provides detailed implementation specs for 5 new agent tools.

## Tool Patterns (LangChain Best Practices)

```python
# Pattern from LangChain docs:
from langchain_core.tools import InjectedToolArg, tool
from langchain_core.runnables import RunnableConfig
from typing import Annotated, Dict, Any, Optional

@tool(parse_docstring=True)
async def tool_name(
    required_param: str,  # Visible to LLM
    config: Annotated[RunnableConfig, InjectedToolArg()],  # Hidden from LLM
    optional_param: Optional[str] = None,  # Visible to LLM
) -> Dict[str, Any]:
    """Tool description for LLM to understand when to use it.

    Args:
        required_param: Description of parameter
        optional_param: Description with default behavior
    """
    user_id = config.get("configurable", {}).get("user_id")
    db = config.get("configurable", {}).get("db")
    # Implementation...
    return {"payload": data, "summary": "Human readable result"}
```

---

## Tool 1: detect_stale_tasks

### Purpose
Find tasks that haven't been updated recently (avoidance pattern detection).

### Signature
```python
@tool(parse_docstring=True)
async def detect_stale_tasks(
    config: Annotated[RunnableConfig, InjectedToolArg()],
    days_threshold: int = 14,
    include_completed: bool = False,
    limit: int = 20,
) -> Dict[str, Any]:
```

### Query
```python
stale_cutoff = datetime.utcnow() - timedelta(days=days_threshold)
query = select(Task).where(
    Task.user_id == user_id,
    Task.updated_at < stale_cutoff,
    Task.status == TaskStatus.ACTIVE
).order_by(Task.updated_at.asc()).limit(limit)
```

### Return Structure
```python
{
    "stale_tasks": [
        {
            "id": int,
            "title": str,
            "days_stale": int,
            "last_updated": str,  # ISO date
            "staleness_reason": str,
            "suggested_action": str,
            "quadrant": str,
        }
    ],
    "total_stale": int,
    "insights": {
        "by_quadrant": {"Q1": 0, "Q2": 2, ...},
        "average_staleness_days": float,
    },
    "summary": str,
}
```

---

## Tool 2: breakdown_task

### Purpose
Split complex tasks into 3-5 actionable subtasks using LLM.

### Signature
```python
@tool(parse_docstring=True)
async def breakdown_task(
    config: Annotated[RunnableConfig, InjectedToolArg()],
    task_id: Optional[int] = None,
    description: Optional[str] = None,
    max_subtasks: int = 5,
    create_subtasks: bool = False,
) -> Dict[str, Any]:
```

### LLM Prompt Template (task_breakdown_v1.txt)
```
You are a task breakdown specialist. Decompose complex tasks into smaller, actionable subtasks.

## Task to Break Down:
Title: {task_title}
Description: {task_description}
Maximum Subtasks: {max_subtasks}

## Output Format (JSON only):
{
  "subtasks": [
    {
      "title": "Clear, actionable title (max 80 chars)",
      "description": "Brief context (max 200 chars)",
      "estimated_minutes": 15-240,
      "order": 1,
      "dependencies": []
    }
  ],
  "total_estimated_minutes": 120
}

## Guidelines:
1. Each subtask should be a single, completable action
2. Use specific verbs: Draft, Review, Send, Create, Research
3. Target 15-60 minutes per subtask
4. List in logical execution order
```

### Return Structure
```python
{
    "parent_task": {"id": int, "title": str} | None,
    "subtasks": [
        {
            "title": str,
            "description": str,
            "estimated_minutes": int,
            "order": int,
        }
    ],
    "total_estimated_minutes": int,
    "created_task_ids": List[int],  # if create_subtasks=True
    "summary": str,
}
```

---

## Tool 3: draft_email

### Purpose
Generate contextual email drafts based on task context.

### Signature
```python
@tool(parse_docstring=True)
async def draft_email(
    task_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg()],
    email_type: str = "status_update",
    recipient_context: Optional[str] = None,
    tone: str = "professional",
) -> Dict[str, Any]:
```

### Email Types
- `status_update`: Progress update on a task
- `request`: Asking for help/approval
- `escalation`: Flagging blockers
- `completion`: Announcing task done

### Tone Options
- `professional`: Default, clear and direct
- `friendly`: Warmer, conversational
- `formal`: Structured, for executives
- `urgent`: Action required, shorter

### LLM Prompt Template (email_draft_v1.txt)
```
You are an email drafting assistant. Generate professional emails based on task context.

## Task Context:
Title: {task_title}
Description: {task_description}
Status: {task_status}
Due Date: {due_date}
Quadrant: {quadrant}

## Email Parameters:
- Type: {email_type}
- Recipient: {recipient_context}
- Tone: {tone}

## Output Format (JSON only):
{
  "subject": "Clear subject line (max 60 chars)",
  "body": "Full email body with proper formatting",
  "suggested_ccs": ["role/person"]
}
```

### Return Structure
```python
{
    "task": {"id": int, "title": str},
    "email": {
        "subject": str,
        "body": str,
        "suggested_ccs": List[str],
        "email_type": str,
        "tone": str,
    },
    "summary": str,
}
```

---

## Tool 4: get_workload_analytics

### Purpose
Calculate capacity, risk level, and workload insights.

### Signature
```python
@tool(parse_docstring=True)
async def get_workload_analytics(
    config: Annotated[RunnableConfig, InjectedToolArg()],
    period: str = "this_week",
) -> Dict[str, Any]:
```

### Periods
- `today`: 8 hours available
- `this_week`: 40 hours available (Mon-Fri)
- `this_month`: ~172 hours available

### Risk Levels
- `low`: <70% capacity
- `medium`: 70-85% capacity
- `high`: 85-100% capacity
- `critical`: >100% capacity

### Uses WellbeingService
```python
from app.services.wellbeing_service import WellbeingService
service = WellbeingService(db, user_id)
result = await service.calculate_workload(period)
```

---

## Tool 5: get_rest_recommendation

### Purpose
Suggest rest periods based on work intensity patterns.

### Signature
```python
@tool(parse_docstring=True)
async def get_rest_recommendation(
    config: Annotated[RunnableConfig, InjectedToolArg()],
) -> Dict[str, Any]:
```

### Urgency Levels
- `immediate`: Rest score >= 70, take a break now
- `soon`: Rest score 50-70, schedule break today
- `optional`: Rest score <50, doing okay

### Factors Analyzed
- Recent task completions (activity level)
- Q1 task density (urgent pressure)
- Overdue tasks (stress factor)
- Capacity utilization

### Uses WellbeingService
```python
from app.services.wellbeing_service import WellbeingService
service = WellbeingService(db, user_id)
result = await service.calculate_rest_recommendation()
```

---

## Files to Create/Modify

### New Files
1. `backend/app/services/wellbeing_service.py` ✅ DONE
2. `backend/app/services/task_intelligence_service.py`
3. `backend/app/prompts/task_breakdown_v1.txt`
4. `backend/app/prompts/email_draft_v1.txt`

### Modified Files
1. `backend/app/agent/tools.py` - Add 5 tool functions
2. `backend/app/agent/graph.py` - Register tools, update system message
3. `backend/app/services/__init__.py` - Export new services
4. `backend/app/api/agent.py` - Add to tool_map
5. `backend/tests/agent_test_cases.json` - Add test cases

---

## System Message Updates (graph.py)

Add to get_system_message():
```python
**New capabilities:**
- Detect stale/forgotten tasks (avoidance patterns)
- Break down complex tasks into subtasks
- Draft emails based on task context
- Provide workload analytics and capacity insights
- Recommend rest periods based on work intensity

**When to use new tools:**
- "What have I been avoiding?" → detect_stale_tasks
- "Break this down" / "Help me split this task" → breakdown_task
- "Draft an email about..." → draft_email
- "How busy am I?" / "What's my workload?" → get_workload_analytics
- "Should I take a break?" / "I'm overwhelmed" → get_rest_recommendation
```

---

## Test Cases to Add

```json
[
  {
    "name": "Detect Stale Tasks",
    "query": "What tasks have I been avoiding?",
    "expected": {
      "should_call_tools": true,
      "expected_tool": "detect_stale_tasks"
    }
  },
  {
    "name": "Breakdown Task",
    "query": "Help me break down the quarterly review task",
    "expected": {
      "should_call_tools": true,
      "expected_tool": "breakdown_task"
    }
  },
  {
    "name": "Draft Email",
    "query": "Draft an email to my manager about task 5",
    "expected": {
      "should_call_tools": true,
      "expected_tool": "draft_email"
    }
  },
  {
    "name": "Workload Analytics",
    "query": "How busy am I this week?",
    "expected": {
      "should_call_tools": true,
      "expected_tool": "get_workload_analytics"
    }
  },
  {
    "name": "Rest Recommendation",
    "query": "I'm feeling overwhelmed, should I take a break?",
    "expected": {
      "should_call_tools": true,
      "expected_tool": "get_rest_recommendation"
    }
  }
]
```
