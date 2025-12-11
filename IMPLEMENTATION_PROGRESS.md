# Enhanced TickTick Metadata Integration - Implementation Progress

**Started:** 2025-12-11
**Target:** MVP - Core bi-directional sync with user-initiated AI suggestions
**Status:** 🟡 In Progress

---

## Project Overview

Transform the task management system to:
1. Capture comprehensive TickTick metadata (priority, tags, projects, dates)
2. Enable user-initiated AI analysis (not automatic)
3. Implement suggestion approval workflow
4. Enable bi-directional sync (Context ↔ TickTick)

**MVP Scope:** Manual sync only, synchronous processing, Ollama LLM, full suggestion history tracking

---

## Phase 1: Database Schema & Models

### Task 1.1: Create Project Model
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/models/project.py`

**Requirements:**
- Fields: id, user_id, ticktick_project_id, name, color, sort_order, is_archived, created_at, updated_at
- Relationship: One-to-Many with Task
- Index on (user_id, ticktick_project_id)

**Completion Criteria:**
- [x] Model file created
- [x] Relationships defined
- [x] Validates with SQLAlchemy

---

### Task 1.2: Create TaskSuggestion Model
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/models/task_suggestion.py`

**Requirements:**
- Fields: id, task_id, suggestion_type, current_value (JSONB), suggested_value (JSONB), reason, confidence, status, created_at, resolved_at, resolved_by_user
- Relationship: Many-to-One with Task
- Index on (task_id, status)

**Completion Criteria:**
- [x] Model file created
- [x] Relationships defined
- [x] Status enum (pending, approved, rejected)

---

### Task 1.3: Extend Task Model
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/models/task.py`

**Add Fields:**
```python
# TickTick Extended Metadata
ticktick_priority: Optional[int]  # 0=None, 1=Low, 3=Medium, 5=High
start_date: Optional[datetime]
all_day: bool = False
reminder_time: Optional[datetime]
repeat_flag: Optional[str]

# Organization
project_name: Optional[str]
parent_task_id: Optional[str]
sort_order: int = 0
column_id: Optional[str]

# Additional Metadata
ticktick_tags: Optional[dict] = None  # JSONB
time_estimate: Optional[int]  # minutes
focus_time: Optional[int]  # minutes

# Sync Tracking
last_synced_at: Optional[datetime]
last_modified_at: Optional[datetime]
sync_version: int = 1
```

**Completion Criteria:**
- [x] All 14 fields added
- [x] Defaults set appropriately
- [x] Relationships to Project and TaskSuggestion added

---

### Task 1.4: Create Alembic Migration
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/alembic/versions/232f0f5bae6c_add_ticktick_metadata_and_suggestions.py`

**Requirements:**
- Create projects table
- Create task_suggestions table
- Add 14 new columns to tasks table
- Create indexes

**Completion Criteria:**
- [x] Migration generated with `alembic revision --autogenerate`
- [x] Migration reviewed for correctness
- [x] Migration tested with `alembic upgrade head`
- [x] Rollback tested with `alembic downgrade -1`

**Notes:**
- Ensure backward compatibility (all fields nullable)
- Verify indexes created correctly
- Fixed foreign key constraint name in downgrade
- Added enum type cleanup in downgrade

---

## Phase 2: Enhanced TickTick Integration (Pull)

### Task 2.1: Update TickTickService.get_tasks()
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/services/ticktick.py`

**Extend metadata extraction to include:**
- `priority` → ticktick_priority
- `startDate` → start_date
- `isAllDay` → all_day
- `tags` → ticktick_tags
- `items` → parent_task_id (for subtasks)
- `sortOrder` → sort_order
- `columnId` → column_id
- `focusSummaries` → focus_time
- `pomodoroSummaries` → time_estimate
- `dueDate` → due_date
- `reminders` → reminder_time (first reminder)
- `repeatFlag` → repeat_flag

**Completion Criteria:**
- [x] All 18 metadata fields extracted from TickTick API response
- [x] Proper type conversion (ISO dates → datetime via _parse_datetime helper)
- [x] Priority mapped correctly (0/1/3/5)
- [x] Tags stored as JSONB array
- [x] Helper methods created for datetime parsing and time calculations

**Implementation Notes:**
- Created `_parse_datetime()` helper for ISO 8601 conversion
- Created `_calculate_time_estimate()` for Pomodoro → minutes conversion
- Created `_calculate_focus_time()` for focus time → minutes conversion
- All 18 fields now extracted and ready for database insertion
- Project name included for display purposes

---

### Task 2.2: Add TickTickService.sync_projects()
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/services/ticktick.py`

