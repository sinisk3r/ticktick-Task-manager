# Unsorted Task List Feature Specification

**Created:** 2025-12-11
**Priority:** High (User Requested)
**Status:** Planning

---

## Overview

Add an "Unsorted" list view that serves as a staging area for tasks before they are organized into the Eisenhower Matrix. This improves the user workflow by:
1. Allowing tasks to exist without immediate categorization
2. Providing a simple list view for quick task entry
3. Enabling manual or AI-assisted sorting at the user's convenience
4. Syncing new tasks created in Context to TickTick

---

## User Workflow

### Current Workflow (Problem)
1. User syncs tasks from TickTick
2. All tasks appear in matrix immediately (forced categorization)
3. Tasks without analysis are hard to locate
4. No clear "inbox" for new tasks

### New Workflow (Solution)
1. User syncs tasks from TickTick → appear in "Unsorted" list
2. User creates new task in Context → appears in "Unsorted" + syncs to TickTick
3. User can:
   - **Manually drag** task from Unsorted → Matrix quadrant
   - **Click "Analyze"** → AI suggests quadrant → User approves → Task moves to matrix
   - **Batch analyze** multiple unsorted tasks at once
4. Organized tasks appear in Eisenhower Matrix
5. Unsorted list shows count: "Unsorted (12)"

---

## Technical Requirements

### 1. Database Schema Changes

**Task Model - Add field:**
```python
is_sorted = Column(Boolean, default=False)  # False = Unsorted, True = In Matrix
```

**Migration:**
- Add `is_sorted` column to `tasks` table (default: False)
- Create index on (user_id, is_sorted) for efficient queries
- Backfill existing tasks: Set `is_sorted = True` if `eisenhower_quadrant IS NOT NULL`

---

### 2. Backend API Changes

#### New Endpoints

**GET /api/tasks/unsorted**
```python
@router.get("/unsorted")
async def get_unsorted_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all unsorted tasks for current user"""
    stmt = select(Task).where(
        Task.user_id == current_user.id,
        Task.is_sorted == False,
        Task.status != "completed"
    ).order_by(Task.created_at.desc())

    result = await db.execute(stmt)
    tasks = result.scalars().all()
    return tasks
```

**POST /api/tasks/{id}/sort**
```python
@router.post("/{task_id}/sort")
async def sort_task(
    task_id: int,
    sort_data: TaskSortRequest,  # { quadrant: "Q1" }
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually sort a task into a quadrant.
    Marks task as sorted and assigns quadrant.
    """
    task = await get_task_or_404(task_id, current_user.id, db)

    task.eisenhower_quadrant = sort_data.quadrant
    task.is_sorted = True
    task.manual_quadrant_override = True  # User explicitly chose this

    await db.commit()
    return task
```

**POST /api/tasks/sort/batch**
```python
@router.post("/sort/batch")
async def batch_sort_tasks(
    batch_data: BatchSortRequest,  # { task_ids: [1,2,3], quadrant: "Q2" }
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch sort multiple tasks into a quadrant"""
    tasks = await get_tasks_by_ids(batch_data.task_ids, current_user.id, db)

    for task in tasks:
        task.eisenhower_quadrant = batch_data.quadrant
        task.is_sorted = True
        task.manual_quadrant_override = True

    await db.commit()
    return {"sorted_count": len(tasks)}
```

#### Modified Endpoints

**POST /api/tasks (Task Creation)**
```python
@router.post("")
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create task locally AND push to TickTick"""

    # Create local task (unsorted by default)
    new_task = Task(
        user_id=current_user.id,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        is_sorted=False,  # Start in unsorted list
        ticktick_priority=task_data.ticktick_priority or 0,
        ticktick_tags=task_data.tags or []
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    # Push to TickTick if user is connected
    if current_user.ticktick_access_token:
        try:
            ticktick_service = TickTickService(current_user)
            ticktick_task = await ticktick_service.create_task(
                {
                    "title": new_task.title,
                    "description": new_task.description,
                    "due_date": new_task.due_date,
                    "ticktick_priority": new_task.ticktick_priority,
                    "ticktick_tags": new_task.ticktick_tags,
                    "ticktick_project_id": task_data.project_id
                },
                db
            )

            # Store TickTick ID for future sync
            new_task.ticktick_task_id = ticktick_task.get("id")
            new_task.ticktick_project_id = ticktick_task.get("projectId")
            new_task.last_synced_at = datetime.utcnow()
            await db.commit()

            logger.info(f"Created task {new_task.id} and synced to TickTick")
        except Exception as e:
            logger.error(f"Failed to sync new task to TickTick: {e}")
            # Don't fail local creation if TickTick sync fails

    return new_task
```

