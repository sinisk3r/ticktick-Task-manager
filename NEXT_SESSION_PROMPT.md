# Phase 3: Task List View & Display - Session Prompt

## Context

**Project:** Context Task Management - AI-powered task management with Eisenhower Matrix
**Current Status:** Phase 2 Complete (TickTick OAuth + Sync Working)
**Next Goal:** Display synced tasks in a list view with AI analysis results

## What's Already Done ✅

### Phase 1 (Completed 2025-12-10)
- ✅ Tabbed UI with Analyze Task | Settings tabs
- ✅ Manual task analysis working via Ollama qwen3:4b
- ✅ Settings UI with model selector and connection testing

### Phase 2 (Completed 2025-12-10)
- ✅ TickTick OAuth integration fully working
- ✅ Backend: OAuth service, auth router, sync endpoint
- ✅ Frontend: OAuth callback page, TickTick connection UI, sync button
- ✅ **60 tasks synced** from real TickTick account
- ✅ **All tasks analyzed** with urgency/importance/quadrant scores
- ✅ Tasks stored in PostgreSQL database with TickTick metadata
- ✅ End-to-end tested with Playwright

### Current Database State
- **1 User** with TickTick OAuth tokens stored
- **60 Tasks** with AI analysis:
  - `title`, `description` (from TickTick)
  - `urgency_score` (1-10), `importance_score` (1-10)
  - `eisenhower_quadrant` (Q1/Q2/Q3/Q4)
  - `analysis_reasoning` (AI explanation)
  - `ticktick_task_id`, `ticktick_project_id` (for sync)

### Current Architecture
```
Frontend (Next.js 14 @ localhost:3000)
    ↓
Backend (FastAPI @ localhost:8000)
    ↓
Ollama (qwen3:4b @ 127.0.0.1:11434)
    ↓
PostgreSQL (Docker @ port 5433)
```

## Your Mission: Phase 3 - Task List View

### Objectives
1. **Create Task List Component** (frontend)
2. **Add "My Tasks" tab** to display synced tasks
3. **Show task cards** with AI analysis
4. **Filter by Eisenhower quadrant**
5. **Display task metadata** (urgency, importance, reasoning)

### Pending Todo List

**Phase 3 (Frontend):**
- [ ] Create TaskList component (`frontend/components/TaskList.tsx`)
- [ ] Add "My Tasks" tab to main page (`frontend/app/page.tsx`)
- [ ] Create TaskCard component for individual task display
- [ ] Add quadrant filter UI (Q1/Q2/Q3/Q4 tabs or dropdown)
- [ ] Display task count per quadrant
- [ ] Show task metadata (urgency/importance scores, reasoning)
- [ ] Add loading states and error handling

**Phase 3 (Optional Backend):**
- [ ] Add endpoint to get tasks grouped by quadrant (optional, can use existing `/api/tasks` with filters)
- [ ] Add task statistics endpoint (counts per quadrant)

**Phase 3 (Testing):**
- [ ] Test task list displays all 60 tasks
- [ ] Test quadrant filtering works
- [ ] Test task detail view shows all AI analysis
- [ ] Playwright E2E testing

**Phase 3 (Documentation):**
- [ ] Update `docs/Plan1-2025-12-09.md` with Phase 3 completion
- [ ] Commit changes to git

## Implementation Plan

### 1. Backend: Task List API (Already Exists!)

The backend already has everything needed:

**Existing Endpoint:**
```python
GET /api/tasks?user_id=1&quadrant=Q1&status=active&limit=100&offset=0
```

