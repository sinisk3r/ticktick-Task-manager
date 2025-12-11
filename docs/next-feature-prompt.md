# Feature Request: Enhanced TickTick Metadata Integration & Bi-directional Sync

## Objective
Enhance the task management system to capture and sync comprehensive TickTick metadata, enabling full bi-directional synchronization between Context and TickTick.

## Current State
- System currently syncs basic task data (title, description, due_date)
- Tasks are pulled from TickTick and displayed in local dashboard
- LLM analysis happens independently of TickTick's native metadata
- Changes in Context dashboard don't sync back to TickTick
- Missing key TickTick metadata: project, priority, start date, tags, etc.

## Complete User Flow

**1. Initial Sync (TickTick → Context):**
- User connects TickTick account via OAuth
- System pulls all tasks from TickTick to local PostgreSQL database
- Tasks appear in Context dashboard with all TickTick metadata
- User sees tasks organized in Eisenhower matrix (auto-assigned based on existing TickTick priority/dates)

**2. Review & Select (User Browsing):**
- User browses their tasks in the dashboard
- Can filter by project, quadrant, tags
- Sees all TickTick metadata (project, priority, tags, dates)
- **User decides which tasks need AI analysis** (not automatic)

**3. Request AI Analysis (User-Initiated):**
- User clicks "⚡ Analyze" on specific task(s)
- Or selects multiple tasks and clicks "⚡ Analyze Selected (5)"
- LLM analyzes with full context (project, related tasks, workload)
- Suggestions appear in task card

**4. Approve/Reject Suggestions:**
- User reviews AI suggestions with reasoning
- Approves individual suggestions or all at once
- Or dismisses suggestions if not helpful

**5. Sync Back to TickTick (Approved Changes Only):**
- When user approves suggestions → immediate sync to TickTick
- When user manually edits task → immediate sync to TickTick
- TickTick stays as source of truth, Context is intelligent layer on top

**6. Continuous Sync:**
- Webhook from TickTick → updates appear in Context real-time
- Polling fallback every 5 min catches missed updates
- User always sees latest state from both systems

## Requirements

### 1. Enhanced Metadata Capture from TickTick
Extend the Task model and sync logic to capture:

**Priority & Scheduling:**
- `ticktick_priority`: TickTick's native priority (None, Low, Medium, High)
- `start_date`: When task should be started (different from due_date)
- `all_day`: Boolean for all-day tasks
- `reminder_time`: TickTick reminder settings
- `repeat_flag`: Recurrence pattern if applicable

**Organization:**
- `project_id`: TickTick project/list the task belongs to
- `project_name`: Human-readable project name
- `parent_task_id`: For subtasks
- `sort_order`: Task position in TickTick lists

**Metadata:**
- `ticktick_tags`: Native TickTick tags (sync with our LLM-generated tags)
- `time_estimate`: TickTick's Pomodoro/time estimate
- `focus_time`: Time allocated in TickTick
- `column_id`: Kanban column (if project uses board view)

### 2. Bi-directional Synchronization with Approval Workflow

Implement full two-way sync with **user approval for LLM suggestions**:

**Context → TickTick (Push changes):**
- **User-initiated changes sync immediately** (no approval needed):
  - When user manually moves task to different quadrant → update TickTick priority
  - When user assigns project in Context → update TickTick project
  - When user edits title/description/due date → update in TickTick
  - When user adds tags manually → merge with TickTick tags
  - When user marks task complete → complete in TickTick

- **LLM suggestions require approval before syncing**:
  - LLM analysis generates suggestions (quadrant, tags, priority)
  - Suggestions shown in task card UI with approve/reject controls
  - User must explicitly approve before changes push to TickTick
  - Approved suggestions sync immediately
  - Rejected suggestions are logged but not applied

**TickTick → Context (Pull & Display - Already partially exists, enhance):**
- **Initial sync:** Pull all user tasks from TickTick on first connection
- **Ongoing sync:** Webhook + polling keeps tasks up-to-date
- Store all TickTick metadata locally (priority, project, tags, dates)
- Display tasks in dashboard for user review
- Respect TickTick priority when performing LLM analysis
- Use start_date for scheduling intelligence
- Sync project changes from TickTick
- Sync tag changes from TickTick
- Handle task deletions, completions, and moves
- **User browses local data** → decides what to analyze/modify

