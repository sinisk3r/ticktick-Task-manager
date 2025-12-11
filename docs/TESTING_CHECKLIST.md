# TickTick-Inspired UI - Testing Checklist

## Pre-Testing Setup

1. ✅ Build completed successfully (`npm run build`)
2. ⬜ Start backend server (`cd backend && uvicorn app.main:app --reload --port 8000`)
3. ⬜ Start frontend dev server (`cd frontend && npm run dev`)
4. ⬜ Ensure at least a few tasks exist in the system

## Feature Testing

### TaskDetailPopover Component

#### Opening the Popover
- [ ] Click on any task card in the Matrix View → Opens TaskDetailPopover
- [ ] Click on task title in Unsorted View → Opens TaskDetailPopover
- [ ] Click on task in List View → Opens TaskDetailPopover
- [ ] Click outside or press ESC → Closes popover
- [ ] Click X button → Closes popover

#### Title Editing
- [ ] Click in title field and edit text
- [ ] Wait 800ms → Check network tab for PATCH request
- [ ] Verify title updates in task list after closing
- [ ] Leave title empty → Should still save (or show validation)

#### Checkbox (Completion)
- [ ] Click completion checkbox → Immediately sends PATCH request
- [ ] Task status changes from "active" to "completed" or vice versa
- [ ] Verify task updates in list view

#### Due Date Picker
- [ ] Click "Due Date" calendar button → Opens calendar popover
- [ ] Select a date → Immediately saves (PATCH request)
- [ ] Date displays in "PPP" format (e.g., "December 11, 2025")
- [ ] Click X icon on selected date → Clears due date
- [ ] Verify date appears as badge in list view

#### Start Date Picker
- [ ] Same tests as Due Date Picker
- [ ] Verify start date saved independently from due date

#### Priority Selector
- [ ] Click Priority dropdown → Shows None/Low/Medium/High options
- [ ] Select "High" (5) → Immediately saves
- [ ] Verify priority badge appears in list view
- [ ] Color-coding: None=gray, Low=blue, Medium=yellow, High=red

#### Project Display
- [ ] If task has project_name → Shows project badge
- [ ] If no project → No badge shown
- [ ] Badge should be read-only (no editing yet)

#### Tags Display
- [ ] If task has ticktick_tags → Shows tag badges
- [ ] If no tags → Section hidden
- [ ] Tags should be read-only (no editing yet)

#### Description (Markdown Editor)
- [ ] Type in description textarea
- [ ] Wait 800ms → Auto-saves
- [ ] Click "Preview" button → Shows rendered markdown
- [ ] Test markdown features:
  - [ ] `# Header 1`, `## Header 2`, `### Header 3`
  - [ ] `**bold text**` → Shows bold
  - [ ] `*italic text*` → Shows italic
  - [ ] `` `code` `` → Shows inline code with bg-muted
  - [ ] `- List item` → Shows bullet list
- [ ] Click "Edit" button → Returns to textarea
- [ ] Long text → Expands textarea automatically

#### AI Analysis Section
- [ ] Shows quadrant badge (Q1/Q2/Q3/Q4)
- [ ] If manual override → Shows "Manual Override" badge
- [ ] Shows urgency score (e.g., "Urgency: 8/10")
- [ ] Shows importance score (e.g., "Importance: 7/10")
- [ ] Shows AI reasoning text
- [ ] Section only appears if AI analysis exists

#### Delete Functionality
- [ ] Click "Delete" button → Shows browser confirmation
- [ ] Click "Cancel" → Nothing happens
- [ ] Click "OK" → Sends DELETE request
- [ ] Task removed from list view
- [ ] Popover closes automatically

#### Error Handling
- [ ] Disconnect from backend → Edit field → Shows error alert
- [ ] Error alert displays with AlertCircle icon
- [ ] Error message is user-friendly

#### Saving Indicator
- [ ] While saving → Shows "Saving..." text in footer
- [ ] After save complete → "Saving..." disappears

### ListView Page

#### Toolbar - Search
- [ ] Type in search box → Filters tasks in real-time
- [ ] Search by task title → Shows matching tasks
- [ ] Search by description → Shows matching tasks
- [ ] Search by project name → Shows matching tasks
- [ ] Clear search → Shows all tasks again

#### Toolbar - Sort
- [ ] Select "Sort: Due Date" → Tasks ordered by earliest due date first
- [ ] Tasks with no due date → Appear at bottom
- [ ] Select "Sort: Priority" → Tasks ordered High → Medium → Low → None
- [ ] Select "Sort: Created" → Newest tasks first
- [ ] Select "Sort: Title" → Alphabetical order (A-Z)

#### Toolbar - Filter
- [ ] Select "All Tasks" → Shows all tasks
- [ ] Select "Today" → Shows only tasks due today
- [ ] Select "This Week" → Shows tasks due within this week
- [ ] Select "Overdue" → Shows tasks with past due dates
- [ ] Select "Quadrant 1" → Shows only Q1 tasks
- [ ] Repeat for Q2, Q3, Q4

#### Toolbar - Group
- [ ] Select "No Grouping" → All tasks in one section
- [ ] Select "Group by Project" → Tasks grouped by project_name
  - [ ] Tasks without projects → "No Project" group
- [ ] Select "Group by Priority" → Groups: High, Medium, Low, None
  - [ ] Empty groups → Not shown
- [ ] Select "Group by Due Date" → Groups: Overdue, Today, This Week, Later, No Due Date
  - [ ] Empty groups → Not shown
- [ ] Select "Group by Quadrant" → Groups: Q1, Q2, Q3, Q4
  - [ ] Empty groups → Not shown

