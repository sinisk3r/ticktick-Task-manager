# MVP Implementation Roadmap

**Total Duration:** 10.5 weeks (52.5 days)  
**Work Schedule:** 10-15 hours/week  
**Target Launch:** Mid-February 2025

---

## Pre-Development (Week 0)

### Setup Checklist
- [ ] Create GitHub repository
- [ ] Register TickTick OAuth app at developer.ticktick.com
- [ ] Get Claude API key from Anthropic
- [ ] Set up PostgreSQL database (Railway)
- [ ] Set up Redis instance (Railway)
- [ ] Create project Kanban board (GitHub Projects)

**Time:** 3-4 hours

---

## Phase 1: MVP (Weeks 1-4)

### Week 1: Foundation & Authentication

**Goal:** Set up project structure and TickTick OAuth

**Backend Tasks:**
- [ ] Initialize FastAPI project structure
- [ ] Configure PostgreSQL with SQLAlchemy
- [ ] Set up Alembic for migrations
- [ ] Create User model
- [ ] Implement TickTick OAuth flow
  - Authorization endpoint
  - Callback handler
  - Token refresh logic
- [ ] Create JWT-based session management
- [ ] Write tests for auth flow

**Frontend Tasks:**
- [ ] Initialize Next.js project with TypeScript
- [ ] Set up Tailwind CSS with dark mode
- [ ] Configure shadcn/ui components
- [ ] Create login page
- [ ] Implement OAuth redirect flow
- [ ] Create authenticated layout wrapper

**Deliverables:**
- ✅ User can log in with TickTick
- ✅ Session persists across page refreshes
- ✅ Logout functionality works

**Time Investment:** 12-15 hours

**Checkpoint:** Can you successfully authenticate and see your TickTick user info?

---

### Week 2: Smart Task Intake

**Goal:** Fetch tasks from TickTick and analyze them with Claude

**Backend Tasks:**
- [ ] Create Task model (PostgreSQL)
- [ ] Implement TickTick API client
  - Get all tasks endpoint
  - Get task by ID
  - Update task
- [ ] Create LLM service for Claude API
- [ ] Write task analysis prompt (v1)
- [ ] Implement analyze_task() function
  - Parse urgency/importance
  - Assign quadrant
  - Extract blockers
- [ ] Create Celery worker setup
- [ ] Background job: analyze_new_task
- [ ] API endpoint: POST /api/sync/ticktick
- [ ] API endpoint: GET /api/tasks
- [ ] Write unit tests for LLM service

**Frontend Tasks:**
- [ ] Create Task type definitions
- [ ] Build API client (lib/api.ts)
- [ ] Create TaskCard component
- [ ] Build basic task list view
- [ ] Show LLM analysis results

**Deliverables:**
- ✅ Tasks sync from TickTick
- ✅ Claude analyzes each task
- ✅ Quadrant assignment visible

**Time Investment:** 15-18 hours

**Checkpoint:** Do your TickTick tasks appear with urgency/importance scores?

---

### Week 3: Dashboard & Matrix

**Goal:** Build the Eisenhower matrix dashboard

**Backend Tasks:**
- [ ] API endpoint: GET /api/tasks/by-quadrant
- [ ] Implement filtering (today, this week, all)
- [ ] Add caching layer (Redis)
- [ ] WebSocket server setup for real-time updates

**Frontend Tasks:**
- [ ] Create EisenhowerMatrix component
  - 2x2 grid layout
  - Responsive design
  - Dark mode styling
- [ ] Implement drag-and-drop between quadrants
  - react-dnd or dnd-kit library
  - Optimistic updates
- [ ] Create WorkloadWidget component
  - Progress bar
  - Capacity percentage
  - Risk badge
- [ ] Build dashboard page (app/page.tsx)
  - Matrix as primary view
  - Workload widget above
  - Filter controls
- [ ] Implement WebSocket connection
  - Auto-reconnect on disconnect
  - Handle real-time task updates

**Deliverables:**
- ✅ Dashboard shows tasks in 4 quadrants
- ✅ Can drag tasks between quadrants
- ✅ Real-time updates work
- ✅ Dark mode looks good

