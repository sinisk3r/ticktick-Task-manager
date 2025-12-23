# Seamless Chat UX - Major Feature Update Plan

## Executive Summary

Upgrade the current ReAct agent to a **LangChain v1 single agent with middleware** that acts as a personal task assistant - learning user preferences, adapting tone/style, proactively helping with prioritization, and providing a seamless conversational experience.

**Architecture Choice: Option A - Single Agent + Middleware** (confirmed)

---

## User-Confirmed Choices

| Decision | Choice |
|----------|--------|
| **Reminders** | In-app toast notifications only (no email) |
| **Vision Model** | Gemini Flash (already integrated) - lower priority |
| **Work Style Discovery** | Auto-detect from patterns (zero friction) |
| **Priority Features** | Memory + Tone, Day planning, Reminders |

---

## Architectural Recommendation

### Option A vs Option B: Which to Choose?

| Criteria | Option A: Single Agent + Middleware | Option B: Multi-Agent Supervisor |
|----------|-------------------------------------|----------------------------------|
| **Complexity** | Simpler, less code | More complex, more files |
| **Routing** | LLM decides tool to call | Supervisor decides agent to call |
| **Latency** | Single LLM call per action | 2+ LLM calls (supervisor → agent) |
| **Flexibility** | All tools available always | Specialized agents, cleaner separation |
| **Debugging** | Easier - single agent trace | Harder - multi-agent handoffs |

**Recommendation: Start with Option A**

Given your use case (task management + planning + memory), a single agent with middleware is likely sufficient because:
1. **Tool count is manageable** (~15 tools) - no need to split into agents
2. **Lower latency** - critical for chat UX
3. **Middleware handles personalization** - dynamic prompts based on user preferences
4. **Easier to iterate** - add tools without redesigning agent structure

**When to switch to Option B:**
- If you need 30+ tools (agent confusion increases)
- If you want different LLM models per domain (e.g., Claude for planning, Gemini for analysis)
- If you need complex multi-step workflows with human-in-the-loop approval

---

## Current State Analysis

### What Exists
- **Agent**: Single LangGraph ReAct agent with 12 tools (task CRUD, analyze, stale detection, breakdown, email draft, workload, rest)
- **Memory**: `MemorySaver` for conversation history (in-memory only, lost on restart)
- **Streaming**: SSE-based with rich event types (thinking, step, tool_request, tool_result, message)
- **User Profile**: Basic JSONB fields (people, pets, activities, notes) - max 1000 chars total
- **Chat UI**: `ChatPanel.tsx` (912 lines) with task card rendering, error handling, export

### Current Limitations
1. **No persistent memory** - Chat cleared on page refresh, no learning across sessions
2. **No user preference adaptation** - Same tone/style for all users
3. **No proactive behavior** - Only responds to user queries, doesn't ping/remind
4. **Single agent bottleneck** - All logic in one agent, complex routing in system prompt
5. **No work style detection** - No patterns learned over time
6. **No image processing** - Can't handle photos of physical notes

---

## Proposed Architecture: Single Agent + Middleware (LangChain v1)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MAIN AGENT (create_agent)                           │
│  - Single agent with all tools                                          │
│  - Middleware for dynamic prompts & personalization                    │
│  - LLM decides which tool to call                                       │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ TASK TOOLS  │ │PLANNING     │ │MEMORY TOOLS │ │ANALYSIS     │ │REMINDER     │
│             │ │TOOLS        │ │             │ │TOOLS        │ │TOOLS        │
│- create     │ │- prioritize │ │- store_pref │ │- workload   │ │- check_due  │
│- update     │ │- suggest    │ │- get_context│ │- stale      │ │- schedule   │
│- complete   │ │- breakdown  │ │- detect_pat │ │- rest_rec   │ │             │
│- delete     │ │             │ │             │ │             │ │             │
│- fetch      │ │             │ │             │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
    ┌─────────────────────┐         ┌─────────────────────┐
    │   MEMORY STORE      │         │   CHECKPOINTER      │
    │ (PostgreSQL-backed) │         │ (PostgreSQL-backed) │
    │ - User preferences  │         │ - Thread state      │
    │ - Work style        │         │ - Conversation hist │
    │ - Learned facts     │         │ - Short-term memory │
    └─────────────────────┘         └─────────────────────┘
