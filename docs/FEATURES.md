# Features Specification

This document provides detailed specifications for all 9 selected features across 3 phases.

---

## Phase 1: MVP Features

### Feature 1: Smart Task Intake

**Goal:** Automatically analyze incoming tasks from TickTick and intelligently categorize them using Claude LLM.

**User Story:**
> As a user, when I create a task in TickTick, I want Context to automatically determine its urgency and importance so I don't have to manually categorize it.

**Detailed Behavior:**

1. **Task Detection**
   - User creates task in TickTick app
   - TickTick webhook fires to Context backend
   - Task data includes: title, description, due date, project, tags

2. **LLM Analysis**
   - Extract full task context
   - Send to Claude API with analysis prompt
   - Claude returns structured JSON:
   ```json
   {
     "urgency_score": 8,
     "importance_score": 7,
     "effort_hours": 2.5,
     "blockers": ["Need stakeholder approval", "Requires data from finance team"],
     "suggested_tags": ["work", "stakeholder-management", "urgent"],
     "eisenhower_quadrant": "Q1",
     "reasoning": "High urgency due to approaching deadline. High importance as it impacts Q4 revenue goals."
   }
   ```

3. **Quadrant Assignment Rules**
   - **Q1 (Urgent & Important):** urgency ≥ 7 AND importance ≥ 7
   - **Q2 (Not Urgent, Important):** urgency < 7 AND importance ≥ 7
   - **Q3 (Urgent, Not Important):** urgency ≥ 7 AND importance < 7
   - **Q4 (Neither):** urgency < 7 AND importance < 7

4. **Storage**
   - Save task to PostgreSQL with all analysis data
   - Generate embedding for task similarity
   - Store embedding in ChromaDB

5. **User Notification**
   - WebSocket push to frontend
   - Task appears in appropriate quadrant
   - Show confidence score badge

**Acceptance Criteria:**
- ✅ Task created in TickTick appears in Context within 5 seconds
- ✅ LLM analysis completes within 3 seconds
- ✅ Quadrant assignment is accurate ≥80% of the time (based on user feedback)
- ✅ User can see reasoning behind classification
- ✅ If LLM fails, task defaults to Q2 (Important, Not Urgent) for manual review

**Edge Cases:**
- **No description provided:** Use title only, lower confidence score
- **Ambiguous urgency:** Ask user or default to Q2
- **LLM API timeout:** Retry 3x, then queue for later analysis
- **Duplicate task:** Check if similar task exists (using embeddings), link them

**UI Components:**
```typescript
// Frontend notification
<TaskNotification
  task={newTask}
  quadrant="Q1"
  confidence={0.87}
  reasoning="High urgency due to deadline..."
/>
```

**Backend Prompt:**
```python
# app/prompts/task_analysis_v1.txt
SYSTEM_PROMPT = """
You are a task analysis expert. Analyze the given task and provide:
1. Urgency (1-10): How soon does this need to be done?
2. Importance (1-10): How much does this impact long-term goals?
3. Effort (hours): Estimated time to complete
4. Blockers: What might prevent completion?
5. Tags: Categorization tags
6. Quadrant: Q1/Q2/Q3/Q4 based on Eisenhower Matrix

Consider:
- Explicit deadlines
- Keywords like "urgent", "ASAP", "important"
- Context from description
- Project associations

Return JSON only.
"""
```

---

### Feature 2: Basic Dashboard

**Goal:** Provide a clear, compact, dark-mode dashboard with matrix-first layout showing today's priorities.

**User Story:**
> As a user, when I open Context, I want to immediately see what I should work on right now, organized by urgency and importance.

**Dashboard Layout (Matrix First):**

```
┌─────────────────────────────────────────────────────────────────┐
│  Context                      [Today] [This Week] [Settings]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Workload: 28/40 hrs  ███████░░  70%   [Rest Score: 65%]       │
│                                                                  │
├──────────────────────────┬──────────────────────────────────────┤
│    Q1: DO FIRST          │    Q2: SCHEDULE                      │
│    Urgent & Important    │    Important, Not Urgent             │
├──────────────────────────┼──────────────────────────────────────┤
│  ⚠️ Prepare board deck   │  📝 Write Q1 OKRs                   │
│     Due: Today 5pm       │     Due: Next week                   │
│     2hrs ⏱️              │     3hrs ⏱️                         │
│                          │                                      │
│  🔥 Client escalation    │  📚 Review team feedback             │
│     Due: Today EOD       │     Due: This week                   │
│     1hr ⏱️               │     1.5hrs ⏱️                       │
│                          │                                      │
│  + Add task              │  + Add task                          │
├──────────────────────────┼──────────────────────────────────────┤
│    Q3: DELEGATE          │    Q4: ELIMINATE                     │
│    Urgent, Not Important │    Neither Urgent nor Important      │
├──────────────────────────┼──────────────────────────────────────┤
│  📧 Review expense       │  🎮 Gaming setup research            │
│     reports              │     No deadline                      │
│     Due: Tomorrow        │     2hrs ⏱️                         │
│     0.5hrs ⏱️            │                                      │
│                          │                                      │
│  + Add task              │  + Add task                          │
└──────────────────────────┴──────────────────────────────────────┘

Recent Activity                           Rest Reminder
─────────────────────────────────────     ─────────────────────────
✓ Updated investor pitch (Q1)             💡 You've had 6 days of
✓ Completed team standup notes (Q3)           intense work. Consider
📥 New: Schedule dentist appointment (Q3)     blocking Saturday as a
                                              rest day.
```