**Time Investment:** 12-15 hours

**Checkpoint:** Does the dashboard feel fast and intuitive?

---

### Week 4: Manual Overrides & Polish

**Goal:** Allow users to override LLM decisions

**Backend Tasks:**
- [ ] Add manual override fields to Task model
  - manual_urgency
  - manual_importance
  - manual_quadrant
  - manual_override (boolean)
  - override_feedback (text)
- [ ] API endpoint: PUT /api/tasks/{id}/priority
- [ ] API endpoint: PUT /api/tasks/{id}/quadrant
- [ ] Store override feedback for LLM improvement
- [ ] Run database migration

**Frontend Tasks:**
- [ ] Create TaskDetailModal component
  - Show LLM analysis
  - Sliders for urgency/importance
  - Quadrant selector
  - Feedback textarea
- [ ] Implement modal state management
- [ ] Add "Reset to LLM" button
- [ ] Show override badge on task cards
- [ ] Polish UI/UX
  - Smooth animations
  - Loading states
  - Error messages
  - Empty states

**Testing:**
- [ ] Write E2E test: login → see tasks → override priority
- [ ] Test drag-and-drop across different browsers
- [ ] Mobile responsiveness check

**Deliverables:**
- ✅ Can manually adjust task priorities
- ✅ Can move tasks between quadrants
- ✅ Override feedback is collected
- ✅ UI feels polished

**Time Investment:** 10-12 hours

**Phase 1 Checkpoint:** 
- Can you manage your entire TickTick task list through Context?
- Does the LLM make reasonable decisions most of the time?
- Is the UI pleasant to use for 30+ minutes?

**Demo Video:** Record 2-minute walkthrough for feedback

---

## Phase 2: Integrations (Weeks 5-8)

### Week 5: Workload Intelligence

**Goal:** Track capacity and warn about overcommitment

**Backend Tasks:**
- [ ] Create CapacityReport model
- [ ] Implement workload calculation logic
  - hours_scheduled vs hours_available
  - risk level determination
- [ ] Implement work intensity calculation
  - Q1 task count factor
  - Complexity factor
  - Consecutive days factor
- [ ] Implement rest score calculation
- [ ] API endpoint: GET /api/analytics/workload
- [ ] Celery job: update_workload (every hour)
- [ ] Cache workload data (Redis, 10 min TTL)

**Frontend Tasks:**
- [ ] Build WorkloadAnalytics page
- [ ] Create capacity trend chart (recharts)
- [ ] Create time-by-quadrant chart
- [ ] Add insights section
- [ ] Update WorkloadWidget with real data

**Deliverables:**
- ✅ Workload percentage is accurate
- ✅ Risk level updates in real-time
- ✅ Charts are readable and insightful

**Time Investment:** 8-10 hours

---

### Week 6: Rest Reminders

**Goal:** Proactively suggest breaks

**Backend Tasks:**
- [ ] Create RestReminder model
- [ ] Implement reminder trigger logic
  - Check consecutive work days
  - Check work intensity
  - Check rest score
- [ ] API endpoint: GET /api/analytics/rest-recommendation
- [ ] Celery job: check_rest_needs (daily at 9am)
- [ ] Generate suggestions with Claude
  - "Block Saturday as rest day"
  - "Take 2-hour break today"

**Frontend Tasks:**
- [ ] Create RestReminderBanner component
- [ ] Add calendar blocking feature
  - Create "Rest Day" event
  - Reschedule conflicting tasks
- [ ] Add dismiss logic (24hr cooldown)
- [ ] Track rest day compliance

**Deliverables:**
- ✅ Reminders appear when conditions met
- ✅ One-click rest day blocking works
- ✅ Reminders don't nag excessively

**Time Investment:** 6-8 hours

---

### Week 7: Contextual Email Drafts

**Goal:** Generate email drafts for tasks

**Backend Tasks:**
- [ ] Set up Gmail OAuth
  - Register app in Google Cloud Console
  - Add Gmail API scopes
- [ ] Create EmailDraft model
- [ ] Implement Gmail service
  - OAuth flow
  - Create draft in Gmail
  - Send email
