# TickTick Metadata Enhancement Plan

## Goal
Display and allow editing of ALL TickTick metadata fields in the UI, with LLM assistance for filling them out.

## Current State Audit

### Database Fields Available (from Task model)
✅ **Already in DB:**
1. `ticktick_priority` (0/1/3/5)
2. `start_date` (DateTime)
3. `due_date` (DateTime)
4. `all_day` (Boolean)
5. `reminder_time` (DateTime)
6. `repeat_flag` (String - TickTick format)
7. `project_name` (String)
8. `project_id` (FK to projects table)
9. `parent_task_id` (String - for subtasks)
10. `ticktick_tags` (JSONB array)
11. `time_estimate` (Integer - minutes)
12. `focus_time` (Integer - minutes)
13. `sort_order` (Integer)
14. `column_id` (String - for Kanban columns)

### UI Components to Enhance

#### 1. TaskCard (Matrix View)
**Currently Shows:**
- Title
- Description (truncated)
- Urgency/Importance scores
- Quadrant badge

**Missing:**
- Project badge
- Priority badge
- Due date badge
- Tags
- Subtask indicator
- Repeat indicator
- Time estimate

#### 2. TaskDetailPopover
**Currently Shows:**
- Title (editable)
- Description (editable with markdown)
- Due date picker
- Start date picker
- Priority selector
- Project badge (read-only)
- Tags (read-only)

**Missing:**
- Reminder picker
- Repeat pattern selector
- Time estimate input
- Focus time input
- Subtask list/creator
- All-day toggle
- Project selector (currently read-only)
- Tag editor (currently read-only)

#### 3. QuickAddTaskModal
**Currently Shows:**
- Title input
- Description textarea
- Due date picker
- Priority selector

**Missing:**
- Project selector
- Start date picker
- Tags input
- Repeat pattern
- Reminder time
- Time estimate
- Parent task selector (for subtasks)

#### 4. ListView (List Page)
**Currently Shows:**
- Checkbox
- Title
- Project badge
- Priority badge
- Due date badge
- Quadrant badge
- Tags

**Good coverage!** Just missing:
- Repeat indicator
- Subtask indicator
- Time estimate

## Implementation Plan

### Phase 1: Enhanced Display Components

#### A. Create Reusable Components
```
frontend/components/metadata/
├── RepeatBadge.tsx          # Shows repeat pattern icon + text
├── SubtaskIndicator.tsx     # Shows "📋 3/5 completed"
├── TimeEstimateBadge.tsx    # Shows "⏱️ 2h 30m"
├── ReminderBadge.tsx        # Shows "🔔 Tomorrow 9AM"
└── ProjectSelector.tsx      # Dropdown with all projects
```

#### B. Update TaskCard.tsx
Add badges at bottom:
```tsx
<div className="flex flex-wrap gap-1 mt-2">
  {project && <Badge>{project}</Badge>}
  {priority > 0 && <PriorityBadge value={priority} />}
  {dueDate && <DateBadge date={dueDate} />}
  {repeatFlag && <RepeatBadge pattern={repeatFlag} />}
  {hasSubtasks && <SubtaskIndicator completed={2} total={5} />}
  {timeEstimate && <TimeEstimateBadge minutes={timeEstimate} />}
  {tags?.map(tag => <Badge key={tag}>{tag}</Badge>)}
</div>
```

#### C. Update TaskDetailPopover.tsx
Add new fields in metadata grid:
```tsx
<MetadataRow icon="🗂️" label="Project">
  <ProjectSelector value={projectId} onChange={...} />
</MetadataRow>

<MetadataRow icon="🔔" label="Reminder">
  <DateTimePicker value={reminderTime} onChange={...} />
</MetadataRow>

<MetadataRow icon="🔁" label="Repeat">
  <RepeatPatternSelect value={repeatFlag} onChange={...} />
</MetadataRow>

<MetadataRow icon="⏱️" label="Time Estimate">
  <TimeEstimateInput value={timeEstimate} onChange={...} />
</MetadataRow>

<MetadataRow icon="🏷️" label="Tags">
  <TagsInput value={tags} onChange={...} />
</MetadataRow>

<MetadataRow icon="☀️" label="All Day">
  <Switch checked={allDay} onCheckedChange={...} />
</MetadataRow>
```