```

**Key Components:**
- **Middleware** - `@dynamic_prompt` injects user preferences into system prompt
- **Memory Store** - Cross-thread persistence for learned facts & preferences
- **Checkpointer** - Thread-scoped conversation history

---

## Implementation Phases

### Phase 1: Foundation - Persistent Memory Store
**Goal**: Enable cross-session learning and preference storage

**New Components**:
1. **Memory Store Schema** (`backend/app/models/memory.py`)
   - `UserMemory` model: user_id, namespace, key, value (JSONB), embedding (pgvector)
   - Namespaces: "preferences", "work_style", "learned_facts", "tone_settings"

2. **LangGraph Store Integration** (`backend/app/agent/memory_store.py`)
   - Custom `PostgresStore` implementation using SQLAlchemy
   - Semantic search using pgvector embeddings
   - CRUD operations: put, get, search, delete

3. **Profile Enhancement** (`backend/app/models/profile.py`)
   - Add: `work_style` (enum: deep_focus, meeting_heavy, context_switcher, structured, flexible)
   - Add: `preferred_tone` (enum: professional, friendly, casual, direct, encouraging)
   - Add: `energy_pattern` (JSONB: peak hours, low energy times)
   - Add: `communication_style` (JSONB: verbose/concise, formal/informal)

**Files to Modify**:
- `backend/app/models/memory.py` (NEW)
- `backend/app/models/profile.py` (EXTEND)
- `backend/app/agent/memory_store.py` (NEW)
- `backend/alembic/versions/xxx_add_memory_store.py` (NEW)

---

### Phase 2: Upgrade to LangChain v1 Agent
**Goal**: Replace `create_react_agent` with `create_agent` + middleware

**New Components**:
1. **Main Agent** (`backend/app/agent/main_agent.py`)
   - Uses LangChain v1 `create_agent` API
   - All tools in single agent (~15-20 tools)
   - Custom state schema for user context

2. **Middleware** (`backend/app/agent/middleware.py`)
   - `@dynamic_prompt` - Injects user preferences into system prompt
   - Loads preferences from memory store at invocation time
   - Adapts tone, verbosity, work style

3. **State Schema** (`backend/app/agent/state.py`)
   - `CustomState(AgentState)` with user_id, preferences, work_style
   - Passed to middleware for personalization

**Files to Modify**:
- `backend/app/agent/main_agent.py` (NEW - replaces graph.py)
- `backend/app/agent/middleware.py` (NEW - dynamic prompts)
- `backend/app/agent/state.py` (NEW - custom state schema)
- `backend/app/agent/graph.py` (DEPRECATE - keep for backward compat)
- `backend/app/api/agent.py` (REFACTOR - use new agent)

---

### Phase 3: New Tools for Seamless UX
**Goal**: Add tools that enable conversational task management

**New Tools**:
1. `prioritize_day` - Suggest task order based on urgency, importance, energy patterns
2. `find_relevant_tasks` - Semantic search across task titles/descriptions
3. `update_user_preference` - Store tone, style, work pattern preferences
4. `learn_fact` - Remember user-provided context (e.g., "I have a meeting at 2pm")
5. `recall_context` - Retrieve learned facts relevant to current query
6. `detect_work_style` - Analyze task patterns to infer work style
7. `schedule_reminder` - Set reminders for specific tasks (in-app or push)
8. `check_overdue_tasks` - Identify tasks past due date

**Files to Modify**:
- `backend/app/agent/tools.py` (ADD new tools)
- `backend/app/agent/tools/planning_tools.py` (NEW)
- `backend/app/agent/tools/memory_tools.py` (NEW)
- `backend/app/agent/tools/reminder_tools.py` (NEW)

---

### Phase 4: Tone & Style Adaptation
**Goal**: Assistant adapts communication style to user preference

**Implementation**:
1. **Tone Injection** - Include user's preferred tone in system prompts
2. **Dynamic System Message** - Vary based on user's work_style and preferred_tone
3. **Style Detection** - Analyze user's message patterns to suggest tone changes
4. **A/B Response Preview** - Let user see different tones before choosing

**System Prompt Template**:
```python
def get_personalized_system_message(user_preferences):
    base = "You are Context, an AI task assistant."

    if user_preferences.preferred_tone == "casual":
        base += " Keep it relaxed and friendly. Use contractions, be warm."
    elif user_preferences.preferred_tone == "direct":
        base += " Be concise and to-the-point. No fluff."
    elif user_preferences.preferred_tone == "encouraging":
        base += " Be supportive and celebratory of progress."

    if user_preferences.work_style == "structured":
        base += " Offer organized, step-by-step guidance."
    elif user_preferences.work_style == "flexible":
        base += " Keep suggestions open-ended, allow exploration."

    return base