**Requirements:**
- Fetch all projects from TickTick
- Upsert into Project model
- Return list of Project objects

**Completion Criteria:**
- [x] Method implemented
- [x] Handles API errors gracefully
- [x] Updates existing projects, creates new ones
- [x] Returns list of Project objects with IDs

**Implementation Notes:**
- Fetches projects via `get_projects()` API call
- Upsert logic: checks for existing by ticktick_project_id, updates or creates
- Updates: name, color, sort_order, is_archived
- Commits to database and refreshes objects
- Logs sync count for debugging

---

### Task 2.3: Update /api/tasks/sync Endpoint
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/api/tasks.py`

**Changes:**
1. First sync projects via `sync_projects()`
2. Then sync tasks with full metadata
3. Set `last_synced_at` timestamp
4. Increment `sync_version`

**Completion Criteria:**
- [x] Projects synced before tasks (STEP 1)
- [x] All 18 new fields populated from task_data
- [x] Sync timestamp updated
- [x] Project mapping created (ticktick_project_id → db project_id)
- [x] Tasks linked to projects via project_id foreign key
- [x] Response includes project count

**Implementation Notes:**
- Two-step sync: projects first, then tasks
- Project map ensures valid foreign key references
- Task data includes all 18 metadata fields
- Upsert logic for both new and existing tasks
- Error handling with logging
- Response message shows project and task counts

---

## Phase 3: Project Management

### Task 3.1: Create Projects API Router
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/api/projects.py` (NEW)

**Endpoints:**
- `GET /api/projects` - List user's projects from DB
- `POST /api/projects/sync` - Force sync from TickTick

**Completion Criteria:**
- [x] Router created and registered in main.py
- [x] Both endpoints implemented
- [x] Proper authentication/authorization (uses user_id query param)
- [x] Response schemas documented

**Implementation Notes:**
- Created new projects.py router with APIRouter
- GET endpoint returns all non-archived projects for user
- POST endpoint triggers sync_projects() and returns synced count
- Both endpoints use user_id query parameter (default: 1)
- Error handling for missing user, TickTick not connected
- Registered in main.py app router includes

---

### Task 3.2: Frontend ProjectSelector Component
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `frontend/src/components/ProjectSelector.tsx` (NEW)

**Requirements:**
- Dropdown showing user's projects
- Used in task creation/edit forms
- Fetches from `/api/projects`

**Completion Criteria:**
- [ ] Component created
- [ ] Integrated into task forms
- [ ] Shows project name and color

---

### Task 3.3: Frontend Project Display on TaskCard
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `frontend/src/components/TaskCard.tsx`

**Changes:**
- Add project badge/label
- Use project color if available
- Show "No Project" if unassigned

**Completion Criteria:**
- [ ] Project displayed on task cards
- [ ] Styling matches design system

---

## Phase 4: LLM Suggestion Engine

### Task 4.1: Create Versioned Prompt File
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/prompts/task_analysis_suggestions_v1.txt` (NEW)

**Prompt Requirements:**
- Input: task details, project context, related tasks, user workload
- Output: JSON with suggestions array
- Each suggestion: type, current, suggested, current_display, suggested_display, reason, confidence
- TickTick-compatible values (priority 0/1/3/5)

**Completion Criteria:**
- [x] Prompt file created
- [x] Tested with sample inputs
- [x] Generates valid JSON

**Implementation Notes:**
- Created comprehensive prompt with detailed examples
- Includes all suggestion types: priority, tags, start_date, quadrant
- Provides clear guidance on confidence scoring (0.5-1.0 scale)
- Emphasizes respecting user's explicit choices
- Examples demonstrate TickTick priority mapping (0/1/3/5)
- Fixed prompt to prevent LLM from echoing input by using chat API endpoint

---

### Task 4.2: Update LLMService.analyze_task()
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/services/llm_ollama.py`

**Changes:**
1. Rename to `generate_suggestions()`
2. Accept project_context, related_tasks, workload parameters
3. Load prompt from versioned file
4. Parse suggestions JSON response
5. Return list of suggestion dicts

**Completion Criteria:**
- [x] Method refactored (added new method, kept old for backward compatibility)
- [x] Accepts context parameters
- [x] Returns suggestion format
- [x] Handles LLM errors gracefully

