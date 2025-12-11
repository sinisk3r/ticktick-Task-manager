# Quick Start Guide - TickTick-Inspired UI

## What's New?

This redesign adds a comprehensive task editing experience inspired by TickTick, with auto-save, advanced filtering, and a clean interface.

## Key Features

### 1. TaskDetailPopover - Click any task to edit
- **Auto-saves** your changes (no "Save" button needed!)
- Edit title, priority, due dates, description
- Markdown support in descriptions
- See AI analysis and reasoning
- Delete tasks with confirmation

### 2. ListView - New comprehensive list page
- **Search** tasks by title, description, or project
- **Sort** by due date, priority, created, or title
- **Filter** by Today, This Week, Overdue, or Quadrant
- **Group** by Project, Priority, Due Date, or Quadrant
- Click any task to open detail view

### 3. Enhanced Existing Views
- Matrix View cards are now clickable
- Unsorted cards have better styling and detail popups
- Consistent theme across all components

## How to Use

### Opening Task Details
**From anywhere:**
1. Click on any task card/title
2. TaskDetailPopover opens
3. Make your edits (auto-saves after 800ms)
4. Click X or press ESC to close

### Editing a Task
**Title:** Click and type → Auto-saves
**Priority:** Select from dropdown → Saves immediately
**Due Date:** Click calendar, select date → Saves immediately
**Description:** Type text, use markdown → Auto-saves

### Using ListView
1. Go to sidebar → Click "List View"
2. Use toolbar to filter/sort/group:
   - **Search:** Type to filter tasks
   - **Sort:** Choose how to order tasks
   - **Filter:** Show only specific tasks
   - **Group:** Organize into sections
3. Click any task to edit

### Markdown in Descriptions
```markdown
# Big Header
## Medium Header
### Small Header

**Bold text**
*Italic text*
`Code text`

- List item 1
- List item 2
```

Preview: Click "Preview" button to see formatted text

## Navigation

### Sidebar Menu
- **Analyze Task** - AI-powered task analysis
- **My Tasks** - Eisenhower Matrix view
- **List View** ⭐ NEW - Comprehensive list with filters
- **Unsorted** - Tasks pending analysis
- **Simple View** - Minimalist view
- **Settings** - Configuration

## Keyboard Shortcuts

- **ESC** - Close task detail popup
- **Tab** - Navigate between fields
- Future: **Cmd+K** - Quick command palette

## Tips & Tricks

### Auto-Save Behavior
- **Text fields** (title, description) - Wait 800ms before saving
- **Dropdowns** (priority) - Save immediately on change
- **Checkboxes** (completion) - Save immediately on click
- **Date pickers** - Save immediately on selection

### Filtering Best Practices
1. Use **Search** for quick finds by keyword
2. Use **Filter** to narrow by time/quadrant
3. Use **Group** to organize similar tasks
4. Combine them for powerful task management

### Performance
- List View handles 200+ tasks efficiently
- Auto-refresh every 10 seconds (SWR)
- Optimistic updates for instant feedback

## Troubleshooting

### Popover doesn't open
- Check browser console for errors
- Ensure backend is running on port 8000
- Try hard refresh (Cmd+Shift+R)

### Changes don't save
- Check network tab for PATCH requests
- Look for error alerts in the popup
- Verify backend connectivity

### Filters not working
- Ensure tasks have required fields (due_date, priority, etc.)
- Check that filter matches your data
- Try clearing filters (select "All Tasks")

### Search returns no results
- Check spelling
- Try partial words
- Clear search and try again

## File Locations

### New Components
```
frontend/
├── components/
│   ├── TaskDetailPopover.tsx    # Main task editor
│   ├── PrioritySelect.tsx        # Priority dropdown
│   ├── DatePicker.tsx            # Calendar picker
│   ├── MetadataRow.tsx           # Metadata layout
│   └── MarkdownEditor.tsx        # Description editor
├── app/(main)/
│   └── list/
│       └── page.tsx              # List View page
└── types/
    └── task.ts                   # Shared Task type
```

### Updated Components
```
frontend/components/
├── TaskCard.tsx         # Now clickable with popup
├── UnsortedTaskCard.tsx # Updated styling + popup
└── Sidebar.tsx          # Added List View link
```

## API Endpoints Used

```
GET  /api/tasks?user_id=1&status=active&limit=200
PATCH /api/tasks/{id}
DELETE /api/tasks/{id}?user_id=1
```

## Theme Colors

### Light Mode
- Background: `#F5F7FA` (light gray)
- Cards: `#FFFFFF` (white)
- Primary: `#2E6794` (blue)
- Accent: `#4DB6AC` (teal)

### Dark Mode
- Background: `#0B1121` (dark navy)
- Cards: `#151E2E` (darker navy)
- Primary: `#4DB6AC` (teal)
- Accent: `#2E6794` (blue)

Toggle in top bar to switch themes.

## Next Steps

1. **Try it out:** Open any task and edit it
2. **Explore filters:** Go to List View and try different combinations
3. **Add tasks:** Use the Analyze tab to sync from TickTick
4. **Organize:** Use the Matrix View drag-and-drop alongside List View filters

## Future Enhancements

Coming soon:
- Quick add task (inline creation)
- Smart parsing ("Fix bug #work @high ^tomorrow")
- Recurrence/reminders
- Keyboard shortcuts
- Bulk actions
- Task templates

## Support

Questions? Check:
- `TICKTICK_UI_REDESIGN_SUMMARY.md` - Detailed implementation
- `TESTING_CHECKLIST.md` - Feature testing guide
- `CLAUDE.md` - Project documentation

Enjoy the new UI! 🎉
