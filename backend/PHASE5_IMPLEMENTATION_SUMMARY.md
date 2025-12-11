# Phase 5: Suggestion API Endpoints - Implementation Summary

## Overview

Phase 5 implements the API endpoints for the LLM suggestion workflow, allowing users to request task analysis, review suggestions, and approve/reject them.

## Implemented Endpoints

### 1. POST /api/tasks/{task_id}/analyze
**Purpose:** User-initiated LLM analysis for a specific task

**Request:**
- Path parameter: `task_id` (int)
- Query parameter: `user_id` (int)

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

**Workflow:**
1. Fetches task details and validates ownership
2. Gathers context (project, related tasks, user workload)
3. Calls LLM service (`generate_suggestions`)
4. Deletes old pending suggestions for this task
5. Stores new suggestions in `TaskSuggestion` table
6. Updates task's `analyzed_at` timestamp

---

### 2. POST /api/tasks/analyze/batch
**Purpose:** Analyze multiple tasks in a single request

**Request:**
- Query parameter: `user_id` (int)
- Body: `{"task_ids": [1, 2, 3]}`

**Response:**
```json
{
  "total": 3,
  "successful": 2,
  "failed": 1,
  "results": [
    {"task_id": 1, "status": "success", "data": {...}},
    {"task_id": 2, "status": "error", "error": "Task not found"}
  ]
}
```