- [ ] Create LLM email prompt (v1)
- [ ] Implement generate_email_draft() function
  - Extract task context
  - Determine recipient
  - Call Claude API
  - Return subject + body
- [ ] API endpoint: POST /api/email/draft/{task_id}
- [ ] API endpoint: POST /api/email/send
- [ ] Rate limiting: 10 drafts/hour per user

**Frontend Tasks:**
- [ ] Gmail OAuth consent screen
- [ ] Create EmailDraftModal component
  - Recipient field
  - Type selector (Update, Request, etc.)
  - Generated preview
  - Action buttons
- [ ] Add "Draft Email" button to TaskDetailModal
- [ ] Show generating loader
- [ ] Handle regeneration

**Deliverables:**
- ✅ Can generate email draft for any task
- ✅ Draft is contextually relevant
- ✅ One-click "Open in Gmail" works

**Time Investment:** 12-14 hours

---

### Week 8: Integration Testing & Refinement

**Goal:** Ensure Phase 2 features work well together

**Tasks:**
- [ ] E2E test suite for Phase 2
  - Workload warning triggers rest reminder
  - High workload prevents email drafts
  - Rest day blocks tasks properly
- [ ] Performance optimization
  - Reduce API calls
  - Optimize SQL queries
  - Cache more aggressively
- [ ] UI/UX improvements based on self-testing
  - Fix annoyances
  - Improve error messages
  - Better loading states
- [ ] Write user documentation
  - How to use workload intelligence
  - How to generate email drafts
  - FAQ section

**Deliverables:**
- ✅ All Phase 2 features work together
- ✅ No major bugs
- ✅ Performance is good

**Time Investment:** 8-10 hours

**Phase 2 Checkpoint:**
- Does workload intelligence help you avoid overcommitment?
- Do rest reminders actually make you take breaks?
- Are email drafts useful or just gimmicky?

---

## Phase 3: Advanced Automation (Weeks 9-10.5)

### Week 9: Azure DevOps Integration

**Goal:** Auto-create work items from tasks

**Backend Tasks:**
- [ ] Set up Azure DevOps authentication
  - Personal Access Token (PAT)
  - Store in environment variable
- [ ] Create AzureWorkItem model
- [ ] Implement Azure DevOps service
  - Create work item
  - Get work item
  - Update work item
- [ ] Map TickTick fields to Azure fields
- [ ] API endpoint: POST /api/azure/create-workitem
- [ ] Celery job: auto_create_azure_workitems
  - Trigger on "work" tag
  - Check user settings
- [ ] Store mapping in database

**Frontend Tasks:**
- [ ] Create AzureDevOpsSettings page
  - Toggle auto-create
  - Organization selector
  - Project selector
  - Work item type selector
  - Trigger tags multi-select
- [ ] Show Azure link on task cards
- [ ] Add "Create in Azure" button

**Deliverables:**
- ✅ Work items auto-create for tagged tasks
- ✅ Link back to task from Azure
- ✅ Configuration is intuitive

**Time Investment:** 12-14 hours

---

### Week 10: Weekly Planning + Voice Capture

**Goal:** Implement AI weekly reviews and voice notes

**Weekly Planning Tasks (6-7 hours):**
- [ ] Create WeeklyReview model
- [ ] Implement weekly analysis logic
  - Fetch last week's tasks
  - Calculate metrics
  - Call Claude for insights
- [ ] Create LLM weekly review prompt (v1)
- [ ] Celery job: generate_weekly_reviews (Sundays 6pm)
- [ ] API endpoint: GET /api/planning/weekly-review
- [ ] Frontend: WeeklyReviewModal component
  - Show summary
  - Top 3 priorities
  - Suggested schedule
  - Accept/Customize buttons

**Voice Capture Tasks (6-7 hours):**
- [ ] Set up Whisper API (OpenAI)
- [ ] Create voice capture endpoint: POST /api/voice/transcribe
- [ ] Implement transcription logic
- [ ] Implement task extraction from transcript
- [ ] Frontend: VoiceCapture component
  - Record button (hold to record)
  - Waveform animation
  - Processing state
  - Extracted tasks preview
  - Confirm & add to TickTick