```

**Files to Modify**:
- `backend/app/agent/prompts.py` (NEW - centralize system prompts)
- `backend/app/api/agent.py` (EXTEND - pass user preferences)

---

### Phase 5: Image Processing (Vision Agent)
**Goal**: Extract tasks from photos of physical notes

**Implementation**:
1. **Vision-capable LLM** - Use Gemini Flash or GPT-4V for image understanding
2. **Image Upload Endpoint** - Accept image files in chat
3. **OCR + Task Extraction** - Extract text, identify task-like items
4. **Confirmation Flow** - Show extracted tasks for user approval before creation

**Flow**:
```
User uploads image → Vision Agent extracts text →
Parse tasks → Show preview → User confirms →
Orchestrator routes to Task Agent → Create tasks
```

**Files to Modify**:
- `backend/app/agent/agents/vision_agent.py` (NEW)
- `backend/app/api/agent.py` (EXTEND - handle file uploads)
- `frontend/components/ChatPanel.tsx` (EXTEND - image upload UI)

---

### Phase 6: Proactive Reminders
**Goal**: Assistant pings user about pending tasks

**Implementation**:
1. **Background Worker** (Celery task)
   - Runs every 30 mins
   - Checks for overdue tasks, approaching deadlines
   - Generates reminder messages

2. **WebSocket/SSE Push**
   - Push reminders to connected clients
   - Show notification toast in UI

3. **Smart Reminder Logic**
   - Prioritize Q1 (urgent+important) tasks
   - Respect user's work hours (don't remind at midnight)
   - Batch reminders to avoid notification fatigue

**Files to Modify**:
- `backend/app/workers/reminder_worker.py` (NEW)
- `backend/app/api/websocket.py` (NEW or EXTEND)
- `frontend/components/NotificationToast.tsx` (NEW)
- `frontend/lib/useNotifications.ts` (NEW)

---

### Phase 7: Chat Persistence
**Goal**: Preserve chat history across sessions

**Implementation**:
1. **Chat History Model** (`backend/app/models/chat.py`)
   - `ChatSession`: user_id, created_at, title
   - `ChatMessage`: session_id, role, content, metadata, timestamp

2. **API Endpoints**:
   - `GET /api/chat/sessions` - List user's chat sessions
   - `GET /api/chat/sessions/{id}` - Get messages for session
   - `POST /api/chat/sessions` - Create new session
   - `DELETE /api/chat/sessions/{id}` - Delete session

3. **Frontend Changes**:
   - Session list sidebar
   - Resume previous conversations
   - Search across chat history

**Files to Modify**:
- `backend/app/models/chat.py` (NEW)
- `backend/app/api/chat.py` (NEW)
- `frontend/components/ChatHistory.tsx` (NEW)
- `frontend/components/ChatPanel.tsx` (EXTEND)

---

## Critical Files to Modify

### Backend (Python)
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/agent/main_agent.py` | NEW | LangChain v1 create_agent |
| `backend/app/agent/middleware.py` | NEW | @dynamic_prompt for personalization |
| `backend/app/agent/state.py` | NEW | CustomState schema |
| `backend/app/agent/memory/store.py` | NEW | PostgresStore wrapper |
| `backend/app/agent/memory/tone_detector.py` | NEW | Auto-detect user tone |
| `backend/app/agent/tools/planning_tools.py` | NEW | prioritize_day, suggest_order |
| `backend/app/agent/tools/memory_tools.py` | NEW | store_pref, get_context, detect_pattern |
| `backend/app/agent/tools.py` | EXTEND | Add new tools |
| `backend/app/agent/graph.py` | DEPRECATE | Keep for backward compat |
| `backend/app/api/agent.py` | REFACTOR | Use new agent + memory store |
| `backend/app/services/reminder_service.py` | NEW | Background reminder worker |
| `backend/app/api/notifications.py` | NEW | SSE notification stream |