**POST /api/tasks/sync (TickTick Sync)**
```python
# Modification: Don't auto-categorize synced tasks
# Set is_sorted = False so they appear in Unsorted list

for task_data in tasks_from_ticktick:
    new_task = Task(
        user_id=current_user.id,
        is_sorted=False,  # New tasks start unsorted
        **task_data
    )
```

**POST /api/tasks/{id}/suggestions/approve**
```python
# Modification: When user approves quadrant suggestion, mark as sorted

if "quadrant" in approved_suggestion_types:
    task.eisenhower_quadrant = suggestion.suggested_quadrant
    task.is_sorted = True  # Move out of unsorted list
```

---

### 3. Frontend Changes

#### New Components

**`UnsortedList.tsx`**
```tsx
export function UnsortedList() {
  const { data: tasks, isLoading } = useSWR('/api/tasks/unsorted', fetcher)

  return (
    <div className="unsorted-container">
      <div className="header">
        <h2>Unsorted Tasks ({tasks?.length || 0})</h2>
        <button onClick={analyzeBatch}>⚡ Analyze All</button>
      </div>

      <div className="task-list">
        {tasks?.map(task => (
          <UnsortedTaskCard
            key={task.id}
            task={task}
            onSort={handleSort}
            onAnalyze={handleAnalyze}
          />
        ))}
      </div>
    </div>
  )
}
```

**`UnsortedTaskCard.tsx`**
```tsx
export function UnsortedTaskCard({ task, onSort, onAnalyze }) {
  const [showQuadrantPicker, setShowQuadrantPicker] = useState(false)

  return (
    <div className="unsorted-task-card">
      <div className="task-info">
        <h3>{task.title}</h3>
        <p>{task.description}</p>
        {task.ticktick_priority > 0 && (
          <Badge>Priority: {priorityDisplay(task.ticktick_priority)}</Badge>
        )}
      </div>

      <div className="actions">
        <button onClick={() => onAnalyze(task.id)}>
          ⚡ Analyze
        </button>

        <button onClick={() => setShowQuadrantPicker(true)}>
          📊 Sort Manually
        </button>

        {showQuadrantPicker && (
          <QuadrantPicker
            onSelect={(quadrant) => onSort(task.id, quadrant)}
            onCancel={() => setShowQuadrantPicker(false)}
          />
        )}
      </div>
    </div>
  )
}
```

**`QuadrantPicker.tsx`**
```tsx
export function QuadrantPicker({ onSelect, onCancel }) {
  const quadrants = [
    { id: 'Q1', label: 'Q1: Urgent & Important', color: 'red' },
    { id: 'Q2', label: 'Q2: Important, Not Urgent', color: 'blue' },
    { id: 'Q3', label: 'Q3: Urgent, Not Important', color: 'yellow' },
    { id: 'Q4', label: 'Q4: Neither', color: 'gray' },
  ]

  return (
    <div className="quadrant-picker">
      {quadrants.map(q => (
        <button
          key={q.id}
          onClick={() => onSelect(q.id)}
          className={`quadrant-option ${q.color}`}
        >
          {q.label}
        </button>
      ))}
      <button onClick={onCancel}>Cancel</button>
    </div>
  )
}
```

**`SimpleTaskView.tsx`** (New page)
```tsx
export function SimpleTaskView() {
  const [newTask, setNewTask] = useState({ title: '', description: '' })
  const { data: unsorted } = useSWR('/api/tasks/unsorted', fetcher)

  const handleCreateTask = async () => {
    await api.createTask(newTask)
    setNewTask({ title: '', description: '' })
    mutate('/api/tasks/unsorted')  // Refresh list
  }

  return (
    <div className="simple-task-view">
      <div className="create-section">
        <h2>Quick Add Task</h2>
        <input
          placeholder="Task title..."
          value={newTask.title}
          onChange={(e) => setNewTask({...newTask, title: e.target.value})}
        />
        <textarea
          placeholder="Description (optional)..."
          value={newTask.description}
          onChange={(e) => setNewTask({...newTask, description: e.target.value})}
        />
        <button onClick={handleCreateTask}>
          Add Task (syncs to TickTick)
        </button>
      </div>

      <UnsortedList />
    </div>
  )
}
```

#### Modified Components

**`Sidebar.tsx`** - Add navigation items:
```tsx
<SidebarItem icon="📥" label="Unsorted" count={unsortedCount} href="/unsorted" />
<SidebarItem icon="📝" label="Simple View" href="/simple" />
<SidebarItem icon="📊" label="Matrix View" href="/" />
```

**`EisenhowerMatrix.tsx`** - Accept drag from Unsorted:
```tsx
// Allow dropping tasks from unsorted list into quadrants
const handleDropFromUnsorted = async (taskId, quadrant) => {
  await api.sortTask(taskId, quadrant)
  mutate('/api/tasks')  // Refresh matrix
  mutate('/api/tasks/unsorted')  // Refresh unsorted
}
```

