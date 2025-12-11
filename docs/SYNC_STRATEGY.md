# TickTick Sync Strategy

## Overview

The sync strategy has been updated to give users **full control** over when data is synced to TickTick. All local changes (create, update, delete) are **NOT** automatically synced to the cloud.

## Current Behavior (Manual Sync Only)

### ❌ What Does NOT Auto-Sync

1. **Task Creation** (`POST /api/tasks`)
   - New tasks created locally via "New Task" button
   - Saved to local database only
   - NOT pushed to TickTick automatically

2. **Task Updates** (`PUT/PATCH /api/tasks/{id}`)
   - Edits in TaskDetailPopover (title, description, priority, dates, etc.)
   - Quadrant changes (drag & drop in matrix)
   - Manual priority overrides
   - All changes saved locally only

3. **Task Deletions** (`DELETE /api/tasks/{id}`)
   - Both soft delete and hard delete
   - Removed from local database only
   - NOT removed from TickTick automatically

4. **Suggestion Approvals** (`POST /api/tasks/{id}/suggestions/approve`)
   - Accepting AI suggestions
   - Updates local task only

### ✅ What DOES Sync

**Only the explicit "Sync with TickTick" button:**
- Located in sidebar (above "New Task")
- Calls `POST /api/tasks/sync`
- **Pull-only** sync (TickTick → Context)
- Downloads all tasks and projects from TickTick
- Updates local database with cloud data

**Direction**: One-way (Cloud → Local)

## Sync Button Behavior

```typescript
// In Sidebar.tsx
const handleSync = async () => {
  // 1. Call sync endpoint
  POST /api/tasks/sync?user_id=1

  // 2. Refresh all caches
  mutate('/api/tasks')
  mutate('/api/tasks/unsorted')
  mutate('/api/projects')

  // 3. Show last sync time
  setLastSyncTime(new Date())
}
```

**What happens on sync:**
1. Fetches all projects from TickTick → saves to `projects` table
2. Fetches all tasks from TickTick → saves to `tasks` table
3. For each new task → runs LLM analysis (if has description)
4. Links tasks to projects via `project_id`
5. Returns counts: `synced_count`, `analyzed_count`, `failed_count`

## User Experience

### Scenario 1: Create New Task
1. User clicks "New Task"
2. Fills out form, gets AI suggestions
3. Clicks "Create Task"
4. ✅ Task appears in local UI immediately
5. ❌ Task is NOT in TickTick yet
6. User must click "Sync" to push to cloud (future feature)

### Scenario 2: Edit Existing Task
1. User opens TaskDetailPopover
2. Changes title, priority, due date
3. Changes auto-save after 800ms
4. ✅ Changes visible in local UI
5. ❌ Changes NOT in TickTick yet
6. User must sync manually

### Scenario 3: Delete Task
1. User clicks "Delete" in TaskDetailPopover
2. Confirms deletion
3. ✅ Task removed from local UI
4. ❌ Task still exists in TickTick
5. User must sync to remove from cloud

## Future Enhancement: Auto-Sync Setting

**Proposed Implementation:**

### User Settings Model
```python
class UserSettings(Base):
    user_id = Column(Integer, ForeignKey("users.id"))
    auto_sync_enabled = Column(Boolean, default=False)
    auto_sync_interval_minutes = Column(Integer, default=5)
    sync_on_change = Column(Boolean, default=False)
    sync_on_llm_approval = Column(Boolean, default=False)
```

### Settings UI
```typescript
// In Settings page
<Switch
  checked={autoSyncEnabled}
  onCheckedChange={handleToggle}
  label="Enable Auto-Sync"
/>

<Select value={syncInterval}>
  <option value="1">Every 1 minute</option>
  <option value="5">Every 5 minutes</option>
  <option value="15">Every 15 minutes</option>
  <option value="30">Every 30 minutes</option>
</Select>

<Checkbox
  checked={syncOnChange}
  label="Sync immediately after local changes"
/>

<Checkbox
  checked={syncOnLLMApproval}
  label="Sync after approving AI suggestions"
/>
```

### Backend Implementation

**Option 1: Polling (Simple)**
```python
# In background worker (Celery/APScheduler)
@celery.task
async def auto_sync_users():
    users = await get_users_with_auto_sync_enabled()
    for user in users:
        if should_sync(user):  # Check interval
            await sync_user_tasks(user.id)
```

**Option 2: Event-Driven (Better)**
```python
# After task create/update/delete
if user.settings.sync_on_change:
    await queue_sync_job(user.id, delay_seconds=2)

# Debounce: Only sync once per 2 seconds even with rapid changes
```