Add subtask section:
```tsx
<div className="border-t pt-4">
  <h3>📋 Subtasks</h3>
  <SubtaskList taskId={task.id} />
  <Button onClick={addSubtask}>+ Add Subtask</Button>
</div>
```

#### D. Update QuickAddTaskModal.tsx
Add more fields below existing ones:
```tsx
// After due date
<MetadataRow icon="🗂️" label="Project">
  <ProjectSelector />
</MetadataRow>

<MetadataRow icon="📅" label="Start Date">
  <DatePicker />
</MetadataRow>

<MetadataRow icon="🏷️" label="Tags">
  <TagsInput placeholder="Add tags..." />
</MetadataRow>

// Expandable "More Options" section
<Collapsible>
  <CollapsibleTrigger>⚙️ More Options</CollapsibleTrigger>
  <CollapsibleContent>
    <MetadataRow icon="🔁" label="Repeat">
      <RepeatPatternSelect />
    </MetadataRow>
    <MetadataRow icon="⏱️" label="Time Estimate">
      <TimeEstimateInput />
    </MetadataRow>
  </CollapsibleContent>
</Collapsible>
```

### Phase 2: LLM Enhancement

#### A. Update LLM Prompt
Enhance `task_analysis_suggestions_v1.txt` to suggest:

```text
## Additional Suggestions

The LLM should also suggest:

1. **Project Assignment**
   - Analyze task title/description for project keywords
   - Suggest matching project from user's project list
   - Example: "Review Q4 financials" → Project: "Finance"

2. **Tags**
   - Extract relevant tags from context
   - Example: "Urgent bug in production" → Tags: ["bug", "urgent", "production"]

3. **Time Estimate**
   - Estimate effort in minutes based on task complexity
   - Example: "Quick code review" → 30 minutes
   - Example: "Implement auth system" → 480 minutes (8 hours)

4. **Repeat Pattern**
   - Detect recurring tasks
   - Example: "Weekly team standup" → RRULE:FREQ=WEEKLY;BYDAY=MO
   - Example: "Monthly report" → RRULE:FREQ=MONTHLY

5. **Subtask Breakdown** (if complex)
   - For large tasks, suggest breaking into subtasks
   - Example: "Launch product" → ["Design UI", "Implement backend", "Write tests", "Deploy"]

Output format:
{
  "analysis": { ... },
  "suggestions": [
    {
      "type": "project",
      "suggested": "Finance",
      "reason": "Task involves Q4 financial review"
    },
    {
      "type": "tags",
      "suggested": ["quarterly", "review", "finance"],
      "reason": "Common tags for financial reviews"
    },
    {
      "type": "time_estimate",
      "suggested": 120,
      "reason": "Typical review takes 2 hours"
    },
    {
      "type": "repeat",
      "suggested": "RRULE:FREQ=MONTHLY;BYMONTHDAY=1",
      "reason": "Monthly recurring task"
    }
  ]
}
```

#### B. Update Backend Suggestion Types
Add new suggestion types in `task_suggestion.py`:
- `project`
- `tags`
- `time_estimate`
- `repeat`
- `subtasks`

#### C. Update Frontend SuggestionPanel
Display new suggestion types:
```tsx
{suggestion.type === 'project' && (
  <div>
    Suggested Project: <Badge>{suggestion.suggested}</Badge>
  </div>
)}

{suggestion.type === 'tags' && (
  <div>
    Suggested Tags: {suggestion.suggested.map(tag => <Badge>{tag}</Badge>)}
  </div>
)}

{suggestion.type === 'time_estimate' && (
  <div>
    Estimated Time: <Badge>{formatMinutes(suggestion.suggested)}</Badge>
  </div>
)}
```