**Conflict Resolution:**
- Manual user changes always win over LLM suggestions
- Manual user changes always win over TickTick changes
- For non-override fields, last-write-wins with timestamp tracking
- Add `last_synced_at` and `last_modified_at` fields to detect conflicts

### 3. User-Initiated LLM Analysis

**User Flow Recap:**
1. **Tasks pulled from TickTick** → stored locally
2. **User sees all tasks** in dashboard
3. **User selects which tasks** to analyze
4. **LLM suggests improvements**
5. **User approves** → syncs to TickTick

**Analysis Trigger - User Selection:**

LLM analysis is **NOT automatic**. Users must explicitly request it after browsing their tasks:

**Option 1: Per-Task Analysis**
- Task card has "⚡ Analyze with AI" button
- User clicks to request LLM suggestions for that specific task
- Analysis runs in background, shows loading state
- Suggestions appear when ready

**Option 2: Bulk Analysis**
- Checkbox selection on multiple tasks
- Toolbar shows "⚡ Analyze Selected (5 tasks)" button
- User can select which tasks need AI input
- Batch analysis for efficiency

**Option 3: Smart Suggestions**
- System can suggest "This task might benefit from analysis" for:
  - Tasks without due dates but with long descriptions
  - Tasks in projects with many other tasks
  - Tasks created via quick-add (minimal metadata)
- User still must click to trigger analysis