**Implementation Notes:**
- Created `load_prompt_template()` helper function
- Added `generate_suggestions()` method with comprehensive context support
- Uses chat API endpoint (`/api/chat`) instead of generate for better control
- Added `think: False` flag to work around Qwen3 thinking mode
- Fallback to `thinking` field if `content` is empty
- Robust JSON parsing with regex fallback
- Structure validation ensures "analysis" and "suggestions" keys present
- Created `workload_calculator.py` service with helper functions:
  - `calculate_user_workload()` - gets task counts and hours by quadrant
  - `get_project_context()` - gets project metadata and task counts
  - `get_related_tasks()` - finds related tasks in same project
- Test script created and verified working with 2 scenarios

---

## Phase 5: Suggestion API & Workflow

### Task 5.1: Create Suggestion Endpoints
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `backend/app/api/tasks.py`

**New Endpoints:**
- `POST /api/tasks/{id}/analyze` - Trigger user-initiated analysis
- `POST /api/tasks/analyze/batch` - Bulk analysis (body: task_ids array)
- `GET /api/tasks/{id}/suggestions` - Get pending suggestions
- `POST /api/tasks/{id}/suggestions/approve` - Approve (body: suggestion_types or "all")
- `POST /api/tasks/{id}/suggestions/reject` - Reject (body: suggestion_types or "all")

**Completion Criteria:**
- [ ] All 5 endpoints implemented
- [ ] Suggestions stored in TaskSuggestion model
- [ ] Approve updates Task fields
- [ ] Batch analysis handles multiple tasks

---

### Task 5.2: Implement Approval Logic
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `backend/app/api/tasks.py`

**Approval Flow:**
1. Fetch pending suggestions for task
2. Filter by suggestion_types (if specified)
3. Apply each suggestion to Task model fields
4. Mark suggestions as "approved"
5. Trigger push sync to TickTick
6. Increment sync_version

**Completion Criteria:**
- [ ] Approval applies changes to Task
- [ ] Suggestions marked resolved
- [ ] TickTick updated via push sync

---

## Phase 6: Bi-directional Sync (Push to TickTick)

### Task 6.1: Add TickTick Push Methods
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/services/ticktick.py`

**New Methods:**
- `update_task(ticktick_task_id, data, db)` - POST to TickTick API (TickTick uses POST for updates)
- `create_task(data, db)` - POST to TickTick API
- `delete_task(ticktick_task_id, project_id, db)` - DELETE to TickTick API

**Completion Criteria:**
- [x] All 3 methods implemented
- [x] Proper error handling with HTTPException
- [x] Token refresh on 401 errors
- [x] Logging for debugging

**Implementation Notes:**
- Added `refresh_user_token()` method to handle token expiry
- Modified `__init__` to accept optional User object for authenticated calls
- All methods include retry logic for 401 (token expired) errors
- Proper mapping between Context fields and TickTick API fields

---

### Task 6.2: Update PUT /api/tasks/{id} for Push Sync
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/api/tasks.py`

**Changes:**
1. On task update, check if ticktick_task_id exists
2. If exists, push changes to TickTick via `update_task()`
3. Update last_modified_at, last_synced_at
4. Increment sync_version
5. Preserve manual_override flags

**Completion Criteria:**
- [x] Manual edits push to TickTick
- [x] Sync happens within same request
- [x] Errors logged but don't block local update
- [x] Track changes to only sync modified fields
- [x] DELETE endpoint also syncs to TickTick

**Implementation Notes:**
- Updated both PUT and DELETE endpoints
- Changes tracked via `changes` dict to only sync what changed
- User fetched from DB to get TickTick credentials
- Graceful error handling - sync failures don't block local updates
- Soft delete also triggers TickTick deletion

---

### Task 6.3: Implement Conflict Resolution
**Status:** ✅ Complete
**Assignee:** Claude Code
**File:** `backend/app/services/sync_service.py` (NEW)

**Logic:**
- Manual user changes always win
- Use sync_version to detect conflicts
- Last-write-wins for non-override fields

**Completion Criteria:**
- [x] Manual overrides preserved
- [x] Conflict detection works
- [x] Sync_version incremented correctly
- [x] Comprehensive test coverage

