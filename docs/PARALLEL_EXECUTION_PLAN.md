# Parallel Execution Plan - Chat UX v2

## Overview

This document defines how to split the Chat UX v2 feature into **5 parallel workstreams** that can be executed by independent agents without file conflicts.

**Reference:** See `docs/Chat_UX_v2.md` for full feature specification.

---

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 0: FOUNDATION (BLOCKING)                   │
│  - Install langgraph-checkpoint-postgres                            │
│  - Must complete before other streams can start                     │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   STREAM A    │    │   STREAM B    │    │   STREAM C    │
│   Database    │───▶│  Agent Core   │    │   New Tools   │
│   & Models    │    │  & Middleware │    │  (parallel)   │
└───────┬───────┘    └───────┬───────┘    └───────────────┘
        │                    │
        │                    ▼
        │            ┌───────────────┐
        │            │   STREAM D    │
        └───────────▶│   API Layer   │
                     │   Integration │
                     └───────────────┘
                              │
                              ▼
                     ┌───────────────┐
                     │   STREAM E    │
                     │   Frontend    │
                     │  (parallel)   │
                     └───────────────┘
```

---

## Stream Definitions

### PHASE 0: Foundation Setup (BLOCKING - Run First)

**Purpose:** Install dependencies required by all streams

**Owner:** Single agent or manual execution

**Tasks:**
```bash
# 1. Install required packages
cd backend
pip install langgraph-checkpoint-postgres==3.0.2 psycopg[binary,pool]

