# Suggestion API Endpoints - Quick Reference

## Base URL
```
http://localhost:8000
```

## Endpoints

### 1. Analyze Task (Generate Suggestions)

```http
POST /api/tasks/{task_id}/analyze?user_id={user_id}
```

**Response:**
```json
{
  "task_id": 123,
  "analysis": {
    "urgency": 8,
    "importance": 7,
    "quadrant": "Q1",
    "reasoning": "High urgency due to deadline..."
  },
  "suggestions": [
    {
      "id": 456,
      "type": "priority",
      "current": 0,
      "suggested": 5,
      "reason": "Task is urgent and important",
      "confidence": 0.9
    }
  ]
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/tasks/123/analyze?user_id=1"
```

---

### 2. Batch Analyze Tasks

```http
POST /api/tasks/analyze/batch?user_id={user_id}
Content-Type: application/json

{
  "task_ids": [1, 2, 3]
}
```

**Response:**
```json
{
  "total": 3,
  "successful": 2,
  "failed": 1,
  "results": [...]
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/tasks/analyze/batch?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"task_ids": [1, 2, 3]}'
```

---

### 3. Get Pending Suggestions

```http
GET /api/tasks/{task_id}/suggestions?user_id={user_id}
```

**Response:**
```json
{
  "task_id": 123,
  "suggestions": [
    {
      "id": 456,
      "type": "priority",
      "current": 0,
      "suggested": 5,
      "reason": "Task is urgent and important",
      "confidence": 0.9,
      "created_at": "2025-12-11T10:00:00Z"
    }
  ]
}
```

**Curl Example:**
```bash
curl "http://localhost:8000/api/tasks/123/suggestions?user_id=1"
```

---

### 4. Approve Suggestions

```http
POST /api/tasks/{task_id}/suggestions/approve?user_id={user_id}
Content-Type: application/json

{
  "suggestion_types": ["priority", "tags"]
}
```

**OR approve all:**
```json
{
  "suggestion_types": ["all"]
}
```

**Response:**
```json
{
  "task_id": 123,
  "approved_count": 2,
  "approved_types": ["priority", "tags"],
  "synced_to_ticktick": true
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/tasks/123/suggestions/approve?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"suggestion_types": ["priority", "tags"]}'
```

---

### 5. Reject Suggestions

```http
POST /api/tasks/{task_id}/suggestions/reject?user_id={user_id}
Content-Type: application/json

{
  "suggestion_types": ["start_date"]
}
```

**OR reject all:**
```json
{
  "suggestion_types": ["all"]
}
```

**Response:**
```json
{
  "task_id": 123,
  "rejected_count": 1,
  "rejected_types": ["start_date"]
}
```

**Curl Example:**
```bash
curl -X POST "http://localhost:8000/api/tasks/123/suggestions/reject?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"suggestion_types": ["all"]}'
```

---

## Suggestion Types

- `priority` - TickTick priority (0, 1, 3, 5)
- `tags` - Task tags array
- `quadrant` - Eisenhower quadrant (Q1, Q2, Q3, Q4)
- `start_date` - Task start date (ISO format)

---

## Error Responses

### 404 Not Found
```json
{
  "detail": "Task not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Analysis failed: <error message>"
}
```

### 200 OK (No Suggestions)
```json
{
  "message": "No pending suggestions to approve"
}
```

---

## Complete Workflow Example

```bash
# 1. Create a task
TASK_ID=$(curl -X POST "http://localhost:8000/api/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Complete quarterly report",
    "description": "Finish Q4 financial report by Friday",
    "user_id": 1
  }' | jq -r '.id')

# 2. Analyze the task
curl -X POST "http://localhost:8000/api/tasks/$TASK_ID/analyze?user_id=1"

# 3. Get pending suggestions
curl "http://localhost:8000/api/tasks/$TASK_ID/suggestions?user_id=1"

# 4. Approve priority and tags
curl -X POST "http://localhost:8000/api/tasks/$TASK_ID/suggestions/approve?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"suggestion_types": ["priority", "tags"]}'

# 5. Reject remaining suggestions
curl -X POST "http://localhost:8000/api/tasks/$TASK_ID/suggestions/reject?user_id=1" \
  -H "Content-Type: application/json" \
  -d '{"suggestion_types": ["all"]}'
```

---

## Python Client Example

```python
import httpx
import asyncio

async def suggestion_workflow(task_id: int, user_id: int = 1):
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # Analyze
        response = await client.post(
            f"{base_url}/api/tasks/{task_id}/analyze?user_id={user_id}"
        )
        suggestions = response.json()["suggestions"]

        # Get suggestions
        response = await client.get(
            f"{base_url}/api/tasks/{task_id}/suggestions?user_id={user_id}"
        )

        # Approve specific types
        await client.post(
            f"{base_url}/api/tasks/{task_id}/suggestions/approve?user_id={user_id}",
            json={"suggestion_types": ["priority", "tags"]}
        )

        # Reject others
        await client.post(
            f"{base_url}/api/tasks/{task_id}/suggestions/reject?user_id={user_id}",
            json={"suggestion_types": ["all"]}
        )

# Run
asyncio.run(suggestion_workflow(task_id=123))
```

---

## Testing

### Manual Test Script
```bash
cd backend
python tests/test_suggestion_api_manual.py
```

### Verify Server is Running
```bash
curl http://localhost:8000/health
```

Should return:
```json
{
  "status": "ok",
  "ollama_connected": true,
  "ollama_model": "qwen3:4b"
}
```