**Implementation Notes:**
- Created `SyncConflictResolver` class with conflict resolution logic
- Protected fields: quadrant-related (if manual_quadrant_override), priority (if manual_priority_override)
- Timestamp comparison to determine which data is newer
- Timezone-aware timestamp handling with fallback to naive datetimes
- Created `SyncService` class for sync orchestration
- Added `should_sync_to_ticktick()` helper method
- Added `get_sync_status()` for debugging
- All tests passing (9/9)

---

## Phase 7: Frontend Suggestion UI

### Task 7.1: Create SuggestionBadge Component
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `frontend/src/components/SuggestionBadge.tsx` (NEW)

**Features:**
- Shows pending suggestion count
- Different states: pending, partially applied, all applied
- Click to expand suggestions

**Completion Criteria:**
- [ ] Component created
- [ ] Shows correct states
- [ ] Integrated into TaskCard

---

### Task 7.2: Create SuggestionPanel Component
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `frontend/src/components/SuggestionPanel.tsx` (NEW)

**Features:**
- Collapsible list of suggestions
- Individual approve/reject buttons
- "Approve All" / "Dismiss All" actions
- Show TickTick values (priority 0/1/3/5)
- Display confidence and reasoning

**Completion Criteria:**
- [ ] Component created
- [ ] All actions wired to API
- [ ] UI matches design mockups

---

### Task 7.3: Add Analyze Button to TaskCard
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `frontend/src/components/TaskCard.tsx`

**Changes:**
- Add "⚡ Analyze with AI" button
- Shows loading state during analysis
- Disabled if analysis already pending

**Completion Criteria:**
- [ ] Button added
- [ ] Calls `/api/tasks/{id}/analyze`
- [ ] Shows loading spinner

---

### Task 7.4: Add Bulk Selection UI
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `frontend/src/components/EisenhowerMatrix.tsx`

**Changes:**
- Add checkbox to each TaskCard
- Toolbar with "⚡ Analyze Selected (N)" button
- Selection state management

**Completion Criteria:**
- [ ] Checkboxes added
- [ ] Bulk analyze button works
- [ ] Calls `/api/tasks/analyze/batch`

---

### Task 7.5: Display TickTick Metadata on TaskCard
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `frontend/src/components/TaskCard.tsx`

**Add Display For:**
- TickTick priority (0/1/3/5 with badge)
- Project name
- TickTick tags (differentiated from AI tags)
- Start date

**Completion Criteria:**
- [ ] All metadata displayed
- [ ] Clear visual hierarchy
- [ ] Doesn't clutter card

---

### Task 7.6: Update Frontend API Client
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `frontend/src/lib/api.ts`

**Add Methods:**
- `analyzeTask(taskId)`
- `analyzeBatch(taskIds)`
- `getSuggestions(taskId)`
- `approveSuggestions(taskId, types)`
- `rejectSuggestions(taskId, types)`
- `getProjects()`
- `syncProjects()`

**Completion Criteria:**
- [ ] All methods implemented
- [ ] Proper TypeScript types
- [ ] Error handling

---

## Phase 8: Remove Auto-Analysis

### Task 8.1: Remove Auto-Analysis from POST /api/tasks
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `backend/app/api/tasks.py`

**Changes:**
- Remove LLM analysis call from task creation
- Task created without urgency/importance initially
- User must manually trigger analysis

**Completion Criteria:**
- [ ] Auto-analysis removed
- [ ] Task creation faster
- [ ] No breaking changes

---

### Task 8.2: Remove Auto-Analysis from Sync
**Status:** ⏳ Not Started
**Assignee:** TBD
**File:** `backend/app/api/tasks.py`

**Changes:**
- Remove LLM analysis from `/api/tasks/sync`
- Sync only imports metadata from TickTick
- Analysis happens only when user requests

**Completion Criteria:**
- [ ] Auto-analysis removed from sync
- [ ] Sync speed improved

---

## Phase 9: Testing & Validation

### Task 9.1: End-to-End Manual Testing
**Status:** ⏳ Not Started
**Assignee:** TBD

**Test Scenarios:**
1. Initial sync from TickTick captures all metadata
2. Projects display correctly
3. Click "Analyze" → suggestions appear
4. Approve suggestion → TickTick updates
5. Manual edit → pushes to TickTick
6. Bulk analysis works
7. Priority values always 0/1/3/5

**Completion Criteria:**
- [ ] All 7 scenarios pass
- [ ] No console errors
- [ ] Performance acceptable

---

### Task 9.2: Unit Tests
**Status:** ⏳ Not Started
**Assignee:** TBD