**Key Components:**

1. **Workload Bar**
   - Shows hours scheduled vs hours available this week
   - Color-coded: Green (<70%), Yellow (70-85%), Red (>85%)
   - Rest score indicator

2. **Eisenhower Matrix (4 Quadrants)**
   - **Q1:** Red accent, bold borders
   - **Q2:** Blue accent
   - **Q3:** Yellow accent
   - **Q4:** Gray accent
   - Tasks are cards with:
     - Title
     - Due date
     - Estimated time
     - Emoji icons for quick visual scanning

3. **Task Card**
   ```tsx
   <TaskCard
     title="Prepare board deck"
     quadrant="Q1"
     dueDate="Today 5pm"
     estimatedHours={2}
     confidence={0.91}
     onDrag={handleDragToNewQuadrant}
     onClick={openTaskDetail}
   />
   ```

4. **Filters (Top Right)**
   - Today / This Week / All
   - Toggle between personal / work / clinic tasks

5. **Recent Activity Feed**
   - Last 5 actions
   - Completed tasks
   - New tasks synced

**Dark Mode Colors:**
```css
--bg-primary: #1f2937;      /* gray-800 */
--bg-secondary: #374151;    /* gray-700 */
--bg-card: #4b5563;         /* gray-600 */
--text-primary: #f9fafb;    /* gray-50 */
--text-secondary: #d1d5db;  /* gray-300 */
--accent-q1: #ef4444;       /* red-500 */
--accent-q2: #3b82f6;       /* blue-500 */
--accent-q3: #eab308;       /* yellow-500 */
--accent-q4: #6b7280;       /* gray-500 */
```

**Responsive Behavior:**
- Desktop (>1024px): 2x2 grid for quadrants
- Tablet (768-1024px): 2x2 grid, smaller cards
- Mobile (<768px): Stack vertically, Q1 first