**Features:**
- Independent processing (one failure doesn't stop the batch)
- Detailed per-task results
- Uses the single-task endpoint internally

---

### 3. GET /api/tasks/{task_id}/suggestions
**Purpose:** Retrieve pending suggestions for a task

**Request:**
- Path parameter: `task_id` (int)
- Query parameter: `user_id` (int)

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

**Notes:**
- Only returns PENDING suggestions (not approved/rejected)
- Ordered by creation time (newest first)

---

### 4. POST /api/tasks/{task_id}/suggestions/approve
**Purpose:** Approve and apply specific suggestions

**Request:**
- Path parameter: `task_id` (int)
- Query parameter: `user_id` (int)
- Body: `{"suggestion_types": ["priority", "tags"]}` or `{"suggestion_types": ["all"]}`

**Response:**
```json
{
  "task_id": 123,
  "approved_count": 2,
  "approved_types": ["priority", "tags"],
  "synced_to_ticktick": true
}
```

**Workflow:**
1. Fetches pending suggestions of specified types
2. Applies suggested values to task:
   - `priority` → updates `task.ticktick_priority`
   - `tags` → updates `task.ticktick_tags`
   - `quadrant` → updates `task.eisenhower_quadrant` and sets `is_sorted=True`
   - `start_date` → updates `task.start_date`
3. Marks suggestions as APPROVED
4. Updates sync metadata (`last_modified_at`, `sync_version`)
5. Pushes changes to TickTick if task is synced
6. Returns approval summary

**Special Handling:**
- Approving `quadrant` suggestion moves task out of unsorted list
- TickTick sync only happens if task has `ticktick_task_id` and user has access token
- Errors in TickTick sync are logged but don't fail the approval

---

### 5. POST /api/tasks/{task_id}/suggestions/reject
**Purpose:** Reject specific suggestions without applying them

**Request:**
- Path parameter: `task_id` (int)
- Query parameter: `user_id` (int)
- Body: `{"suggestion_types": ["start_date"]}` or `{"suggestion_types": ["all"]}`

**Response:**
```json
{
  "task_id": 123,
  "rejected_count": 1,
  "rejected_types": ["start_date"]
}
```

**Workflow:**
1. Fetches pending suggestions of specified types
2. Marks them as REJECTED (does NOT apply changes to task)
3. Sets `resolved_at` and `resolved_by_user=True`

**Notes:**
- Rejected suggestions are kept in database for tracking user preferences
- Task fields are NOT modified when rejecting

---

## Database Changes

### Task Model Updates
- Uses existing `analyzed_at` field to track last analysis time

### TaskSuggestion Model
All fields already present from Phase 4:
- `task_id` (ForeignKey to tasks)
- `suggestion_type` (priority, tags, quadrant, start_date)
- `current_value` (JSONB)
- `suggested_value` (JSONB)
- `reason` (String)
- `confidence` (Float)
- `status` (PENDING, APPROVED, REJECTED)
- `resolved_at` (DateTime)
- `resolved_by_user` (Boolean)

---

## Integration Points

### LLM Service (llm_ollama.py)
- `generate_suggestions()` method used for analysis
- Returns structured JSON with analysis and suggestions

### Workload Calculator (workload_calculator.py)
- `calculate_user_workload()` - provides context about user's current task load
- `get_project_context()` - provides project statistics
- `get_related_tasks()` - finds similar tasks in same project

### TickTick Service (ticktick.py)
- `update_task()` method used to sync approved changes
- Only called if task has `ticktick_task_id` and user has access token

---

## Error Handling

### Common Error Responses

**404 Not Found:**
- Task doesn't exist or doesn't belong to user
```json
{"detail": "Task not found"}
```

**500 Internal Server Error:**
- LLM service failure during analysis
```json
{"detail": "Analysis failed: <error message>"}
```

**200 OK with message:**
- No pending suggestions to approve/reject
```json
{"message": "No pending suggestions to approve"}
```

### Graceful Degradation

1. **LLM Analysis Failure:**
   - Error logged, 500 returned to user
   - Existing suggestions not affected

2. **TickTick Sync Failure:**
   - Error logged, but approval succeeds locally
   - `synced_to_ticktick` returned as `false`

3. **Batch Analysis Partial Failure:**
   - Continues processing other tasks
   - Failed tasks reported in `results` array

---

## Testing

### Manual Test Script
Located at: `backend/tests/test_suggestion_api_manual.py`

**Usage:**
```bash
# Ensure backend is running on localhost:8000
python tests/test_suggestion_api_manual.py
```

**Test Coverage:**
1. Complete suggestion workflow (create → analyze → get → approve → reject)
2. Batch analysis with multiple tasks
3. Error cases (non-existent tasks, no suggestions)

### Unit Tests
Located at: `backend/tests/test_suggestion_api.py`

**Note:** Unit tests require PostgreSQL (JSONB not supported in SQLite)

**Test Classes:**
1. `TestAnalyzeTaskEndpoint` - Analysis endpoint tests
2. `TestBatchAnalyzeEndpoint` - Batch analysis tests
3. `TestGetSuggestionsEndpoint` - Get suggestions tests
4. `TestApproveSuggestionsEndpoint` - Approval tests
5. `TestRejectSuggestionsEndpoint` - Rejection tests
6. `TestSuggestionWorkflow` - Integration tests

---

## API Usage Examples

### Example 1: Complete Workflow

```python
import httpx

async def suggestion_workflow():
    async with httpx.AsyncClient() as client:
        # 1. Create task
        task = await client.post(
            "http://localhost:8000/api/tasks",
            json={
                "title": "Complete quarterly report",
                "description": "Finish Q4 financial report by Friday",
                "user_id": 1
            }
        )
        task_id = task.json()["id"]

        # 2. Analyze task
        analysis = await client.post(
            f"http://localhost:8000/api/tasks/{task_id}/analyze?user_id=1"
        )
        suggestions = analysis.json()["suggestions"]

        # 3. Approve priority and tags suggestions
        await client.post(
            f"http://localhost:8000/api/tasks/{task_id}/suggestions/approve?user_id=1",
            json={"suggestion_types": ["priority", "tags"]}
        )

        # 4. Reject quadrant suggestion
        await client.post(
            f"http://localhost:8000/api/tasks/{task_id}/suggestions/reject?user_id=1",
            json={"suggestion_types": ["quadrant"]}
        )
```

### Example 2: Batch Analysis

```python
# Analyze multiple tasks at once
response = await client.post(
    "http://localhost:8000/api/tasks/analyze/batch?user_id=1",
    json={"task_ids": [1, 2, 3, 4, 5]}
)

results = response.json()
print(f"Analyzed {results['successful']}/{results['total']} tasks")
```

### Example 3: Approve All Suggestions

```python
# Approve all pending suggestions for a task
response = await client.post(
    f"http://localhost:8000/api/tasks/{task_id}/suggestions/approve?user_id=1",
    json={"suggestion_types": ["all"]}
)
```

---

## Performance Considerations

1. **LLM Analysis:**
   - Async execution to avoid blocking
   - Timeout configured in OllamaService
   - Cached workload context calculated once per request

2. **Batch Analysis:**
   - Tasks processed sequentially (not parallel)
   - Each task analyzed independently
   - Failure isolation per task

3. **Database Queries:**
   - Old pending suggestions deleted before creating new ones
   - Single transaction per approve/reject operation
   - Minimal joins for context gathering

---

## Future Enhancements

1. **Async Background Processing:**
   - Move analysis to Celery worker for better UX
   - WebSocket notifications when analysis completes

2. **Suggestion Learning:**
   - Track approval/rejection patterns
   - Use to improve future suggestions

3. **Bulk Operations:**
   - Approve/reject across multiple tasks
   - Smart filtering of suggestions

4. **Suggestion Versioning:**
   - Track suggestion changes over time
   - Compare old vs new suggestions

---

## File Changes Summary

### Modified Files
1. `backend/app/api/tasks.py`
   - Added 5 new endpoints (lines 932-1294)
   - Added imports: `Body`, `delete`, `logging`
   - Total additions: ~360 lines

### New Files
1. `backend/tests/conftest.py`
   - Pytest fixtures for async testing
   - Database session management
   - HTTP client fixtures

2. `backend/tests/test_suggestion_api.py`
   - Comprehensive unit tests (17 test cases)
   - Covers all endpoints and error cases

3. `backend/tests/test_suggestion_api_manual.py`
   - Manual integration tests
   - Real HTTP requests to running server

4. `backend/PHASE5_IMPLEMENTATION_SUMMARY.md`
   - This documentation file

---

## Deployment Checklist

- [x] API endpoints implemented
- [x] Error handling added
- [x] TickTick sync integration
- [x] Manual test script created
- [x] Documentation written
- [ ] Unit tests passing (requires PostgreSQL)
- [ ] Integration tests on staging
- [ ] Frontend integration (Phase 6)

---

## Known Issues

1. **Unit Tests:**
   - Require PostgreSQL database (JSONB not supported in SQLite)
   - Run `test_suggestion_api_manual.py` instead for validation

2. **Authentication:**
   - Currently using `user_id` query parameter
   - Should be replaced with proper auth tokens in production

---

## Support

For issues or questions about this implementation:
1. Check this documentation
2. Review manual test output
3. Check backend logs for errors
4. Verify Ollama service is running