#### Task List Display
- [ ] Each task shows:
  - [ ] Checkbox (checked if completed)
  - [ ] Task title (truncated if long)
  - [ ] Project badge (if exists)
  - [ ] Priority badge (if > 0)
  - [ ] Due date badge (formatted: "Today", "Mon", "Dec 11")
  - [ ] Overdue badge → Red/destructive variant
  - [ ] Quadrant badge
  - [ ] Tag badges
- [ ] Hover over task → Border changes to primary color
- [ ] Hover over task → Star button appears (opacity 0 → 100)
- [ ] Group headers show task count (e.g., "Q1 (5)")

#### Task Interaction
- [ ] Click anywhere on task row → Opens TaskDetailPopover
- [ ] Edit task in popover → Close → Task updates in list
- [ ] Delete task in popover → Task disappears from list

#### Data Refresh
- [ ] Tasks auto-refresh every 10 seconds (via SWR)
- [ ] Edit task → Optimistic update (immediate UI change)
- [ ] Create task in another tab → Appears after 10s refresh

#### Empty States
- [ ] No tasks in system → Shows "No tasks found" message
- [ ] Filter returns no results → Shows "No tasks found" message
- [ ] Group has no tasks → Group not displayed

#### Add Task Button
- [ ] "Add Task" button visible in toolbar
- [ ] Currently placeholder (no functionality yet)

### Updated Components

#### TaskCard (Matrix View)
- [ ] Click on card → Opens TaskDetailPopover
- [ ] Edit task → Close → Card updates (quadrant, scores, etc.)
- [ ] Delete task → Card disappears from matrix
- [ ] Drag-and-drop still works (if implemented)
- [ ] Click "Read more" button → Doesn't open popover (stopPropagation)

#### UnsortedTaskCard
- [ ] Click on task title → Opens TaskDetailPopover
- [ ] Edit task → Close → Card updates
- [ ] Delete task → Card disappears
- [ ] "Analyze" button still works
- [ ] "Sort Manually" button still works
- [ ] Uses theme colors (bg-card, text-foreground, border-border)

#### Sidebar Navigation
- [ ] "List View" option visible
- [ ] Positioned between "My Tasks" and "Unsorted"
- [ ] Click "List View" → Navigates to /list
- [ ] Active state → Highlighted with bg-sidebar-primary
- [ ] ListTodo icon displays

### Theme Compatibility

#### Light Mode
- [ ] Background: Light gray (#F5F7FA)
- [ ] Cards: White (#FFFFFF)
- [ ] Primary: Blue (#2E6794)
- [ ] Accent: Teal (#4DB6AC)
- [ ] Text readable and contrasts well
- [ ] All components use theme colors

#### Dark Mode
- [ ] Background: Dark navy (#0B1121)
- [ ] Cards: Darker navy (#151E2E)
- [ ] Primary: Teal (#4DB6AC)
- [ ] Accent: Blue (#2E6794)
- [ ] Text readable and contrasts well
- [ ] All components use theme colors
- [ ] Toggle theme → All components update

### Responsive Design

#### Desktop (> 768px)
- [ ] TaskDetailPopover → Dialog (max-w-2xl)
- [ ] List View → Full toolbar visible
- [ ] Filters/sorts in row layout
- [ ] Task cards show all metadata

#### Mobile (< 768px)
- [ ] TaskDetailPopover → Full screen dialog
- [ ] List View → Stacked toolbar
- [ ] Filters/sorts wrap to new lines
- [ ] Task cards remain readable
- [ ] Sidebar slides in from left with overlay

### Performance

#### Large Task Lists (100+ tasks)
- [ ] List View renders without lag
- [ ] Filtering/sorting is responsive
- [ ] Grouping calculates quickly
- [ ] Scrolling is smooth
- [ ] useMemo prevents unnecessary re-renders

#### Network Efficiency
- [ ] Debounced auto-save (text fields wait 800ms)
- [ ] Immediate save (selects/checkboxes) don't debounce
- [ ] Optimistic updates (UI updates before server response)
- [ ] Failed requests → Show error, don't lose user input

### Accessibility

- [ ] All interactive elements keyboard accessible
- [ ] Tab navigation works through form fields
- [ ] ESC closes dialogs
- [ ] Focus visible on all inputs
- [ ] Screen reader labels present (aria-labels)
- [ ] Color contrast meets WCAG AA standards

## Known Issues / Future Enhancements

### Not Yet Implemented
- ⏳ Quick add task (inline creation at top of list)
- ⏳ Smart task parsing (e.g., "Fix bug #work @high ^tomorrow")
- ⏳ Recurrence/repeat selector
- ⏳ Reminder selector
- ⏳ Virtualized scrolling (for 1000+ tasks)
- ⏳ Keyboard shortcuts (Cmd+K, Cmd+Enter, etc.)
- ⏳ Bulk actions (multi-select delete/edit)
- ⏳ Right-click context menu
- ⏳ Task templates
- ⏳ Subtasks support

### Potential Bugs to Watch For
- ⚠️ Race conditions with auto-save (rapid edits)
- ⚠️ SWR cache conflicts with optimistic updates
- ⚠️ Date picker timezone issues
- ⚠️ Markdown XSS vulnerabilities (using dangerouslySetInnerHTML)
- ⚠️ Memory leaks from uncancelled debounce timers
- ⚠️ Large description text performance

## Browser Testing

Test in multiple browsers:
- [ ] Chrome/Chromium (primary)
- [ ] Firefox
- [ ] Safari
- [ ] Edge
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

## Completion Criteria

All core features checked ✅ → **Ready for production**

Blockers found → Document and prioritize fixes