### Frontend (TypeScript/React)
| File | Action | Purpose |
|------|--------|---------|
| `frontend/components/ChatPanel.tsx` | EXTEND | Notification integration |
| `frontend/components/NotificationToast.tsx` | NEW | Reminder toast UI |
| `frontend/lib/useNotifications.ts` | NEW | SSE notification hook |

### Database
| Migration | Purpose |
|-----------|---------|
| `add_memory_store.py` | LangGraph PostgresStore tables |
| `add_reminder_schedules.py` | Reminder tracking table |

---

## Dependencies to Add

```txt
# requirements.txt additions (Dec 2025 - LangChain v1 + LangGraph v1)
langchain>=1.0.0             # NEW: create_agent with middleware
langgraph>=1.0.0             # Stable v1 release
langgraph-checkpoint-postgres  # PostgreSQL checkpointer
langgraph-supervisor>=0.1.0  # Multi-agent supervisor (if using Option B)
pgvector>=0.3.0              # Vector embeddings for memory search
```

**Note:** The current codebase uses `langchain==0.3.13` and `langgraph==0.2.60`. Upgrade path:
```bash
pip install -U langchain langgraph langgraph-checkpoint-postgres
```

---

## Detailed Implementation

### IMPORTANT: LangChain v1 Updates (Dec 2025)

Per latest LangChain docs:
- **`create_react_agent` is DEPRECATED** - Use `create_agent` from `langchain.agents`
- **Middleware system** for customization (prompts, state injection)
- LangGraph v1 stable - core graph APIs unchanged

### Agent Structure (LangChain v1 + LangGraph v1)

**Option A: Single Agent with Middleware (Recommended for simpler routing)**
```python
# backend/app/agent/main_agent.py
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest

class CustomState(AgentState):
    user_id: int
    user_preferences: dict
    work_style: str

@dynamic_prompt
def personalized_prompt(request: ModelRequest) -> str:
    prefs = request.state.get("user_preferences", {})
    tone = prefs.get("tone", "friendly")
    return f"You are Context, a helpful task assistant. Tone: {tone}"

agent = create_agent(
    model="gemini-2.0-flash",  # or user's configured model
    tools=[
        # Task tools
        create_task, update_task, complete_task, delete_task, fetch_tasks,
        # Planning tools
        prioritize_day, suggest_task_order, breakdown_task,
        # Memory tools
        store_user_preference, get_user_context, detect_work_pattern,
        # Analysis tools
        get_workload_analytics, detect_stale_tasks, get_rest_recommendation,
    ],
    state_schema=CustomState,
    middleware=[personalized_prompt],
)
```

**Option B: Multi-Agent Supervisor (For complex routing)**
```python
# backend/app/agent/supervisor.py
from langchain.agents import create_agent
from langgraph_supervisor import create_supervisor

# Create specialized agents using new create_agent API
task_agent = create_agent(
    model=model,
    tools=get_task_tools(),
    system_prompt="You handle task CRUD operations.",
    name="task_agent",
)

planning_agent = create_agent(
    model=model,
    tools=get_planning_tools(),
    system_prompt="You help with day planning and prioritization.",
    name="planning_agent",
)

# Supervisor orchestrates handoffs
supervisor = create_supervisor(
    agents=[task_agent, planning_agent],
    model=model,
    prompt="Route to task_agent for CRUD, planning_agent for scheduling.",
).compile(checkpointer=checkpointer, store=store)
```