**Why User-Initiated?**
- Saves LLM API costs (only analyze what's needed)
- User stays in control
- Faster UI (no waiting for automatic analysis)
- Users can batch analyze similar tasks together

### 4. UI Design for LLM Suggestion Approval

**Task Card Enhancement - Suggestion Badges:**

After user requests analysis, when a task has pending LLM suggestions, show a compact notification:

```
┌─────────────────────────────────────────┐
│ Complete Q4 OKR Review                  │
│ Work - Q4 OKRs                          │
│ Due: Dec 20                             │
│                            [⚡ Analyze]  │  ← User clicks to request analysis
└─────────────────────────────────────────┘

After analysis completes:

┌─────────────────────────────────────────┐
│ Complete Q4 OKR Review                  │
│ Work - Q4 OKRs                          │
│ Due: Dec 20                             │
│                                         │
│ ⚡ AI Suggestions (3)                    │  ← Collapsible section
│   ├─ Priority: Low → High               │
│   ├─ Add tags: strategic, leadership   │
│   ├─ Start: Tomorrow 9 AM               │
│                                         │
│   [✓ Approve All] [✗ Dismiss]          │  ← Action buttons
└─────────────────────────────────────────┘
```

**Individual Suggestion Approval:**

Users can expand to approve/reject individual suggestions:

```
⚡ AI Suggestions (3)                     [Expand ▼]

  ⭐ Priority: Low (1) → High (5)        [✓ Apply] [✗]
     "Q1 task with imminent deadline and high importance"
     Confidence: 90%

  🏷️ Tags: Add "strategic", "leadership"  [✓ Apply] [✗]
     "Task involves leadership planning based on project context (Work - Q4 OKRs)"
     Confidence: 85%

  📅 Start Date: Set to Tomorrow 9 AM    [✓ Apply] [✗]
     "Due in 2 days, should start tomorrow to avoid last-minute rush"
     Confidence: 80%
```

**Note:** Priority values shown in TickTick format (0/1/3/5) for transparency.

**Suggestion States:**

1. **Pending:** Yellow badge with count `⚡ AI Suggestions (3)`
2. **Partially Applied:** Blue badge `⚡ 2 applied, 1 pending`
3. **All Applied:** Green checkmark `✓ Synced with TickTick`
4. **All Dismissed:** No badge, suggestions cleared

**Quick Actions:**
- **Approve All:** Apply all suggestions and sync to TickTick immediately
- **Dismiss:** Clear all suggestions without applying
- **Individual Apply:** Cherry-pick specific suggestions

### 4. Project Management in Context UI
Add project assignment and filtering to the dashboard:

**UI Enhancements:**
- Project selector dropdown in task creation/edit
- Filter tasks by project in Eisenhower matrix
- Show project badge on task cards (e.g., "Work - Q4 OKRs")
- Project-based color coding (optional)

**Project Sync:**
- Fetch user's TickTick projects via API
- Store in new `Project` model with user relationship
- Sync project list every 30 minutes
- Allow creating tasks in specific projects

### 5. LLM Analysis Improvements with Suggestion Engine
Enhance the LLM prompt to generate **suggestions** rather than direct changes:

**Input to LLM (Full Context):**
```python
{
  # Task details
  "title": "...",
  "description": "...",

  # TickTick metadata
  "ticktick_priority": "High",  # User already marked important
  "start_date": "2025-12-15",
  "due_date": "2025-12-20",
  "time_estimate": 120,  # minutes

  # Project context for intelligent prioritization
  "project_name": "Work - Q4 OKRs",
  "project_id": "abc123",
  "ticktick_tags": ["urgent", "client-facing"],

  # Related tasks in same project (for context-aware prioritization)
  "related_tasks_in_project": [
    {"title": "Review Q4 metrics", "status": "completed"},
    {"title": "Schedule team review", "status": "pending", "due_date": "2025-12-18"}
  ],

  # User's current workload (for better scheduling)
  "user_workload": {
    "total_q1_tasks": 8,
    "total_q2_tasks": 15,
    "available_hours_this_week": 12
  }
}
```

**LLM Output - Suggestions Model (TickTick-Compatible Format):**
```python
{
  "analysis": {
    "urgency_score": 8,
    "importance_score": 9,
    "eisenhower_quadrant": "Q1",
    "effort_hours": 2.0
  },
  "suggestions": [
    {
      "type": "priority",
      "current": 1,  # TickTick priority: 0=None, 1=Low, 3=Medium, 5=High
      "suggested": 5,  # High priority in TickTick format
      "current_display": "Low",  # Human-readable for UI
      "suggested_display": "High",
      "reason": "Q1 task with imminent deadline and high importance",
      "confidence": 0.90
    },
    {
      "type": "tags",
      "current": ["urgent", "client-facing"],
      "suggested": ["urgent", "client-facing", "strategic", "leadership"],
      "reason": "Task involves leadership planning based on project context (Work - Q4 OKRs)",
      "confidence": 0.85
    },
    {
      "type": "start_date",
      "current": null,
      "suggested": "2025-12-18T09:00:00Z",  # ISO format for TickTick
      "suggested_display": "Tomorrow 9 AM",
      "reason": "Due in 2 days, should start tomorrow to avoid last-minute rush",
      "confidence": 0.80
    }
  ]
}
```

**TickTick Priority Mapping:**
- `0` = None (No priority)
- `1` = Low priority
- `3` = Medium priority
- `5` = High priority

**IMPORTANT:** All suggestions must use TickTick's native values for seamless cross-sync.

**LLM Behavior:**
- **Only run when user explicitly requests analysis** (not automatic on every task)
- Generate suggestions only when there's a meaningful difference
- Don't suggest changes if current state is already optimal
- Respect user's explicit TickTick priority as a strong signal
- **Use project context for intelligent prioritization** (related tasks, project type, workload)
- Consider start_date vs due_date for urgency calculation
- Factor in project context (e.g., "Work - Q4 OKRs" vs "Personal - Home")
- **Use related tasks in same project to understand priority relative to other work**
- Provide confidence scores to help users decide
- Include clear reasoning for each suggestion
- **Output all values in TickTick-compatible format** (priority: 0/1/3/5, dates: ISO format)

### 5. Worker Model Guidance & Token Management

**Scaffolding for Evaluation:**
The worker model should be guided to:
- Validate sync operations completed successfully (check TickTick API responses)
- Verify database state matches expected changes
- Test bi-directional sync with sample task modifications
- Confirm no data loss during conflict resolution
- Check that manual overrides are preserved

**Subtask Management for Token Efficiency:**
Break implementation into discrete subtasks:
1. **Subtask 1:** Database migration - Add new fields to Task model + Project model + TickTick-compatible formats
2. **Subtask 2:** TickTick service - Initial sync endpoint to pull all tasks with extended metadata (priority as 0/1/3/5, etc.)
3. **Subtask 3:** TickTick service - Ongoing sync (webhook + polling) to keep local data fresh
4. **Subtask 4:** LLM context enrichment - Pass project context, related tasks, workload to LLM
5. **Subtask 5:** LLM suggestion engine - Generate suggestions in TickTick-compatible format
6. **Subtask 6:** Suggestion API - User-initiated analysis endpoints + approve/reject
7. **Subtask 7:** Push sync logic - Send approved changes back to TickTick
8. **Subtask 8:** Conflict resolution - Last-write-wins with manual override protection
9. **Subtask 9:** Frontend - Display tasks with TickTick metadata (project badges, priority, etc.)
10. **Subtask 10:** Frontend - "Analyze with AI" button + bulk selection
11. **Subtask 11:** Frontend - Suggestion badge UI with approve/reject controls (show TickTick values)
12. **Subtask 12:** Frontend - Project selector, filters, task editing
13. **Subtask 13:** Testing - Unit tests for sync (both directions), suggestions, conflicts, TickTick format conversion
14. **Subtask 14:** Validation - Manual testing with real TickTick account

**After each subtask:**
- Worker should evaluate: "Does this work as expected?"
- Run relevant tests (unit/integration)
- Check for regressions
- Request next subtask only when current is validated

## Database Schema Changes

### Task Model Extensions
```python
class Task:
    # Existing fields...

    # TickTick Extended Metadata (stored in TickTick-compatible format)
    ticktick_priority: Optional[int]  # 0=None, 1=Low, 3=Medium, 5=High (TickTick format)
    start_date: Optional[datetime]  # ISO format
    all_day: bool = False
    reminder_time: Optional[datetime]
    repeat_flag: Optional[str]

    # Organization
    project_id: Optional[str]  # TickTick project ID
    project_name: Optional[str]
    parent_task_id: Optional[str]
    sort_order: int = 0

    # Metadata
    ticktick_tags: JSONB  # ["tag1", "tag2"]
    time_estimate: Optional[int]  # minutes
    focus_time: Optional[int]  # minutes
    column_id: Optional[str]

    # Sync tracking
    last_synced_at: datetime
    last_modified_at: datetime
    sync_version: int = 1  # Increment on each change

    # LLM Analysis
    llm_analyzed_at: Optional[datetime]  # When last analyzed
    pending_suggestions: JSONB = []  # List of suggestion objects
    # Example: [{"type": "priority", "current": 1, "suggested": 5, "current_display": "Low",
    #            "suggested_display": "High", "reason": "...", "confidence": 0.95}]
```

### New TaskSuggestion Model (Optional - for tracking history)
```python
class TaskSuggestion:
    id: int
    task_id: int
    suggestion_type: str  # quadrant_change, tags, priority, etc.
    current_value: JSONB
    suggested_value: JSONB
    reason: str
    confidence: float
    status: str  # pending, approved, rejected
    created_at: datetime
    resolved_at: Optional[datetime]
    resolved_by_user: bool = False
```

### New Project Model
```python
class Project:
    id: int
    user_id: int
    ticktick_project_id: str
    name: str
    color: Optional[str]
    sort_order: int
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
```

## API Endpoints to Add/Modify

```python
# Initial Setup & Sync
POST   /api/sync/ticktick/initial       # First-time: Pull all tasks from TickTick
GET    /api/sync/status                 # Check sync status (last sync time, pending items)

# Projects
GET    /api/projects                    # List user's projects (from local DB)
POST   /api/projects/sync               # Force project sync from TickTick

# Tasks (enhance existing)
PUT    /api/tasks/{id}                  # Add project_id, tags to update
PUT    /api/tasks/{id}/project          # Change task project
POST   /api/tasks                       # Accept project_id on creation

# Suggestions (NEW)
POST   /api/tasks/{id}/analyze          # User-initiated: Trigger LLM analysis for task
POST   /api/tasks/analyze/batch         # Bulk analysis for multiple tasks
  Body: { "task_ids": [1, 2, 3, 4, 5] }
GET    /api/tasks/{id}/suggestions      # Get pending suggestions for task
POST   /api/tasks/{id}/suggestions/approve  # Approve suggestions
  Body: { "suggestion_types": ["priority", "tags"] }  # or "all"
POST   /api/tasks/{id}/suggestions/reject   # Reject suggestions
  Body: { "suggestion_types": ["start_date"] }  # or "all"

# Sync (enhance)
POST   /api/sync/ticktick/push/{task_id}  # Force push changes to TickTick (after approval)
GET    /api/sync/conflicts              # Show sync conflicts for resolution
```

## Success Criteria

✅ All TickTick metadata fields are captured and stored **in TickTick-compatible format**
✅ **LLM analysis is user-initiated (not automatic)** via "Analyze" button or bulk selection
✅ **LLM generates suggestions with clear reasoning and confidence scores**
✅ **LLM receives project context, related tasks, and workload for intelligent prioritization**
✅ **All LLM outputs use TickTick-compatible values** (priority: 0/1/3/5, ISO dates)
✅ **Users can approve/reject suggestions individually or in bulk**
✅ **Only approved suggestions sync to TickTick**
✅ User-initiated changes in Context UI sync to TickTick within 5 seconds
✅ Changes in TickTick appear in Context within 30 seconds (webhook + polling)
✅ Manual user changes are never overwritten by LLM suggestions or TickTick sync
✅ Project assignment works in both directions
✅ Tag merging works correctly (approved LLM tags + TickTick tags + user tags)
✅ No data loss during sync conflicts or format conversions
✅ LLM analysis quality improves with project and workload context
✅ Suggestion UI is intuitive and doesn't clutter task cards
✅ All sync and suggestion operations have tests with >80% coverage

## Testing Strategy

**Unit Tests:**
- Test metadata extraction from TickTick API responses
- Test bi-directional sync logic for each field
- Test conflict resolution with various scenarios
- Test manual override preservation

**Integration Tests:**
- Create task in Context → verify in TickTick
- Modify task in TickTick → verify in Context
- Simultaneous edits → verify conflict resolution
- Project changes sync correctly

**Manual Testing Checklist:**
1. **Initial sync**: Connect TickTick account → all existing tasks appear in Context dashboard
2. **Display**: Verify all TickTick metadata visible (project, priority=5, tags, dates)
3. **User browsing**: Filter by project, quadrant → tasks display correctly
4. **Select task**: User clicks "⚡ Analyze" → LLM suggestions appear with TickTick-compatible values
5. **Approve suggestion**: User approves priority change → TickTick updates to new value (0/1/3/5)
6. **Manual edit**: User moves task in matrix manually → TickTick priority updates correctly
7. **Bi-directional sync**: Change project in TickTick → Context reflects change within 30 sec
8. **Tag merging**: Add tags in both systems → merged correctly
9. **Bulk analysis**: Select 5 tasks, click "Analyze Selected" → all get suggestions, approve individually
10. **Delete in TickTick**: Delete task in TickTick → removed from Context
11. **Complete in Context**: Mark task done in Context → marked complete in TickTick
12. **Format integrity**: Verify priority values are 0/1/3/5 (not strings or other values)
13. **New task in TickTick**: Create new task in TickTick → appears in Context without needing manual sync

## Implementation Notes

**TickTick API References:**
- Task object schema: https://developer.ticktick.com/api#/openapi?id=task-object
- Update task endpoint: https://developer.ticktick.com/api#/openapi?id=update-a-task
- Projects list: https://developer.ticktick.com/api#/openapi?id=get-all-lists

**Rate Limiting Considerations:**
- TickTick has rate limits (~120 req/min)
- Batch updates where possible
- Use webhook for real-time sync, polling only as fallback
- Cache project list (refresh every 30 min, not on every task)

**Data Privacy:**
- All TickTick metadata is user-specific
- Respect user's project privacy settings
- Don't expose TickTick IDs in frontend (use internal IDs)

## Out of Scope (Future Enhancements)
- Subtask synchronization (keep flat for now)
- Attachment sync
- Comment sync
- Collaboration features
- Custom field mapping

## Questions for Clarification
1. Should we allow users to map Context quadrants to specific TickTick projects?
2. How should we handle TickTick's "list" vs "project" terminology?
3. Should LLM analysis be re-run when TickTick priority changes?
4. Do we want conflict resolution UI or just last-write-wins?

---

**Reminder:** Use TodoWrite to break this into manageable subtasks, and validate each step before proceeding to the next. Request subtask approval if uncertain about implementation approach.