**Deliverables:**
- ✅ Weekly review generates every Sunday
- ✅ Voice notes transcribe accurately
- ✅ Tasks extracted from voice correctly

**Time Investment:** 12-14 hours

---

### Week 10.5 (Final 2-3 days): Launch Prep

**Tasks:**
- [ ] Final bug fixes
- [ ] Performance tuning
- [ ] Security audit
  - Check for exposed API keys
  - Verify HTTPS everywhere
  - Test rate limiting
- [ ] Write comprehensive README
- [ ] Record demo video
- [ ] Deploy to production (Railway)
- [ ] Set up monitoring (Sentry)
- [ ] Configure backups
- [ ] Invite beta users

**Time Investment:** 6-8 hours

---

## Post-Launch (Weeks 11-12)

### Week 11: Beta Testing & Feedback

**Tasks:**
- [ ] Monitor error logs daily
- [ ] Collect user feedback
- [ ] Fix critical bugs
- [ ] Improve LLM prompts based on accuracy
- [ ] Optimize slow queries

### Week 12: Iteration

**Tasks:**
- [ ] Implement top 3 user requests
- [ ] Improve UX based on feedback
- [ ] Write blog post about building it
- [ ] Share on LinkedIn/Twitter

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| TickTick API changes | Low | High | Subscribe to developer updates, use versioned endpoints |
| Claude API downtime | Medium | High | Implement retry logic, fallback to queue for later |
| Scope creep | High | Medium | Stick to defined 9 features, park new ideas for v2 |
| LLM inaccuracy | Medium | High | Collect feedback, iterate on prompts, allow overrides |
| Running out of time | Medium | Medium | Cut voice capture if needed, focus on core value |

---

## Weekly Time Budget

```
Week  | Hours | Focus Area
------|-------|------------------------------------------
1     | 12-15 | Auth & foundation
2     | 15-18 | Task intake + LLM integration
3     | 12-15 | Dashboard & matrix
4     | 10-12 | Manual overrides + polish
5     | 8-10  | Workload intelligence
6     | 6-8   | Rest reminders
7     | 12-14 | Email drafts + Gmail
8     | 8-10  | Integration testing
9     | 12-14 | Azure DevOps
10    | 12-14 | Weekly planning + Voice
10.5  | 6-8   | Launch prep
------|-------|------------------------------------------
Total | 114-128 hours over 10.5 weeks
```

**Average:** 11-12 hours/week

---

## Success Criteria

**MVP is successful if:**
1. ✅ All 9 features work end-to-end
2. ✅ LLM accuracy ≥75% (based on user overrides)
3. ✅ You personally use it daily for 2+ weeks
4. ✅ Dashboard loads in <1 second
5. ✅ No critical bugs in production
6. ✅ 3+ beta users find it valuable

---

## Development Principles

### Iterate Fast
- Build feature → test → get feedback → improve
- Don't wait for perfection
- Ship MVP, then iterate

### Focus on Value
- Every feature must solve a real problem
- If a feature feels gimmicky, cut it
- Your own usage is the best test

### Keep It Simple
- Don't over-engineer
- Use existing libraries when possible
- Code for readability, not cleverness

### Fail Fast
- Test core assumptions early
- If LLM accuracy is <60%, pivot approach
- Don't be afraid to simplify

---

## When to Pivot

**Stop and reconsider if:**
- Week 2: LLM can't reliably classify tasks
- Week 4: Dashboard feels clunky after daily use
- Week 7: Email drafts take too long to generate
- Week 9: Azure integration is too complex

**Pivot options:**
- Simplify feature scope
- Use different approach (e.g., rule-based instead of LLM)
- Cut feature and add simpler alternative

---

## Celebration Milestones

- 🎉 Week 1: First successful login
- 🎉 Week 2: First task analyzed by Claude
- 🎉 Week 3: First time dragging tasks feels smooth
- 🎉 Week 4: Phase 1 complete! MVP works!
- 🎉 Week 7: First AI-generated email sent
- 🎉 Week 10.5: Production launch! 🚀

---

**Last Updated:** 2024-12-09

**Next Review:** After Week 2 (checkpoint on LLM accuracy)