**Response:**
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Complete quarterly report",
      "description": "Finish Q4 report by Friday",
      "urgency_score": 8.0,
      "importance_score": 7.0,
      "eisenhower_quadrant": "Q1",
      "analysis_reasoning": "High urgency due to Friday deadline...",
      "status": "active",
      "created_at": "2025-12-10T10:00:00Z",
      "ticktick_task_id": "abc123"
    }
  ],
  "total": 60
}
```

### 2. Frontend: TaskList Component

**File:** `frontend/components/TaskList.tsx`

**Requirements:**
- Fetch tasks from `/api/tasks?user_id=1`
- Display in card grid or list layout
- Show quadrant badge with color coding:
  - Q1 (Urgent & Important): Red
  - Q2 (Not Urgent, Important): Green
  - Q3 (Urgent, Not Important): Yellow
  - Q4 (Neither): Blue
- Display urgency/importance progress bars
- Show analysis reasoning (truncated with "Read more")
- Loading skeleton while fetching
- Empty state if no tasks

**Example Component Structure:**
```typescript
export function TaskList() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedQuadrant, setSelectedQuadrant] = useState<string | null>(null)

  useEffect(() => {
    fetchTasks()
  }, [selectedQuadrant])

  const fetchTasks = async () => {
    // Fetch from /api/tasks with quadrant filter
  }

  return (
    <div>
      {/* Quadrant filter tabs */}
      <QuadrantFilter />

      {/* Task cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tasks.map(task => (
          <TaskCard key={task.id} task={task} />
        ))}
      </div>
    </div>
  )
}
```

### 3. Frontend: Add "My Tasks" Tab

**File:** `frontend/app/page.tsx`

Update the tab navigation to include:
- Analyze Task (manual analysis)
- **My Tasks** (synced tasks list) - NEW!
- Settings (LLM + TickTick)

**Tab Content:**
```typescript
<TabsContent value="my-tasks">
  <TaskList />
</TabsContent>
```

### 4. Task Card Component

**File:** `frontend/components/TaskCard.tsx`

**Display:**
- Title (from TickTick)
- Description (truncated)
- Quadrant badge (colored pill)
- Urgency score with progress bar
- Importance score with progress bar
- AI reasoning (expandable)
- TickTick icon/link (optional)

**Design:**
```
┌─────────────────────────────────────┐
│ 🔴 Q1: Urgent & Important           │
├─────────────────────────────────────┤
│ Complete quarterly report           │
│ Finish Q4 report by Friday...       │
│                                     │
│ Urgency:    ████████░░ 8/10        │
│ Importance: ███████░░░ 7/10        │
│                                     │
│ 💡 High urgency due to Friday...   │
│    [Read more]                      │
└─────────────────────────────────────┘
```

### 5. Quadrant Statistics (Optional)

Show counts at the top:
```
Q1: 15 tasks | Q2: 25 tasks | Q3: 10 tasks | Q4: 10 tasks
```

## Important Notes

### From CLAUDE.md:
- Use Context7 MCP tool for UI library documentation when needed
- Use Playwright for end-to-end testing
- Update plan document when milestones complete
- Commit to git with detailed messages

### From Recent Sessions:
- Backend URL is `http://localhost:8000` (standardized)
- User ID is hardcoded to `1` (single-user mode for now)
- Task API supports filtering by `quadrant`, `status`, `limit`, `offset`
- Quadrant enum: Q1, Q2, Q3, Q4
- Status enum: active, completed, deleted

## Files You'll Create/Modify

**New Files:**
1. `frontend/components/TaskList.tsx` (~150-200 lines)
2. `frontend/components/TaskCard.tsx` (~100-150 lines)
3. `frontend/components/QuadrantFilter.tsx` (~50-80 lines) - Optional

**Files to Modify:**
1. `frontend/app/page.tsx` - Add "My Tasks" tab
2. `docs/Plan1-2025-12-09.md` - Mark Iteration 2 complete, start Iteration 3

## Success Criteria

✅ "My Tasks" tab displays all 60 synced tasks
✅ Tasks organized by Eisenhower quadrant with color coding
✅ Each task card shows urgency/importance scores
✅ AI reasoning is visible and readable
✅ Quadrant filtering works (optional)
✅ Loading states and error handling implemented
✅ Responsive design works on mobile/desktop
✅ Playwright E2E tests pass
✅ Documentation updated
✅ Changes committed to git

## Testing Plan

### Manual Testing
1. Start services: `./init.sh start all`
2. Visit http://localhost:3000
3. Click "My Tasks" tab
4. Verify all 60 tasks appear
5. Check quadrant badges are color-coded correctly
6. Verify urgency/importance scores display
7. Test quadrant filter (if implemented)
8. Check responsive layout on mobile

### Playwright Testing
- Navigate to "My Tasks" tab
- Verify task cards render
- Test quadrant filter interactions
- Verify task counts
- Screenshot task list for documentation

## Development Commands

```bash
# Start all services
./init.sh start all

# Frontend only (if backend already running)
cd frontend
npm run dev

# Check database for tasks
docker exec -it context_postgres psql -U context -d context -c "SELECT COUNT(*) FROM tasks;"

# Git workflow
git add -A
git commit -m "feat: implement Phase 3 - task list view with AI analysis display"
```

## Where to Find Things

- **Existing Task API:** `backend/app/api/tasks.py` (line 155+)
- **Task model:** `backend/app/models/task.py`
- **Current tabs:** `frontend/app/page.tsx` (lines 30-50)
- **Existing components:** `frontend/components/TaskAnalyzer.tsx`, `frontend/components/LLMSettings.tsx`
- **shadcn/ui components:** Already installed (Card, Button, Badge, etc.)
- **Architecture docs:** `CLAUDE.md`
- **Plan document:** `docs/Plan1-2025-12-09.md`

## UI Design Guidelines

**Color Scheme (Dark Mode):**
- Q1 (Urgent & Important): Red (`bg-red-900/50 border-red-700`)
- Q2 (Not Urgent, Important): Green (`bg-green-900/50 border-green-700`)
- Q3 (Urgent, Not Important): Yellow (`bg-yellow-900/50 border-yellow-700`)
- Q4 (Neither): Blue (`bg-blue-900/50 border-blue-700`)

**Layout:** Card-based grid, responsive (1 col mobile, 2 cols tablet, 3 cols desktop)
**Typography:** Use existing Tailwind classes, maintain consistency with Phase 1/2

## How to Start

Please proceed with Phase 3 implementation in this order:

1. **Create TaskCard Component** - Individual task display with AI analysis
2. **Create TaskList Component** - Fetch and display all tasks
3. **Add "My Tasks" Tab** - Wire up to main page navigation
4. **Add Quadrant Filter** - Optional but recommended
5. **Test with Real Data** - Verify all 60 tasks display correctly
6. **Playwright E2E Tests** - Automated testing
7. **Update Documentation** - docs/Plan1-2025-12-09.md
8. **Git Commit** - With detailed message

Use **shadcn/ui components** for Cards, Badges, and Progress bars. Use **Playwright** for testing.

Good luck! 🚀