**Performance:**
- Dashboard loads in <1 second
- WebSocket updates appear instantly
- Optimistic UI updates (don't wait for server)

**Acceptance Criteria:**
- ✅ Dashboard loads all tasks within 1 second
- ✅ Matrix layout is clear and scannable in <5 seconds
- ✅ Dark mode is easy on eyes for extended use
- ✅ Drag-and-drop between quadrants works smoothly
- ✅ Clicking task opens detail view
- ✅ Workload bar updates in real-time

---

### Feature 3: Manual Overrides

**Goal:** Allow users to manually adjust task priorities and quadrant assignments when LLM gets it wrong.

**User Story:**
> As a user, when Context misclassifies a task, I want to easily move it to the correct quadrant and adjust its priority so my dashboard stays accurate.

**Override Types:**

1. **Quadrant Override**
   - Drag task from one quadrant to another
   - Click task → "Move to Q2" button
   - System asks: "Why?" (optional feedback to improve LLM)

2. **Priority Override**
   - Adjust urgency slider (1-10)
   - Adjust importance slider (1-10)
   - System recalculates quadrant based on new scores

3. **Effort Override**
   - Edit estimated hours
   - Useful when LLM underestimates complexity

4. **Blocker Override**
   - Add/remove blockers manually
   - Mark blockers as resolved

**UI Flow:**

```tsx
// Task Detail Modal
<TaskDetail task={task}>
  <Header>
    <Title>{task.title}</Title>
    {task.manualOverride && (
      <Badge>Manual Override Active</Badge>
    )}
  </Header>
  
  <Section title="LLM Analysis">
    <Stat label="Urgency" value={task.llmUrgency} />
    <Stat label="Importance" value={task.llmImportance} />
    <Stat label="Quadrant" value={task.llmQuadrant} />
    <Text>{task.llmReasoning}</Text>
  </Section>
  
  <Section title="Your Override">
    <Slider
      label="Urgency"
      value={task.manualUrgency || task.llmUrgency}
      onChange={updateUrgency}
    />
    <Slider
      label="Importance"
      value={task.manualImportance || task.llmImportance}
      onChange={updateImportance}
    />
    <QuadrantSelector
      value={task.manualQuadrant || task.llmQuadrant}
      onChange={updateQuadrant}
    />
  </Section>
  
  <FeedbackForm>
    <Textarea
      placeholder="Why did you override? (helps us improve)"
      optional
    />
  </FeedbackForm>
</TaskDetail>
```

**Backend Logic:**

```python
# app/services/task_service.py
class TaskService:
    async def apply_manual_override(
        self,
        task_id: str,
        urgency: int = None,
        importance: int = None,
        quadrant: str = None,
        feedback: str = None
    ):
        task = await self.get_task(task_id)
        
        # Store original LLM values if first override
        if not task.manual_override:
            task.llm_urgency = task.urgency_score
            task.llm_importance = task.importance_score
            task.llm_quadrant = task.eisenhower_quadrant
        
        # Apply overrides
        if urgency is not None:
            task.urgency_score = urgency
        if importance is not None:
            task.importance_score = importance
        if quadrant is not None:
            task.eisenhower_quadrant = quadrant
        else:
            # Recalculate quadrant from scores
            task.eisenhower_quadrant = self.calculate_quadrant(
                task.urgency_score,
                task.importance_score
            )
        
        task.manual_override = True
        task.override_feedback = feedback
        task.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        # Log for LLM training
        await self.log_override(task_id, feedback)
        
        return task
```

**Reset Override:**
- Button: "Reset to LLM Analysis"
- Restores original LLM values
- Useful if user changes mind

**Bulk Operations:**
- Select multiple tasks
- Apply same override to all
- E.g., "Move all these to Q2"

**Acceptance Criteria:**
- ✅ User can drag task between quadrants
- ✅ Sliders for urgency/importance work smoothly
- ✅ Override is saved immediately (no "Save" button needed)
- ✅ Override badge is visible on task card
- ✅ Can reset to LLM values with one click
- ✅ Feedback is optional but encouraged
- ✅ Override doesn't affect TickTick (only Context view)

**Analytics:**
- Track override frequency per user
- Identify patterns in LLM mistakes
- Use feedback to improve prompts

---

## Phase 2: Integration Features

### Feature 4: Contextual Email Drafts

**Goal:** Generate intelligent, context-aware email drafts for tasks that require communication.

**User Story:**
> As a user, when I need to send an update about a task, I want Context to draft an email for me based on the task details so I can save time writing from scratch.

**Trigger Points:**

1. **Manual:** Click "Draft Email" on any task
2. **Automatic:** Suggest draft when:
   - Task is in Q1 and involves stakeholders
   - Task has been in-progress >3 days
   - Task is blocked and needs escalation

**Email Types:**

| Type | Use Case | Example Task |
|------|----------|--------------|
| Status Update | Inform stakeholders of progress | "Update board on Q4 strategy" |
| Request | Ask for info/approval | "Get budget approval from CFO" |
| Escalation | Flag blockers | "Design mockups delayed" |
| Delegation | Assign to someone else | "Expense report review" |

**UI Flow:**

```tsx
// Task Detail View
<Task task={task}>
  <ActionButtons>
    <Button onClick={generateEmailDraft}>
      ✉️ Draft Email
    </Button>
  </ActionButtons>
</Task>

// After clicking, modal opens
<EmailDraftModal>
  <RecipientField
    value={suggestedRecipients}
    editable
  />
  <TypeSelector
    options={['Status Update', 'Request', 'Escalation']}
    selected="Status Update"
  />
  <GeneratingLoader />  {/* Shows while LLM works */}
  
  {/* Once generated */}
  <EmailPreview>
    <Subject>{draft.subject}</Subject>
    <Body>{draft.body}</Body>
  </EmailPreview>
  
  <Actions>
    <Button onClick={copyToClipboard}>Copy</Button>
    <Button onClick={openInGmail}>Open in Gmail</Button>
    <Button onClick={sendDirectly}>Send Now</Button>
    <Button variant="secondary" onClick={regenerate}>
      Regenerate
    </Button>
  </Actions>
</EmailDraftModal>
```

**LLM Prompt:**

```python
# app/prompts/email_draft_v1.txt
SYSTEM_PROMPT = """
You are an executive assistant helping draft professional emails.

Task: {task_title}
Description: {task_description}
Current Status: {task_status}
Blockers: {blockers}
Due Date: {due_date}

Recipient: {recipient}
Recipient Relationship: {relationship}  # e.g., "Manager", "Stakeholder", "Team member"

Email Type: {email_type}  # Status Update, Request, Escalation, Delegation

Write a concise, professional email that:
1. Opens with context
2. States the main point clearly
3. Includes specific details from the task
4. Has a clear call-to-action
5. Is appropriately formal for the relationship

Tone: Professional but warm. Avoid corporate jargon.
Length: 100-200 words.

Return JSON:
{
  "subject": "...",
  "body": "...",
  "suggested_ccs": ["..."]
}
"""
```

**Example Output:**

```json
{
  "subject": "Q4 Board Deck - Status Update",
  "body": "Hi Sarah,\n\nI wanted to give you a quick update on the Q4 board deck preparation.\n\nI've completed the financial sections and key metrics slides. However, I'm currently blocked on the product roadmap section as I'm waiting for input from the product team. I've reached out to them this morning.\n\nI'm still on track to have the full deck ready by Thursday 5pm, assuming I get the product input by tomorrow.\n\nLet me know if you'd like to review what I have so far.\n\nBest,\n[Your Name]",
  "suggested_ccs": ["product-team@company.com"]
}
```

**Gmail Integration:**

```python
# app/services/email_service.py
class EmailService:
    async def send_via_gmail(
        self,
        user_id: str,
        draft: EmailDraft
    ):
        # Get user's Gmail OAuth token
        gmail_token = await self.get_gmail_token(user_id)
        
        # Create Gmail draft
        service = build('gmail', 'v1', credentials=gmail_token)
        message = {
            'raw': base64.urlsafe_b64encode(
                self.create_message(
                    sender='me',
                    to=draft.recipient,
                    subject=draft.subject,
                    body=draft.body
                ).as_bytes()
            ).decode()
        }
        
        draft_result = service.users().drafts().create(
            userId='me',
            body={'message': message}
        ).execute()
        
        return draft_result['id']
```

**Edge Cases:**
- **No recipient provided:** Ask user to specify
- **Multiple recipients:** Generate slightly different drafts for each
- **Sensitive task:** Warn user to review carefully before sending
- **No Gmail connected:** Show "Copy to clipboard" only

**Acceptance Criteria:**
- ✅ Draft generates within 5 seconds
- ✅ Email tone matches task urgency (urgent = more direct)
- ✅ Includes specific task details (not generic)
- ✅ Can regenerate with different tone/length
- ✅ One-click "Open in Gmail" works
- ✅ Drafts are saved to email_drafts table
- ✅ User can edit draft before sending

**Rate Limiting:**
- 10 email drafts per hour per user
- Prevents abuse of LLM API

---

### Feature 5: Workload Intelligence

**Goal:** Track user's capacity and provide insights on overcommitment risk.

**User Story:**
> As a user, I want to know if I'm taking on too much work so I can avoid burnout and reschedule tasks proactively.

**Metrics Tracked:**

1. **Hours Scheduled vs Available**
   ```
   Weekly: 28 scheduled / 40 available = 70%
   Daily: 6 scheduled / 8 available = 75%
   ```

2. **Overcommitment Risk**
   - **Low:** <70% capacity
   - **Medium:** 70-85% capacity
   - **High:** >85% capacity
   - **Critical:** >100% capacity

3. **Work Intensity Score**
   - Based on: Q1 task count, consecutive work days, average task complexity
   - Scale: 1-10 (10 = very intense)

4. **Rest Score**
   - Scale: 0-100% (100% = well-rested)
   - Factors:
     - Days since last rest day
     - Work intensity last 7 days
     - Sleep quality (if integrated with Apple Health)

**Dashboard Widget:**

```tsx
<WorkloadWidget>
  <Header>
    <Title>This Week's Workload</Title>
    <RiskBadge level={risk}>
      {risk === 'high' ? '⚠️ High Risk' : '✅ Healthy'}
    </RiskBadge>
  </Header>
  
  <ProgressBar
    current={hoursScheduled}
    total={hoursAvailable}
    color={getColorByRisk(risk)}
  />
  
  <Stats>
    <Stat label="Q1 Tasks" value={q1Count} />
    <Stat label="Intensity" value={`${intensity}/10`} />
    <Stat label="Rest Score" value={`${restScore}%`} />
  </Stats>
  
  {risk === 'high' && (
    <Alert variant="warning">
      You're at 92% capacity. Consider:
      • Delegating 2 Q3 tasks
      • Rescheduling "Marketing review" to next week
      • Blocking Friday afternoon for catch-up
    </Alert>
  )}
  
  {restScore < 50 && (
    <Alert variant="info">
      💡 You've had 6 intense work days. Block Saturday as a rest day?
    </Alert>
  )}
</WorkloadWidget>
```

**Analytics View:**

```
┌───────────────────────────────────────────────────────────────┐
│  Workload Analytics                        [This Week] [Month] │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  Capacity Trend                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │100% ┤                                               ███   │ │
│  │ 85% ┤                                   ████████████     │ │
│  │ 70% ┤               ████████████████████                 │ │
│  │ 50% ┤   ████████████                                     │ │
│  │  0% └─────┬─────┬─────┬─────┬─────┬─────┬─────┬────────│ │
│  │         Mon   Tue   Wed   Thu   Fri   Sat   Sun         │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Time by Quadrant                                              │
│  Q1: ████████████░░░░░░░░░░  12hrs (30%)                     │
│  Q2: ████████████████░░░░░░  16hrs (40%)                     │
│  Q3: ████░░░░░░░░░░░░░░░░░░   4hrs (10%)                     │
│  Q4: ████░░░░░░░░░░░░░░░░░░   4hrs (10%)                     │
│       Free: ████░░░░░░░░░░░   4hrs (10%)                     │
│                                                                │
│  Insights                                                      │
│  • Peak overload: Thu-Fri (95% capacity)                      │
│  • Most Q1 tasks: Wednesday                                   │
│  • Rest deficit: 3 days                                       │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

**Calculation Logic:**

```python
# app/services/analytics_service.py
class WorkloadAnalytics:
    def calculate_capacity(
        self,
        tasks: List[Task],
        working_hours_per_day: int = 8
    ) -> CapacityReport:
        # Sum task effort hours
        total_scheduled = sum(t.effort_hours for t in tasks)
        
        # Calculate available hours
        work_days = 5  # Mon-Fri
        total_available = work_days * working_hours_per_day
        
        # Calculate percentage
        capacity_pct = (total_scheduled / total_available) * 100
        
        # Determine risk
        if capacity_pct > 100:
            risk = 'critical'
        elif capacity_pct > 85:
            risk = 'high'
        elif capacity_pct > 70:
            risk = 'medium'
        else:
            risk = 'low'
        
        return CapacityReport(
            scheduled=total_scheduled,
            available=total_available,
            percentage=capacity_pct,
            risk=risk
        )
    
    def calculate_work_intensity(
        self,
        tasks: List[Task]
    ) -> int:
        # Factors:
        # 1. Q1 task count (weight: 40%)
        # 2. Average task complexity (weight: 30%)
        # 3. Consecutive work days (weight: 30%)
        
        q1_count = len([t for t in tasks if t.quadrant == 'Q1'])
        q1_score = min(q1_count / 5, 1) * 10  # Cap at 5 Q1 tasks
        
        avg_complexity = sum(t.complexity for t in tasks) / len(tasks)
        complexity_score = (avg_complexity / 3) * 10  # Scale 0-3 to 0-10
        
        consecutive_days = self.get_consecutive_work_days()
        days_score = min(consecutive_days / 7, 1) * 10  # Cap at 7 days
        
        intensity = (
            q1_score * 0.4 +
            complexity_score * 0.3 +
            days_score * 0.3
        )
        
        return round(intensity)
    
    def calculate_rest_score(
        self,
        work_intensity_history: List[int],
        days_since_rest: int
    ) -> int:
        # Start at 100%
        score = 100
        
        # Deduct for consecutive work days
        score -= days_since_rest * 5  # -5% per day
        
        # Deduct for high intensity
        avg_intensity = sum(work_intensity_history) / len(work_intensity_history)
        if avg_intensity > 7:
            score -= 20
        elif avg_intensity > 5:
            score -= 10
        
        return max(score, 0)
```

**Suggestions Engine:**

When overcommitment detected, LLM suggests:
1. **Which Q3 tasks to delegate**
2. **Which Q2 tasks to reschedule**
3. **When to block rest time**

```python
async def generate_workload_suggestions(
    self,
    user_id: str,
    capacity_report: CapacityReport
) -> List[Suggestion]:
    if capacity_report.risk in ['high', 'critical']:
        tasks = await self.get_user_tasks(user_id)
        
        prompt = f"""
        User is at {capacity_report.percentage}% capacity (risk: {capacity_report.risk}).
        
        Tasks: {json.dumps([t.dict() for t in tasks])}
        
        Suggest 3 specific actions to reduce overload:
        1. Which tasks to delegate (Q3 only)
        2. Which tasks to reschedule (Q2 only)
        3. When to block rest time
        
        Be specific with task names.
        """
        
        suggestions = await self.llm.call(prompt)
        return suggestions
```

**Acceptance Criteria:**
- ✅ Capacity calculation updates in real-time
- ✅ Risk badge shows correct level
- ✅ Suggestions are specific and actionable
- ✅ Rest score factors in work intensity
- ✅ Analytics view loads within 2 seconds
- ✅ Charts are responsive and readable

---

### Feature 6: Rest Reminders

**Goal:** Proactively remind users to take breaks when work intensity is high.

**User Story:**
> As a user, I want Context to tell me when I should take a break so I don't burn out.

**Trigger Conditions:**

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Consecutive work days | ≥6 days | Suggest rest day |
| Work intensity | ≥8/10 for 3+ days | Suggest half-day break |
| Rest score | <40% | Urgent rest needed |
| Q1 task overload | ≥5 Q1 tasks/day | Block buffer time |

**Reminder Types:**

1. **Daily Rest Day**
   ```
   💡 You've worked 6 days straight with high intensity.
   
   Suggestion: Block Saturday as a full rest day.
   
   [Block Saturday] [Remind me tomorrow] [Dismiss]
   ```

2. **Buffer Time**
   ```
   ⚠️ You have 5 Q1 tasks tomorrow (8 hours).
   
   This leaves no buffer for unexpected issues.
   
   Suggestion: Reschedule "Marketing review" (Q2) to next week.
   
   [Reschedule it] [I'll manage] [Dismiss]
   ```

3. **Wellness Break**
   ```
   🌟 Your rest score is 35% (low).
   
   Consider taking a 2-hour break this afternoon.
   
   [Block 2pm-4pm] [Not today] [Dismiss]
   ```

**UI Integration:**

**Banner on Dashboard:**
```tsx
{restScore < 50 && (
  <RestReminderBanner>
    <Icon>💡</Icon>
    <Message>
      You've had {consecutiveWorkDays} intense work days. 
      Consider blocking {suggestedRestDay} as a rest day?
    </Message>
    <Actions>
      <Button onClick={blockRestDay}>
        Block {suggestedRestDay}
      </Button>
      <Button variant="ghost" onClick={dismiss}>
        Dismiss
      </Button>
    </Actions>
  </RestReminderBanner>
)}
```

**Calendar Blocking:**
When user clicks "Block Saturday":
1. Create all-day calendar event: "🌴 Rest Day"
2. Mark tasks due Saturday as "Reschedule needed"
3. Show confirmation: "Saturday blocked. 3 tasks rescheduled to Monday."

**Acceptance Criteria:**
- ✅ Reminders appear when conditions are met
- ✅ User can dismiss for 24 hours
- ✅ One-click calendar blocking works
- ✅ Rest days are respected (no tasks scheduled)
- ✅ Reminder doesn't nag if user dismisses
- ✅ Tracks rest day compliance over time

---

## Phase 3: Advanced Automation Features

### Feature 7: Auto Azure DevOps Creation

**Goal:** Automatically create Azure DevOps work items from TickTick tasks tagged with "work".

**User Story:**
> As a product manager, when I create a work task in TickTick, I want it automatically created in Azure DevOps so I don't have to duplicate entry.

**Trigger:**
- Task in TickTick tagged with "work" OR
- Task in specific TickTick project (e.g., "ServiceNow Q4")

**Mapping:**

| TickTick | Azure DevOps |
|----------|--------------|
| Title | Title |
| Description | Description |
| Due Date | Target Date |
| Tags | Tags |
| Priority (urgency score) | Priority (1-4) |
| Checklist items | Acceptance Criteria |

**Azure DevOps Work Item Type:**
- Default: **User Story**
- Can be configured per user

**Flow:**

```
Task created in TickTick with "work" tag
    ↓
Webhook to Context backend
    ↓
Detect "work" tag
    ↓
Queue Celery task: create_azure_workitem
    ↓
[Async] Fetch user's Azure DevOps config
    ↓
Map TickTick task fields to Azure format
    ↓
Call Azure DevOps API to create work item
    ↓
Store mapping in azure_workitems table
    ↓
Add link to TickTick task notes: "Azure: [Work Item #1234]"
    ↓
Update TickTick via API with link
    ↓
Notify user: "Work item created in Azure DevOps"
```

**Configuration UI:**

```tsx
<AzureDevOpsSettings>
  <Toggle
    label="Auto-create work items"
    checked={autoCreate}
    onChange={setAutoCreate}
  />
  
  <Select
    label="Organization"
    options={orgs}
    value={selectedOrg}
  />
  
  <Select
    label="Project"
    options={projects}
    value={selectedProject}
  />
  
  <Select
    label="Work Item Type"
    options={['User Story', 'Bug', 'Task']}
    value={workItemType}
  />
  
  <MultiSelect
    label="Trigger Tags"
    options={userTags}
    value={triggerTags}
    placeholder="E.g., 'work', 'dev', 'sprint'"
  />
</AzureDevOpsSettings>
```

**Backend Implementation:**

```python
# app/services/azure_service.py
class AzureDevOpsService:
    async def create_work_item(
        self,
        user_id: str,
        task: Task
    ) -> WorkItem:
        config = await self.get_user_config(user_id)
        
        # Map priority
        priority_map = {
            range(1, 4): 4,   # Low urgency → Priority 4
            range(4, 7): 3,   # Medium → Priority 3
            range(7, 9): 2,   # High → Priority 2
            range(9, 11): 1,  # Critical → Priority 1
        }
        priority = next(
            p for r, p in priority_map.items() 
            if task.urgency_score in r
        )
        
        # Build work item
        work_item_data = {
            'op': 'add',
            'path': '/fields/System.Title',
            'value': task.title
        }
        # ... add other fields
        
        # Call Azure API
        url = f"{config.org_url}/{config.project}/_apis/wit/workitems/${config.work_item_type}?api-version=7.0"
        headers = {
            'Content-Type': 'application/json-patch+json',
            'Authorization': f'Basic {config.pat}'
        }
        
        response = await self.http_client.post(
            url,
            json=work_item_data,
            headers=headers
        )
        
        work_item = response.json()
        
        # Store mapping
        await self.db.azure_workitems.insert({
            'user_id': user_id,
            'task_id': task.id,
            'azure_workitem_id': work_item['id'],
            'azure_url': work_item['_links']['html']['href']
        })
        
        return work_item
```

**Bi-directional Sync (Future):**
- When work item status changes in Azure → update TickTick
- When TickTick task completed → close work item

**Acceptance Criteria:**
- ✅ Work item created within 10 seconds of task creation
- ✅ All fields mapped correctly
- ✅ Link added to TickTick task
- ✅ User notified of creation
- ✅ Can view Azure work item from Context UI
- ✅ Error handling if Azure API fails

---

### Feature 8: Weekly Planning Assistant

**Goal:** Every Sunday, review last week and suggest priorities for next week.

**User Story:**
> As a user, at the end of each week, I want Context to analyze my progress and suggest what I should focus on next week.

**Schedule:**
- Runs every Sunday at 6pm (user configurable)
- Takes ~30 seconds to generate
- Notification sent to user

**Weekly Review Contents:**

```
┌─────────────────────────────────────────────────────────────┐
│  Weekly Review: Dec 2-8, 2024                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 Last Week's Summary                                     │
│  ──────────────────                                         │
│  Tasks Completed:  12 / 15  (80%)                           │
│  Time Spent:       32 hours                                 │
│  Q1 Completion:    4 / 5   (80%)                            │
│  Q2 Completion:    6 / 8   (75%)                            │
│  Rest Days Taken:  1                                        │
│                                                              │
│  ✨ Wins                                                     │
│  • Completed Q4 board deck ahead of schedule                │
│  • Resolved 2 client escalations                            │
│  • Finished team OKR planning                               │
│                                                              │
│  ⚠️ Patterns Observed                                       │
│  • 3 Q3 tasks rolled over (delegation needed?)              │
│  • "Marketing review" rescheduled twice (blocker?)          │
│  • High intensity Thu-Fri (92% capacity)                    │
│                                                              │
│  🎯 Next Week's Priorities (Dec 9-15)                       │
│  ────────────────────────                                   │
│  Top 3 Focus Areas:                                         │
│  1. Q1 planning finalization (due Wed)                      │
│  2. Budget reviews with finance team                        │
│  3. Hiring pipeline for 2 PM roles                          │
│                                                              │
│  📋 Suggested Schedule                                      │
│  Mon: Q1 planning deep work (4hrs)                          │
│  Tue: Budget review meetings (3hrs)                         │
│  Wed: Finalize Q1 plan, send to board                       │
│  Thu: Hiring interviews (2 candidates)                      │
│  Fri: Catch-up & weekly recap                               │
│                                                              │
│  🔄 Tasks to Delegate                                       │
│  • Expense report review → Finance team                     │
│  • Social media content approval → Marketing                │
│                                                              │
│  🚨 Blockers to Address                                     │
│  • "Marketing review" blocked by design team               │
│    → Schedule sync meeting with design                      │
│                                                              │
│  💡 Recommendations                                         │
│  • Block Friday afternoon as buffer time                    │
│  • Consider a rest day on Saturday                          │
│  • Limit Q1 tasks to max 3 per day                          │
│                                                              │
│  [View Full Report] [Accept Suggestions] [Customize]       │
└─────────────────────────────────────────────────────────────┘
```

**LLM Prompt:**

```python
# app/prompts/weekly_review_v1.txt
SYSTEM_PROMPT = """
You are a strategic planning assistant. Analyze the user's past week and create a comprehensive weekly review.

Past Week Data:
- Tasks completed: {completed_tasks}
- Tasks incomplete: {incomplete_tasks}
- Time spent per quadrant: {time_breakdown}
- Overcommitment events: {overcommitment_instances}
- Rest days taken: {rest_days}

Next Week Visibility:
- Upcoming tasks: {upcoming_tasks}
- Calendar events: {calendar_events}
- Deadlines: {deadlines}

Provide:
1. **Summary**: Completion %, time spent, key metrics
2. **Wins**: Top 3 accomplishments
3. **Patterns**: Issues observed (delegation gaps, repeated reschedules, overcommitment)
4. **Top 3 Priorities**: Most important focuses for next week
5. **Suggested Schedule**: Day-by-day rough plan
6. **Delegation**: Q3 tasks to hand off
7. **Blockers**: Issues to address proactively
8. **Recommendations**: Workload management advice

Be specific with task names. Be encouraging but honest about problems.

Return structured JSON.
"""
```

**User Actions:**

1. **Accept Suggestions**
   - Auto-schedules recommended tasks
   - Blocks buffer time
   - Creates delegation tasks

2. **Customize**
   - Adjust priorities
   - Change schedule
   - Regenerate with tweaks

3. **Dismiss**
   - Skip this week's plan
   - Keep working ad-hoc

**Acceptance Criteria:**
- ✅ Review generates every Sunday at 6pm
- ✅ Analysis is accurate (80%+ user satisfaction)
- ✅ Suggestions are actionable
- ✅ One-click "Accept All" works
- ✅ Can customize before accepting
- ✅ Historical reviews are saved

---

### Feature 9: Voice Note Capture

**Goal:** Record voice notes that are transcribed and converted into tasks automatically.

**User Story:**
> As a user, when I think of a task while driving or away from my desk, I want to quickly record it as a voice note and have it automatically added to my task list.

**UI:**

```tsx
<VoiceCapture>
  <RecordButton
    onPress={startRecording}
    onRelease={stopRecording}
  >
    🎤 Hold to record
  </RecordButton>
  
  {isRecording && (
    <RecordingIndicator>
      <Waveform />
      <Timer>{duration}s</Timer>
    </RecordingIndicator>
  )}
  
  {isProcessing && (
    <ProcessingLoader>
      Transcribing...
    </ProcessingLoader>
  )}
  
  {tasks.length > 0 && (
    <ExtractedTasks>
      <Title>Found {tasks.length} task(s):</Title>
      {tasks.map(task => (
        <TaskPreview
          key={task.id}
          task={task}
          onEdit={editTask}
          onDelete={deleteTask}
        />
      ))}
      <Button onClick={addToTickTick}>
        Add all to TickTick
      </Button>
    </ExtractedTasks>
  )}
</VoiceCapture>
```

**Processing Pipeline:**

```
User records voice note (up to 60 seconds)
    ↓
Audio file uploaded to backend
    ↓
Send to OpenAI Whisper API for transcription
    ↓
Receive transcript text
    ↓
Send transcript to Claude API:
  "Extract actionable tasks from this voice note.
   Return JSON array of tasks with titles and descriptions."
    ↓
Claude returns:
  [
    {
      "title": "Schedule dentist appointment",
      "description": "Call Dr. Smith's office tomorrow morning",
      "urgency": 6,
      "importance": 5,
      "tags": ["personal", "health"]
    },
    {
      "title": "Buy groceries",
      "description": "Milk, eggs, bread",
      "urgency": 5,
      "importance": 4,
      "tags": ["personal", "shopping"]
    }
  ]
    ↓
Show extracted tasks to user for confirmation
    ↓
User confirms
    ↓
Create tasks in TickTick via API
    ↓
Tasks appear in Context dashboard
```

**Transcription Example:**

**Voice:**
> "Okay so I need to schedule a dentist appointment tomorrow morning, probably around 10am. Also remind me to buy groceries, we need milk, eggs, and bread. Oh and I should follow up with Sarah about the Q4 planning deck, she said she'd have feedback by Wednesday."

**Extracted Tasks:**
1. **Schedule dentist appointment**
   - Description: Call to book appointment for tomorrow ~10am
   - Urgency: 7, Importance: 5
   - Tags: personal, health

2. **Buy groceries**
   - Description: Milk, eggs, bread
   - Urgency: 5, Importance: 4
   - Tags: personal, shopping

3. **Follow up with Sarah on Q4 deck**
   - Description: Sarah will have feedback by Wednesday
   - Urgency: 6, Importance: 8
   - Tags: work, stakeholder-management

**Backend:**

```python
# app/services/voice_service.py
class VoiceService:
    async def process_voice_note(
        self,
        user_id: str,
        audio_file: bytes
    ) -> List[Task]:
        # 1. Transcribe with Whisper
        transcript = await self.transcribe(audio_file)
        
        # 2. Extract tasks with Claude
        tasks = await self.extract_tasks(transcript)
        
        # 3. Store temporarily for user confirmation
        voice_session = await self.db.voice_sessions.insert({
            'user_id': user_id,
            'transcript': transcript,
            'extracted_tasks': tasks,
            'status': 'pending_confirmation'
        })
        
        return tasks
    
    async def transcribe(self, audio: bytes) -> str:
        # Use OpenAI Whisper API
        response = await openai.Audio.transcribe(
            model="whisper-1",
            file=audio
        )
        return response['text']
    
    async def extract_tasks(self, transcript: str) -> List[Dict]:
        prompt = f"""
        Extract actionable tasks from this voice note:
        "{transcript}"
        
        Return JSON array of tasks. Each task should have:
        - title: Clear, action-oriented title
        - description: Additional context from the note
        - urgency: 1-10 score
        - importance: 1-10 score
        - due_date: If mentioned, parse it (ISO format)
        - tags: Relevant tags
        
        If no tasks found, return empty array.
        """
        
        tasks = await self.llm.call(prompt, response_format='json')
        return tasks
```

**Edge Cases:**
- **Rambling note:** Extract only actionable items
- **Multiple tasks:** Separate clearly
- **No tasks:** Inform user, save transcript anyway
- **Background noise:** Whisper handles it well
- **Accents/unclear speech:** Best-effort transcription

**Mobile App Integration (Future):**
- Native mobile app with push-to-talk
- Siri/Google Assistant integration
- Widget on home screen

**Acceptance Criteria:**
- ✅ Transcription accuracy >95% (clear audio)
- ✅ Task extraction is accurate (>80% correct)
- ✅ Processing completes within 10 seconds
- ✅ User can edit extracted tasks before adding
- ✅ Works on desktop (via microphone) and mobile
- ✅ Audio files are deleted after processing (privacy)

---

## Testing Strategy

### Unit Tests
- LLM service mock responses
- Task quadrant calculation logic
- Workload capacity calculations
- Date parsing and timezone handling

### Integration Tests
- TickTick OAuth flow
- Gmail draft creation
- Azure DevOps API calls
- WebSocket real-time updates

### E2E Tests
- User creates task → see it in dashboard
- Drag task between quadrants → persists
- Generate email draft → opens in Gmail
- Voice note → tasks created

### User Acceptance Testing
- 5 beta users test each feature
- Collect feedback on LLM accuracy
- Measure time saved per feature
- Track feature usage frequency

---

## Success Metrics

| Feature | Metric | Target |
|---------|--------|--------|
| Smart Task Intake | LLM accuracy | >80% |
| Email Drafts | Time saved per draft | >5 min |
| Workload Intelligence | Users adjusting workload | >60% |
| Rest Reminders | Users taking suggested rest | >40% |
| Azure DevOps Sync | Adoption rate | >70% |
| Weekly Planning | Satisfaction score | >4/5 |
| Voice Capture | Daily active users | >50% |

---

**Last Updated:** 2024-12-09