#### New Routes

- `/unsorted` → UnsortedList component
- `/simple` → SimpleTaskView component
- `/` → EisenhowerMatrix (existing)

---

### 4. API Client Updates (`lib/api.ts`)

```typescript
export const api = {
  // Existing...

  // New methods
  getUnsortedTasks: () => fetcher('/api/tasks/unsorted'),

  sortTask: (taskId: number, quadrant: string) =>
    fetch(`/api/tasks/${taskId}/sort`, {
      method: 'POST',
      body: JSON.stringify({ quadrant })
    }),

  batchSortTasks: (taskIds: number[], quadrant: string) =>
    fetch('/api/tasks/sort/batch', {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds, quadrant })
    }),

  createTask: (taskData: TaskCreate) =>
    fetch('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(taskData)
    })
}
```

---

## UX Design

### Unsorted List View
```
┌─────────────────────────────────────────────┐
│ Unsorted Tasks (12)        [⚡ Analyze All]  │
├─────────────────────────────────────────────┤
│                                             │
│ ┌─────────────────────────────────────┐    │
│ │ Fix login bug                       │    │
│ │ Description: Users can't log in...  │    │
│ │ Priority: High (5)                  │    │
│ │                                     │    │
│ │ [⚡ Analyze]  [📊 Sort Manually]    │    │
│ └─────────────────────────────────────┘    │
│                                             │
│ ┌─────────────────────────────────────┐    │
│ │ Review Q4 metrics                   │    │
│ │ Work - Q4 Planning                  │    │
│ │                                     │    │
│ │ [⚡ Analyze]  [📊 Sort Manually]    │    │
│ └─────────────────────────────────────┘    │
│                                             │
└─────────────────────────────────────────────┘
```

### Simple Task View
```
┌─────────────────────────────────────────────┐
│ Quick Add Task                              │
├─────────────────────────────────────────────┤
│ ┌─────────────────────────────────────┐    │
│ │ Task title...                       │    │
│ └─────────────────────────────────────┘    │
│                                             │
│ ┌─────────────────────────────────────┐    │
│ │ Description (optional)...           │    │
│ │                                     │    │
│ └─────────────────────────────────────┘    │
│                                             │
│ [Add Task (syncs to TickTick)]             │
│                                             │
├─────────────────────────────────────────────┤
│ Unsorted Tasks (12)                         │
│ (Shows UnsortedList component here)         │
└─────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Database & Backend (2 tasks)
1. ✅ Add `is_sorted` field to Task model
2. ✅ Create migration and backfill existing data
3. ✅ Add unsorted endpoints (GET /unsorted, POST /sort, POST /sort/batch)
4. ✅ Modify POST /api/tasks to push to TickTick

### Phase 2: Frontend Components (3 tasks)
1. ✅ Create UnsortedList component
2. ✅ Create UnsortedTaskCard component
3. ✅ Create QuadrantPicker component
4. ✅ Create SimpleTaskView page
5. ✅ Update Sidebar with new navigation

### Phase 3: Integration (2 tasks)
1. ✅ Connect unsorted list to analyze workflow
2. ✅ Enable drag-and-drop from unsorted to matrix
3. ✅ Update API client with new methods

### Phase 4: Testing (1 task)
1. ✅ Test create task → TickTick sync
2. ✅ Test manual sort → matrix placement
3. ✅ Test AI analyze → approval → matrix placement

**Total: 8 implementation tasks**

---

## Success Criteria

✅ Tasks synced from TickTick appear in Unsorted list by default
✅ New tasks created in Context sync to TickTick immediately
✅ Users can manually drag tasks from Unsorted to Matrix quadrants
✅ Users can click "Analyze" on unsorted task → get suggestions → approve → task moves to matrix
✅ Unsorted count shows in sidebar
✅ Simple view allows quick task entry with TickTick sync
✅ No breaking changes to existing matrix functionality

---

## Benefits

1. **Clearer Workflow:** Tasks have a clear starting point (unsorted) and destination (matrix)
2. **User Control:** Users decide when to categorize tasks
3. **Faster Entry:** Simple view allows quick task creation
4. **Better Sync:** New tasks immediately sync to TickTick
5. **Reduced Friction:** No forced categorization on import
6. **Flexibility:** Manual or AI-assisted sorting

---

## Migration Strategy

**Existing Users:**
- All existing tasks with `eisenhower_quadrant` → set `is_sorted = True`
- Tasks without quadrant → set `is_sorted = False` (appear in unsorted)

**New Users:**
- All synced tasks start with `is_sorted = False`
- User sorts them gradually

---

Last Updated: 2025-12-11 by Main Agent