# 2. Add to requirements.txt
echo "langgraph-checkpoint-postgres==3.0.2" >> requirements.txt
echo "psycopg[binary,pool]" >> requirements.txt
```

**Blocking:** All other streams wait for this to complete.

---

### STREAM A: Database & Models

**Purpose:** Create data models and migrations for memory persistence

**File Ownership (EXCLUSIVE):**
- `backend/app/models/memory.py` (NEW)
- `backend/app/models/profile.py` (MODIFY - add fields)
- `backend/alembic/versions/*_add_memory_and_profile_fields.py` (NEW)

**Tasks:**
1. Create `memory.py` with `UserMemory` model
2. Extend `profile.py` with:
   - `work_style` (VARCHAR enum)
   - `preferred_tone` (VARCHAR enum)
   - `energy_pattern` (JSONB)
   - `communication_style` (JSONB)
3. Create Alembic migration
4. Run migration

**Deliverables:**
- [ ] `UserMemory` model with: user_id, namespace, key, value (JSONB), created_at, updated_at
- [ ] Extended `Profile` model with preference fields
- [ ] Working migration that can be applied

**Dependencies:** None (can start immediately after Phase 0)

**Estimated Time:** 1-2 hours

---

### STREAM B: Agent Core & Middleware

**Purpose:** Implement the new LangChain v1 agent architecture with middleware

**File Ownership (EXCLUSIVE):**
- `backend/app/agent/main_agent.py` (NEW)
- `backend/app/agent/middleware.py` (NEW)
- `backend/app/agent/state.py` (NEW)
- `backend/app/agent/memory/` directory (NEW)
  - `__init__.py`
  - `store.py` (PostgresStore wrapper)
  - `tone_detector.py`

**Tasks:**
1. Create `state.py`:
   ```python
   from langchain.agents import AgentState

   class CustomState(AgentState):
       user_id: int
       user_preferences: dict
       work_style: str
   ```

2. Create `middleware.py`:
   ```python
   from langchain.agents.middleware import dynamic_prompt, ModelRequest

   @dynamic_prompt
   def personalized_prompt(request: ModelRequest) -> str:
       # Load user preferences and adapt system prompt
       ...
   ```

3. Create `main_agent.py`:
   ```python
   from langchain.agents import create_agent

   async def create_context_agent(user_id, db, store, checkpointer):
       # New agent with middleware
       ...
   ```

4. Create `memory/store.py`:
   - Wrapper around `AsyncPostgresStore`
   - Helper methods for namespace management

5. Create `memory/tone_detector.py`:
   - Detect user tone from message patterns
   - Generate tone-specific prompt additions

**Deliverables:**
- [ ] Working `create_agent` implementation with middleware
- [ ] `@dynamic_prompt` that injects user preferences
- [ ] PostgresStore wrapper with namespace helpers
- [ ] Tone detection logic

**Dependencies:**
- STREAM A must complete (needs Profile model fields)
- Phase 0 must complete (needs langgraph-checkpoint-postgres)

**Estimated Time:** 3-4 hours

---

### STREAM C: New Tools

**Purpose:** Create new planning and memory tools

**File Ownership (EXCLUSIVE):**
- `backend/app/agent/tools/` directory (NEW)
  - `__init__.py`
  - `planning_tools.py`
  - `memory_tools.py`

**Tasks:**
1. Create `planning_tools.py`:
   ```python
   @tool(parse_docstring=True)
   async def prioritize_day(...) -> Dict:
       """Create prioritized plan for today based on Q1/Q2 tasks."""

   @tool(parse_docstring=True)
   async def suggest_task_order(...) -> Dict:
       """Suggest optimal task order based on goal."""
   ```

2. Create `memory_tools.py`:
   ```python
   @tool(parse_docstring=True)
   async def store_user_preference(...) -> Dict:
       """Store learned user preference."""

   @tool(parse_docstring=True)
   async def get_user_context(...) -> Dict:
       """Retrieve stored preferences and learned facts."""

   @tool(parse_docstring=True)
   async def detect_work_pattern(...) -> Dict:
       """Analyze task history to detect work style."""
   ```

3. Create `__init__.py` with exports

**Deliverables:**
- [ ] `prioritize_day` tool
- [ ] `suggest_task_order` tool
- [ ] `store_user_preference` tool
- [ ] `get_user_context` tool
- [ ] `detect_work_pattern` tool

**Dependencies:** None - tools can be written with interface stubs

**Estimated Time:** 2-3 hours

---

### STREAM D: API Layer Integration

**Purpose:** Update API layer to use new agent and add notification endpoints

**File Ownership (EXCLUSIVE):**
- `backend/app/api/agent.py` (MODIFY)
- `backend/app/api/notifications.py` (NEW)
- `backend/app/services/reminder_service.py` (NEW)

**Tasks:**
1. Modify `agent.py`:
   - Import new `create_context_agent` from `main_agent.py`
   - Initialize `AsyncPostgresStore` and `AsyncPostgresSaver`
   - Pass user preferences to agent context
   - Keep backward compatibility with existing SSE format

2. Create `notifications.py`:
   ```python
   @router.get("/notifications/stream")
   async def notification_stream(user_id: int):
       # SSE endpoint for push notifications
       ...
   ```

3. Create `reminder_service.py`:
   ```python
   class ReminderService:
       async def check_overdue_tasks(self, user_id: int):
           ...
       async def check_upcoming_deadlines(self, user_id: int):
           ...
   ```

**Deliverables:**
- [ ] Updated `/api/agent/chat` endpoint using new agent
- [ ] New `/api/notifications/stream` SSE endpoint
- [ ] `ReminderService` class with overdue/deadline checks

**Dependencies:**
- STREAM A must complete (Profile model)
- STREAM B must complete (main_agent.py)
- STREAM C should complete (new tools)

**Estimated Time:** 2-3 hours

---

### STREAM E: Frontend Updates

**Purpose:** Add notification UI and integrate with new backend features

**File Ownership (EXCLUSIVE):**
- `frontend/components/NotificationToast.tsx` (NEW)
- `frontend/lib/useNotifications.ts` (NEW)
- `frontend/components/ChatPanel.tsx` (MODIFY - add notification integration)

**Tasks:**
1. Create `useNotifications.ts`:
   ```typescript
   export function useNotifications(userId: number) {
     // Connect to /api/notifications/stream
     // Handle 'overdue', 'deadline', 'reminder' events
     // Return notification state
   }
   ```

2. Create `NotificationToast.tsx`:
   ```typescript
   export function NotificationToast({ notification }) {
     // Render toast with task info
     // Action buttons (View, Dismiss, Snooze)
   }
   ```

3. Modify `ChatPanel.tsx`:
   - Import and use `useNotifications` hook
   - Render `NotificationToast` when notifications arrive
   - Handle new SSE event types

**Deliverables:**
- [ ] Working notification hook with SSE connection
- [ ] Toast component with action buttons
- [ ] ChatPanel integration

**Dependencies:**
- STREAM D must complete (notifications API endpoint)

**Estimated Time:** 2-3 hours

---

## Parallel Execution Matrix

| Time | Agent 1 | Agent 2 | Agent 3 | Agent 4 |
|------|---------|---------|---------|---------|
| T0 | Phase 0: Install deps | - | - | - |
| T1 | STREAM A: Database | STREAM C: Tools | - | - |
| T2 | STREAM B: Agent Core | STREAM C: Tools (cont) | - | - |
| T3 | STREAM D: API | STREAM E: Frontend | - | - |
| T4 | Integration Testing | Integration Testing | - | - |

**Maximum Parallelism:** 2 agents (due to dependencies)
**Recommended:** 2 agents working in parallel

---

## Agent Task Assignments

### Agent 1: Backend Foundation
**Streams:** Phase 0 → A → B → D
**Focus:** Database, models, agent core, API integration

### Agent 2: Tools & Frontend
**Streams:** C → E
**Focus:** New tools, frontend notification system

---

## Conflict Avoidance Rules

1. **File Locking:** Each stream has exclusive ownership of listed files
2. **No Cross-Stream Edits:** Agents must not modify files owned by other streams
3. **Interface First:** Define tool signatures before implementation
4. **Communication Points:**
   - After STREAM A completes, notify STREAM B
   - After STREAM B completes, notify STREAM D
   - After STREAM D completes, notify STREAM E

---

## Integration Checkpoints

### Checkpoint 1: After STREAM A
- [ ] Database migration applied successfully
- [ ] Profile model has new fields
- [ ] UserMemory model created

### Checkpoint 2: After STREAM B + C
- [ ] New agent can be instantiated
- [ ] Middleware loads user preferences
- [ ] All tools have working signatures

### Checkpoint 3: After STREAM D
- [ ] `/api/agent/chat` works with new agent
- [ ] `/api/notifications/stream` returns SSE events
- [ ] ReminderService can query overdue tasks

### Checkpoint 4: Final Integration
- [ ] Frontend receives notifications
- [ ] End-to-end chat flow works
- [ ] Memory persists across sessions

---

## Rollback Plan

If any stream fails:

1. **STREAM A fails:** Other streams cannot proceed. Fix migration issues first.
2. **STREAM B fails:** Fall back to existing `graph.py` agent (backward compat)
3. **STREAM C fails:** Agent works without new tools (existing tools still available)
4. **STREAM D fails:** Keep existing API, defer notifications
5. **STREAM E fails:** Backend works, defer frontend notifications

---

## Success Criteria

- [ ] User preferences persist across sessions
- [ ] Agent adapts tone based on user preference
- [ ] `prioritize_day` tool helps plan daily tasks
- [ ] Notifications appear for overdue tasks
- [ ] No regression in existing functionality