## Conflict Resolution (Future)

When both local and cloud have changes:

### Strategy 1: Last-Write-Wins
- Compare `last_modified_at` timestamps
- Newer change overwrites older

### Strategy 2: Manual Override Protection
- Local manual overrides always win
- Cloud can update non-protected fields

### Strategy 3: Three-Way Merge
- Compare to `last_synced_at` snapshot
- Merge non-conflicting fields
- Prompt user for conflicts

## Benefits of Manual-Only Sync

1. **User Control**: No surprises, explicit actions
2. **Data Safety**: No accidental cloud deletions
3. **Offline-First**: Work without internet, sync later
4. **Bandwidth Efficient**: Only sync when needed
5. **Debugging Easier**: Clear when sync happens
6. **MVP Simplicity**: No background jobs needed

## Limitations

1. **No Real-Time Collaboration**: Changes don't auto-propagate
2. **Risk of Forgetting**: Users may forget to sync
3. **Divergence**: Local and cloud can get out of sync
4. **Manual Effort**: Extra click to sync

## Migration Path

### Phase 1 (Current): Manual Sync Only
- ✅ Pull from TickTick via sync button
- ❌ No automatic push to TickTick

### Phase 2 (Next): Add Push Sync
- ✅ Sync button does bi-directional sync
- Push local changes → TickTick
- Pull TickTick changes → local
- Conflict resolution strategy

### Phase 3 (Future): Optional Auto-Sync
- Add user settings for auto-sync
- Background sync every N minutes
- Sync on local changes (debounced)
- Sync on LLM approval

## Code Changes Summary

### Backend (tasks.py)

**Before:**
```python
# Task creation auto-synced to TickTick
new_task = Task(...)
db.add(new_task)
ticktick_service.create_task(...)  # ❌ Auto-sync
```

**After:**
```python
# Task creation is local only
new_task = Task(...)
db.add(new_task)
# NOTE: NOT synced to TickTick automatically
```

**Same pattern for:**
- `update_task()` - removed TickTick sync code
- `delete_task()` - removed TickTick sync code

### Sync Endpoint

**Purpose**: Pull tasks FROM TickTick (one-way)

```python
@router.post("/sync")
async def sync_ticktick_tasks(user_id: int):
    # 1. Sync projects
    projects = await ticktick_service.sync_projects(db)

    # 2. Get all tasks from TickTick
    ticktick_tasks = await ticktick_service.get_tasks()

    # 3. For each task:
    #    - Save to local DB
    #    - Run LLM analysis
    #    - Link to project

    return {"synced_count": len(ticktick_tasks)}
```

## Testing Checklist

### Manual Sync
- [ ] Click "Sync" button → Shows loading state
- [ ] Tasks from TickTick → Appear in local UI
- [ ] New TickTick task → Syncs on next refresh
- [ ] Last sync time → Displays correctly
- [ ] Sync error → Shows error message

### Task Create (No Auto-Sync)
- [ ] Create task → Saves locally
- [ ] Check TickTick web → Task NOT there
- [ ] Click sync → Still not pushed (pull-only)
- [ ] Task stays local only

### Task Update (No Auto-Sync)
- [ ] Edit title → Saves locally
- [ ] Check TickTick web → Title unchanged
- [ ] Edit priority → NOT synced
- [ ] Approve AI suggestion → NOT synced

### Task Delete (No Auto-Sync)
- [ ] Delete local task → Removed from UI
- [ ] Check TickTick web → Task still exists
- [ ] Sync button → Brings task back (pull from cloud)

## Related Files

- `backend/app/api/tasks.py` - All CRUD endpoints
- `frontend/components/Sidebar.tsx` - Sync button UI
- `QUICK_ADD_FEATURE.md` - Quick add documentation

## Questions & Answers

**Q: How do I push local changes to TickTick?**
A: Not implemented yet. Phase 2 will add bi-directional sync.

**Q: What if I forget to sync?**
A: Local changes stay local. Next sync will pull cloud data (may overwrite local changes).

**Q: Can I auto-sync every 5 minutes?**
A: Not yet. Planned for Phase 3 as optional user setting.

**Q: What happens if I edit the same task in both places?**
A: Next sync will overwrite local with cloud data (pull-only). Phase 2 will add conflict resolution.

**Q: How do I know if a task is synced?**
A: Check `ticktick_task_id` field. If null, it's local-only.

---

**Status**: ✅ Implemented
**Version**: MVP (Manual Sync Only)
**Next**: Add push sync (bi-directional)
**Author**: Claude Code
**Date**: 2025-12-11