### Memory Store Namespaces

```
Namespace Structure:
- (user_id, "preferences")     -> tone, communication style, work hours
- (user_id, "learned_facts")   -> names, projects, recurring patterns
- (user_id, "work_patterns")   -> task creation times, completion rates, avoidance
```

### Tone Detection & Adaptation

```python
# backend/app/agent/tone_detector.py
class ToneDetector:
    CONCISE_INDICATORS = [r"^(yes|no|ok|done|thanks)$", r"^.{1,20}$"]
    CASUAL_INDICATORS = [r"(lol|haha|omg|btw)", r"[:;]-?[)D(P]"]

    @classmethod
    def get_tone_instruction(cls, preferences: dict) -> str:
        tone = preferences.get("tone", "friendly")
        if tone == "concise":
            return "Keep responses very brief (1-2 sentences max)."
        elif tone == "professional":
            return "Use formal, professional language."
        elif tone == "encouraging":
            return "Be motivational and supportive in tone."
        return "Be warm and conversational."
```

### New Planning Tools

```python
# backend/app/agent/tools/planning_tools.py
@tool
async def prioritize_day(config, focus_areas=None, available_hours=8.0) -> Dict:
    """Create prioritized plan for today based on Q1/Q2 tasks."""
    # Fetch active Q1/Q2 tasks, sort by due date + priority
    # Return schedule with time allocations and break suggestions

@tool
async def suggest_task_order(config, task_ids: List[int], optimization_goal="completion") -> Dict:
    """Suggest optimal order: completion (quick wins), impact, energy, deadlines."""
```

### Memory Tools

```python
# backend/app/agent/tools/memory_tools.py
@tool
async def store_user_preference(config, preference_key: str, preference_value: str) -> Dict:
    """Store learned user preference (tone, verbosity, work_hours)."""

@tool
async def get_user_context(config) -> Dict:
    """Retrieve stored preferences, learned facts, and work patterns."""

@tool
async def detect_work_pattern(config, analysis_period_days=14) -> Dict:
    """Analyze task history to detect work style (early_bird, night_owl, etc.)."""
```

### Reminder Service (Background Worker)

```python
# backend/app/services/reminder_service.py
class ReminderService:
    OVERDUE_CHECK_INTERVAL = 3600  # 1 hour

    async def _reminder_loop(self):
        while self.running:
            await self._check_overdue_tasks()
            await self._check_upcoming_deadlines()
            await asyncio.sleep(self.OVERDUE_CHECK_INTERVAL)

    async def _queue_notification(self, user_id, notification_type, data):
        # Store notification for SSE pickup by frontend
```

### Frontend Notification Hook

```typescript
// frontend/lib/useNotifications.ts
export function useNotifications(userId: number) {
  useEffect(() => {
    const eventSource = new EventSource(`/api/notifications/stream?user_id=${userId}`);

    eventSource.addEventListener('overdue', (event) => {
      const data = JSON.parse(event.data);
      toast.warning(`${data.count} overdue task(s)`, {
        description: data.tasks.slice(0, 3).map(t => t.title).join(', '),
        action: { label: 'View', onClick: () => navigate('/matrix?filter=overdue') },
      });
    });

    return () => eventSource.close();
  }, [userId]);
}
```

---

## Success Criteria

1. **Seamless Conversations** - User can have natural multi-turn conversations
2. **Learning Over Time** - Assistant remembers preferences across sessions
3. **Adaptive Tone** - Responses match user's preferred communication style
4. **Proactive Help** - Reminders surface without user asking
5. **Image Support** - Can create tasks from photos of notes
6. **Day Planning** - Can help prioritize and plan user's day

---

## Estimated Effort (Prioritized)