**Test Coverage:**
- TickTick push methods
- Suggestion generation
- Approval/rejection logic
- Conflict resolution

**Completion Criteria:**
- [ ] Tests written
- [ ] All tests pass
- [ ] Coverage >70%

---

## Progress Dashboard

### Overall Status: 13/35 Tasks Complete (37%)

**Phase 1:** 4/4 ✅✅✅✅
**Phase 2:** 3/3 ✅✅✅
**Phase 3:** 1/3 ✅⬜⬜
**Phase 4:** 2/2 ✅✅
**Phase 5:** 0/2 ⬜⬜
**Phase 6:** 3/3 ✅✅✅
**Phase 7:** 0/6 ⬜⬜⬜⬜⬜⬜
**Phase 8:** 0/2 ⬜⬜
**Phase 9:** 0/2 ⬜⬜

---

## How to Use This Document

**For Main Agent:**
- Update overall status and phase progress
- Assign tasks to subagents
- Track dependencies between phases

**For Subagents:**
- When assigned a task, update Status to "🔄 In Progress"
- Check off completion criteria as you complete them
- When done, update Status to "✅ Complete"
- Add notes/blockers in the task section

**Status Legend:**
- ⏳ Not Started
- 🔄 In Progress
- ✅ Complete
- ⚠️ Blocked
- ❌ Failed/Skipped

---

## Notes & Decisions

### 2025-12-11

**Early Morning Session:**
- **Decided:** Synchronous processing (no Celery for MVP)
- **Decided:** Manual sync only (no webhooks/polling)
- **Decided:** Keep Ollama/Qwen3 LLM
- **Decided:** Separate TaskSuggestion model for history tracking
- **Completed:** Phase 1 - Database Schema & Models
  - Created Project model with TickTick integration fields
  - Created TaskSuggestion model with status tracking (pending/approved/rejected)
  - Extended Task model with 16 new fields (14 specified + project_id + relationships)
  - Migration 232f0f5bae6c successfully applied
  - All database schema changes verified
- **Completed:** Phase 4 - LLM Suggestion Engine
  - Created versioned prompt file with comprehensive examples (task_analysis_suggestions_v1.txt)
  - Implemented generate_suggestions() method in LLMService
  - Added workload_calculator.py service with context helpers
  - Successfully tested with 2 scenarios, generating accurate suggestions
  - Fixed Qwen3 model quirks (using chat API, think:False flag)
  - Prompt includes clear TickTick priority mapping (0/1/3/5)
- **Completed:** Phase 6 - Bi-directional Sync (Push to TickTick)
  - Implemented push sync methods: update_task(), create_task(), delete_task()
  - Updated PUT and DELETE endpoints to sync changes to TickTick
  - Created comprehensive conflict resolution logic in sync_service.py
  - Manual overrides always preserved during sync
  - Token refresh handling for expired TickTick credentials
  - All 9 tests passing with complete coverage
  - Graceful error handling - sync failures don't block local operations

**Afternoon Session:**
- **Completed:** Phase 2 - Enhanced TickTick Integration (Pull)
  - Updated TickTickService.get_tasks() to extract 18 comprehensive metadata fields
  - Added 3 helper methods: _parse_datetime(), _calculate_time_estimate(), _calculate_focus_time()
  - Implemented sync_projects() method for project synchronization
  - Updated /api/tasks/sync to sync projects before tasks
  - Created project_id mapping for proper foreign key references
  - All metadata now populates: priority, dates, tags, reminders, time tracking, organization
- **Completed:** Phase 3 Task 3.1 - Projects API Router
  - Created new backend/app/api/projects.py with GET and POST endpoints
  - Registered router in main.py
  - GET /api/projects returns all projects for user
  - POST /api/projects/sync triggers manual project sync
- **Testing:**
  - Created comprehensive test suite (test_phase2_implementation.py)
  - All tests passing (100% success rate)
  - Verified all 18 metadata fields map to Task model columns
  - Confirmed API structure and routing
  - Validated helper methods with edge cases

**Summary Documents Created:**
- PHASE2_IMPLEMENTATION_SUMMARY.md - Comprehensive implementation guide
- EXAMPLE_ENHANCED_TASK_DATA.json - Example task object with all metadata
- test_phase2_implementation.py - Automated test suite

---

## Blockers & Risks

*None currently identified*

---

Last Updated: 2025-12-11 by Claude Code (Phases 1, 2 (complete), 3 (1/3), 4, 6 Complete)