### Phase 3: TickTick Sync Enhancement

#### A. Ensure Pull Sync Captures All Fields
Update `ticktick_service.get_tasks()` to extract:
```python
task_data = {
    # ... existing fields ...
    "repeat_flag": task_json.get("repeatFlag"),
    "reminder_time": parse_datetime(task_json.get("reminders", [])[0]) if task_json.get("reminders") else None,
    "time_estimate": calculate_time_estimate(task_json.get("pomodoroSummaries")),
    "focus_time": task_json.get("focusTime"),
    # ... etc
}
```

#### B. Add Push Sync for All Fields (Phase 2 future)
When implemented, push all fields:
```python
ticktick_payload = {
    "title": task.title,
    "content": task.description,
    "priority": task.ticktick_priority,
    "dueDate": task.due_date,
    "startDate": task.start_date,
    "tags": task.ticktick_tags,
    "repeatFlag": task.repeat_flag,
    "reminders": [task.reminder_time] if task.reminder_time else [],
    # ... etc
}
```

## UI/UX Considerations

### Repeat Pattern UI
**Options:**
- None
- Daily
- Weekly (with day selector)
- Monthly (by date or by day)
- Yearly
- Custom (RRULE editor)

**Display:**
- Badge: "🔁 Weekly on Mon"
- Badge: "🔁 Monthly on 1st"
- Badge: "🔁 Every 2 days"

### Subtasks UI
**Display in Card:**
- Compact: "📋 3/5"
- Expanded: Progress bar with count

**Display in Popover:**
- Full list with checkboxes
- Inline add new subtask
- Reorder with drag & drop

### Time Estimate UI
**Input:**
- Duration picker: "2h 30m"
- Or simple number with unit selector (hours/minutes)

**Display:**
- Badge: "⏱️ 2h 30m"
- Show on card if set

### Project Selector UI
**Dropdown:**
- List all projects with colors
- Search/filter
- Create new project inline

## Priority Order

### Must Have (MVP)
1. ✅ Project display (already done)
2. ✅ Priority display (already done)
3. ✅ Tags display (already done)
4. 🔲 Project selector (editable)
5. 🔲 Tags input (editable)
6. 🔲 Time estimate
7. 🔲 Start date (editable)

### Should Have
8. 🔲 Repeat pattern (display + edit)
9. 🔲 Reminder time
10. 🔲 Subtask indicator
11. 🔲 All-day toggle
12. 🔲 LLM suggestions for new fields

### Nice to Have
13. 🔲 Subtask CRUD
14. 🔲 Focus time
15. 🔲 Column/board assignment
16. 🔲 Advanced repeat patterns

## Next Steps

1. Create reusable metadata components
2. Update TaskDetailPopover with all fields
3. Update QuickAddModal with key fields
4. Enhance LLM prompt for new suggestions
5. Test with real TickTick data
6. Update sync to push all fields (future)

## Files to Create/Modify

### Create:
- `frontend/components/metadata/RepeatBadge.tsx`
- `frontend/components/metadata/SubtaskIndicator.tsx`
- `frontend/components/metadata/TimeEstimateBadge.tsx`
- `frontend/components/metadata/ProjectSelector.tsx`
- `frontend/components/metadata/TagsInput.tsx`
- `frontend/components/metadata/RepeatPatternSelect.tsx`
- `frontend/components/metadata/TimeEstimateInput.tsx`

### Modify:
- `frontend/components/TaskCard.tsx` - Add badges
- `frontend/components/TaskDetailPopover.tsx` - Add fields
- `frontend/components/QuickAddTaskModal.tsx` - Add fields
- `backend/app/prompts/task_analysis_suggestions_v1.txt` - Enhanced prompt
- `backend/app/models/task_suggestion.py` - New suggestion types

---

**Estimated Effort:** 8-12 hours
**Complexity:** Medium-High (many small components)
**Impact:** High (much richer task management)