| Phase | Effort | Priority | Scope |
|-------|--------|----------|-------|
| Phase 1: Memory Store | 2 days | P0 | PostgreSQL-backed LangGraph store |
| Phase 2: Multi-Agent Supervisor | 3 days | P0 | Supervisor + 3 agents (task, planning, memory) |
| Phase 3: New Tools | 2 days | P0 | prioritize_day, suggest_order, memory tools |
| Phase 4: Tone Adaptation | 1 day | P1 | Auto-detect tone, dynamic prompts |
| Phase 5: Proactive Reminders | 2 days | P1 | Background worker + SSE toast |
| Phase 6: Chat Persistence | 1 day | P1 | Optional - conversation history |
| Phase 7: Image Processing | 2 days | P2 | Gemini Flash vision (deferred) |

**MVP Total: ~10 days** (Phases 1-5)

---

## Phased Rollout Plan

### Week 1: Foundation
- [ ] Add dependencies: `langgraph-checkpoint-postgres`, `langgraph-supervisor`
- [ ] Create memory store tables migration
- [ ] Implement `AsyncPostgresStore` and `AsyncPostgresSaver` initialization
- [ ] Create basic supervisor graph structure

### Week 2: Agent Migration + Memory
- [ ] Move existing tools to `task_agent` module
- [ ] Create handoff tools
- [ ] Implement memory tools (store_preference, get_context, detect_pattern)
- [ ] Add tone detection logic

### Week 3: Planning + Reminders
- [ ] Implement `prioritize_day` and `suggest_task_order` tools
- [ ] Create reminder background worker
- [ ] Add notification SSE endpoint
- [ ] Frontend toast integration

### Week 4: Polish + Testing
- [ ] Dynamic prompt generation with user context
- [ ] End-to-end testing of multi-agent flows
- [ ] Performance tuning (agent handoff latency)
- [ ] Update agent test suite

---

## Database Migrations Required

```sql
-- 1. add_memory_store_tables.py
CREATE TABLE user_memory_analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,
    memory_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. add_reminder_schedules.py
CREATE TABLE reminder_schedules (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    reminder_type VARCHAR(50) NOT NULL,
    trigger_at TIMESTAMP WITH TIME ZONE NOT NULL,
    delivered BOOLEAN DEFAULT FALSE
);
CREATE INDEX ix_reminder_trigger ON reminder_schedules(trigger_at, delivered);

-- Note: LangGraph PostgresStore creates its own tables via store.setup()
```

---

## API Contract Changes

The SSE stream format remains **backward compatible**. New events added (additive):

```typescript
type NewSSEEvents =
  | { event: 'agent_handoff'; data: { from: string; to: string } }
  | { event: 'memory_stored'; data: { key: string; value: string } }
  | { event: 'context_loaded'; data: { preferences: object; facts: string[] } };
```

---

## File Structure After Implementation

```
backend/app/agent/
├── main_agent.py            # NEW: LangChain v1 create_agent
├── middleware.py            # NEW: @dynamic_prompt for personalization
├── state.py                 # NEW: CustomState(AgentState)
├── graph.py                 # DEPRECATE: Keep for backward compat
├── memory/
│   ├── __init__.py
│   ├── store.py             # PostgresStore wrapper
│   └── tone_detector.py     # Auto-detect user tone
├── tools/
│   ├── __init__.py
│   ├── planning_tools.py    # NEW: prioritize_day, suggest_order
│   └── memory_tools.py      # NEW: store_pref, get_context
├── tools.py                 # KEEP: Existing 12 tools
└── llm_factory.py           # KEEP: Unchanged

backend/app/services/
└── reminder_service.py      # NEW: Background reminder worker

backend/app/api/
├── agent.py                 # REFACTOR: Use new agent
└── notifications.py         # NEW: SSE notification stream
```

---

## Next Steps

1. **Approve plan** → Exit plan mode
2. **Phase 1** → Install dependencies, create memory store migration
3. **Phase 2** → Build supervisor graph with task + memory agents
4. **Phase 3** → Add planning tools and tone adaptation
5. **Phase 4** → Implement reminder system with toast notifications
