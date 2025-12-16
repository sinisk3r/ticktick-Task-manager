# Context - Vision & Master Plan

**Last Updated**: December 16, 2025
**Status**: Pre-launch (Alpha, targeting beta in Q1 2026)
**Founders**: Srikar + Co-founder

---

## The Vision (What We're Building)

### The Problem

You create tasks. They pile up. You forget them. They rot in your backlog.

**The deeper issue**: Productivity tools force everyone into the same workflow, but high-performers have fundamentally different cognitive styles. A Myers-Briggs "TJ" type needs crisp, structured tasks while an "FP" type gets overwhelmed by that rigidity—yet both need to execute 50+ tasks/week without burning out.

Motion optimizes your calendar. Reclaim protects your time. Sunsama asks you to reflect. **But none of them adapt to HOW YOUR BRAIN WORKS.**

### Our Solution

**Context is your AI work twin** that adapts to HOW you think, not just what you need to do.

It learns your personality-driven work style (structured vs. flexible, detail vs. big-picture) and translates tasks into YOUR language while protecting time for deep work and personal life.

- **For TJ types**: "Here's your Q1 priorities broken into 3 concrete milestones with dependencies"
- **For FP types**: "This week's theme is stakeholder alignment—here are the 2 big conversations to have"

### 3-Year North Star

> "I notice you're avoiding this ambiguous task—should we break it into 3 concrete steps like you prefer?"

> "This feels like too much structure—let's keep it high-level and trust your intuition."

**The assistant that knows you.** Not just your tasks—your patterns, your procrastination triggers, your energy cycles, your communication style. The more you use it, the more it becomes YOUR system.

---

## Who We're Building For

### Extreme User Profile (Srikar)

- Product Manager at large Indian corporate
- 50+ tasks/week across 3 parallel projects (product roadmaps, stakeholder management, technical coordination)
- "Vibe coder" building side projects nights/weekends
- Juggles work travel, family obligations, social life
- **Core pain**: Creates tasks with good intentions, life gets busy, they disappear into the void
- **Pattern**: Avoids ambiguous tasks ("Research competitor X") but crushes concrete ones ("Draft 3-slide pitch for stakeholder Y")

**What Srikar wants**: An assistant that flags "Hey, you created this task 3 weeks ago and haven't touched it—too vague? Let me break it down for you."

### Target ICP (Initial)

**Who**: Product managers, startup founders, consultants managing 50+ tasks/week

**Pain**: They've tried Motion/Reclaim/Sunsama but found them too rigid or impersonal
- Motion's auto-scheduling doesn't understand their work style
- Reclaim just blocks calendar time but doesn't help with prioritization
- Sunsama's daily ritual feels like homework

**Need**: AI that adapts to their cognitive style, not another one-size-fits-all system

**Market size**:
- **TAM**: $2.3B productivity software market (Statista 2024)
- **SAM**: 2M knowledge workers using premium task managers (Motion: 10K users, Reclaim: 50K)
- **SOM**: 1K users by year-end (0.05% of SAM) = $60K ARR at $5-15/mo

### Launch Audience (Beta)

**9,000 ISB (Indian School of Business) alumni network**

Why ISB?
- Business-savvy, productivity-focused professionals
- High task volume (consultants, founders, executives)
- Built-in trust (Srikar is ISB alum)
- Word-of-mouth amplification potential
- Can validate product-market fit before going broad

**Initial reach**: 20 warm contacts → 10 committed beta users → expand to 100 if retention holds

---

## What Makes Context Different (Moats)

### 1. Personality Adaptation Engine

**The core insight**: Task management isn't a calendar problem—it's a psychology problem.

Context learns your cognitive patterns over time:
- **Myers-Briggs type detection** from task patterns (how you phrase tasks, which ones you avoid, when you procrastinate)
- **Work style preferences** (morning deep work vs. afternoon meetings, solo vs. collaborative)
- **Decision-making heuristics** (data-driven vs. intuition-led, deadline-driven vs. quality-driven)

**Switching costs**: The longer you use Context, the more it becomes YOUR system. Leaving means losing your "AI work twin" and starting over.

**Competitors can't copy this easily**: Requires longitudinal data, sophisticated LLM prompting, and deep product iteration—not just a feature flag.

### 2. TickTick Integration Depth

**Strategic leverage**:
- Bi-directional sync (Context ↔ TickTick)
- Piggyback on TickTick's existing user base and storage infrastructure
- Users don't need to migrate—Context sits on top of their existing system
- Can drop dependency later if needed (already storing tasks in PostgreSQL)

**Why this matters**: Lower friction to adoption. "Try Context for a week, keep using TickTick" is easier than "migrate all your tasks to a new system."

### 3. Wellbeing Focus (Not Just Efficiency)

**Most productivity tools optimize for MORE**: More tasks done, more meetings scheduled, more notifications.

**Context optimizes for SUSTAINABLE productivity**:
- Spots avoided tasks and suggests breakdowns
- Protects deep work time from calendar creep
- Detects burnout patterns ("You've worked 3 weekends in a row—let's reschedule")
- Encourages "important but not urgent" tasks that grow your career

**The message**: "I help you get the RIGHT things done without burning out." This resonates with burned-out knowledge workers.

### 4. Open Architecture (Privacy-First)

**Multi-LLM support**:
- OpenRouter free/cheap models (DeepSeek) for free tier
- Claude/GPT for premium tier
- Can use local Ollama models for privacy-conscious users

**Why this matters**:
- Privacy control (your tasks don't need to go to OpenAI)
- Cost control (can switch to cheaper models anytime)
- Future-proof (not locked to one LLM provider)
- Appeals to technical/privacy-conscious users

---

## The MVP (Q1 2026 Sprint)

### Core Feature: Conversational Agent

**The ONE thing that must work**: Natural language task management

- "Create task: Draft Q2 roadmap for stakeholder review"
- "What's urgent today?"
- "Mark 'Email CFO re: budget' as done"
- **Key insight**: "You created this task 3 weeks ago and haven't touched it—too vague? Let me break it into 3 steps for you."

**Why conversation matters**:
- Lower friction than UI forms
- Feels like talking to an assistant, not a database
- Enables personality adaptation (TJ types write structured tasks, FP types write fuzzy ones)

### What's IN V1

✅ **Conversational task CRUD**
- Create, list, complete, delete tasks via chat
- TickTick bi-directional sync
- SSE streaming for real-time responses

✅ **Eisenhower Matrix auto-classification**
- AI analyzes urgency/importance scores
- Q1 (Urgent & Important), Q2 (Not Urgent, Important), Q3 (Urgent, Not Important), Q4 (Neither)
- Drag-and-drop to manually override

✅ **Basic personality insight**
- Avoidance detection: "You haven't touched this task in 3 weeks"
- Task breakdown suggestions: "Too vague? Let me split this into concrete steps"
- Work style inference from task patterns

✅ **Mobile-friendly UI**
- Responsive web app (not native app yet)
- Works on phone browser for task capture on-the-go

✅ **Multi-LLM support**
- OpenRouter (DeepSeek free tier)
- Claude/GPT for premium users
- Configurable via UI (no code changes needed)

### What's OUT (V2+)

❌ **Email drafting** (too complex, low trust for V1)
❌ **Calendar blocking** (Motion/Reclaim already do this well)
❌ **Full Myers-Briggs detection** (need more data first)
❌ **Mobile native app** (web-first for speed)
❌ **Team collaboration** (single-player for now)
❌ **Time tracking** (out of scope)

### The "Aha!" Moment

> "When Context automatically flagged that 'important but not urgent' project I'd been avoiding for 3 weeks—and suggested breaking it into the specific, structured steps I prefer—I actually started it. That's never happened with any other tool."

**Success = users feel SEEN, not just SCHEDULED.**

---

## Business Model

### Pricing (Freemium)

**Free Tier**:
- Basic conversational agent
- TickTick sync
- Eisenhower Matrix
- OpenRouter free models (DeepSeek, Llama)
- **Goal**: Get users hooked, collect personality data

**Indie Tier ($5/mo)**:
- Better models (DeepSeek paid, Claude Haiku)
- More insights (weekly avoidance reports, work style analysis)
- Priority support
- **Target**: Solo founders, indie hackers, consultants

**Pro Tier ($15/mo)**:
- SOTA models (Claude Sonnet/Opus, GPT-4)
- Advanced personality features (full Myers-Briggs, energy cycle detection)
- API access for power users
- **Target**: PMs at tech companies, executives, high-volume users

### Unit Economics (Estimate)

| Tier | LLM Cost/User/Month | Pricing | Margin |
|------|---------------------|---------|--------|
| Free | $0 (free models) | $0 | N/A (lead gen) |
| Indie | $0.10-0.50 | $5 | 90-97% |
| Pro | $2-5 | $15 | 67-75% |

**Break-even target**: ~100 paid users ($500-1500 MRR)

**Assumptions**:
- Average user: 50 tasks/week, 10 chat messages/week
- DeepSeek: ~$0.0001/message
- Claude Haiku: ~$0.001/message
- Claude Sonnet: ~$0.01/message

**Why freemium works**:
- LLM costs are low enough to give away free tier
- Free users provide data to improve personality models
- Conversion happens when users feel the "switching cost" of losing their AI twin

### Value Proposition (Quantified)

**Time savings**:
- 1-2 hours/week on planning (for over-planners)
- Encourages 30 min/week of planning for those who don't plan

**Decision fatigue reduction**:
- 40% fewer "what should I work on now?" moments
- AI pre-triages "urgent vs. important"

**Task completion boost**:
- 25% more "important but not urgent" tasks completed
- These are the career-growth tasks (learning new skills, networking, strategic projects)

**Wellbeing**:
- Fewer weekend work sessions
- More guilt-free downtime

**Target customer ROI**: If you make $100K/year ($50/hr), saving 1 hour/week = $200/mo value. $15/mo is 7.5% of that value—easy justify.

---

## 30-Day Launch Plan

### Week 1: Customer Discovery (Dec 16-22)

**Goal**: Validate assumptions about Motion/Reclaim, collect beta signups

- [ ] Sign up for Motion free trial
- [ ] Sign up for Reclaim.ai free trial
- [ ] Use each for 2 days (document pros/cons in `docs/competitor_analysis.md`)
- [ ] Draft ISB alumni pitch message (see template below)
- [ ] Send to 20 warm contacts (ISB classmates, LinkedIn connections)
- [ ] Interview 5 respondents (30 min each, pay $25 Amazon gift card)

**Interview questions**:
1. Walk me through your current task management system
2. What have you tried? (Motion, Reclaim, Sunsama, Notion, etc.)
3. What worked? What didn't?
4. Show me a task you've been avoiding—why?
5. How do you decide what to work on each day?

**Deliverable**:
- Competitor analysis doc
- 5 interview notes
- 10 committed beta users (50% conversion)

**Beta pitch template**:
> Hey [Name],
>
> I'm building an AI task manager that adapts to your work style (think: "AI work twin" that knows you prefer structured tasks vs. big-picture guidance).
>
> I'm looking for 10 beta users from ISB to test it in January. You'd get:
> - Free forever access
> - Direct input on features
> - Your tasks analyzed by AI to spot avoidance patterns
>
> Would you be interested? I'll send access in early Jan.
>
> - Srikar

### Week 2-3: MVP Build (Dec 23 - Jan 5)

**Goal**: Working conversational agent that Srikar uses daily

**Sprint backlog**:
- [ ] **Conversational task creation**: "Create task: X" → TickTick sync
- [ ] **Task listing with filters**: "What's urgent today?" → Q1 tasks
- [ ] **Task completion**: "Mark X done" → Updates TickTick
- [ ] **Avoidance detection**: Flag tasks untouched for 2+ weeks
- [ ] **Breakdown suggestions**: "Too vague? Here are 3 concrete steps"
- [ ] **Polish UX**: Mobile-friendly chat, Eisenhower Matrix drag-drop

**Technical priorities**:
1. Agent tool calling (create/list/complete tasks)
2. SSE streaming (real-time chat)
3. Personality inference (simple heuristics: task phrasing, avoidance patterns)
4. TickTick bi-directional sync

**Deliverable**:
- Srikar uses Context daily instead of just TickTick
- Can demo to beta users in 5 minutes
- No critical bugs

### Week 4: Beta Launch (Jan 6-12)

**Goal**: 10 active beta users

**Launch checklist**:
- [ ] Fix critical bugs from Srikar's dogfooding
- [ ] Send beta access emails (with onboarding video)
- [ ] Set up retention tracking (Day 2, Day 7, Day 14)
- [ ] Create feedback form (Google Form or Typeform)
- [ ] Schedule 30-min feedback calls with 5 users (end of Week 1)

**Onboarding flow**:
1. Email: "Your Context beta access is ready"
2. Connect TickTick account (OAuth)
3. Chat tutorial: "Try saying 'What's urgent today?'"
4. First insight: "I noticed you have 12 tasks—let me classify them"

**Success metrics**:
- 10/10 users complete onboarding (connect TickTick)
- 7/10 users active on Day 2 (send ≥1 chat message)
- 6/10 users active on Day 7 (60% week-1 retention)

**Deliverable**:
- 10 active beta users
- 5 feedback call notes
- Prioritized V1.1 backlog based on feedback

### Week 5-6: Iterate (Jan 13-26)

**Goal**: Decide if we have product-market fit

**Retention target**:
- Week 2: 60% retained (6/10 users)
- Week 3: 50% retained (5/10 users)

**Decision tree**:

**If retention GOOD (≥50% at Week 2)**:
- Add most-requested feature (likely: email drafts or calendar sync)
- Expand beta to 50 users (send to broader ISB network)
- Start building paid tier infrastructure

**If retention OKAY (30-50% at Week 2)**:
- More interviews (why did 50% churn?)
- A/B test messaging (is "AI work twin" resonating?)
- Focus on 1 core use case (e.g., "task avoidance therapy")

**If retention BAD (<30% at Week 2)**:
- Pivot or kill
- Interview churned users: "Why did you stop using it?"
- Consider: Wrong ICP? Wrong feature? Wrong positioning?

**Deliverable**:
- Retention report (cohort analysis)
- Decision: Scale, iterate, or pivot

---

## Success Metrics

### Primary Metric: Retention

**Why retention?** Because if users don't come back, nothing else matters.

**Targets**:
- **Day 2**: 70% (7/10 users come back next day)
- **Week 2**: 60% (6/10 users still active)
- **Week 4**: 50% (5/10 users still active)
- **Month 3**: 40% (4/10 users still active)

**Benchmark**:
- Motion/Reclaim likely have 30-40% month-1 retention (productivity tools churn hard)
- We need to beat 50% because of personality lock-in

### Secondary Metrics

**Engagement**:
- Tasks analyzed per user per week (target: 20+)
- Chat messages per user per week (target: 10+)
- High engagement = users are forming habits

**Value delivered**:
- "Avoided tasks" completed (target: 2-3 per user per week)
- This is the core value prop—did we actually help them do hard things?

**Word-of-mouth potential**:
- NPS from beta users (target: 50+)
- "Would you recommend Context to a friend/colleague?"
- ≥50 NPS = strong word-of-mouth potential

### Vanity Metrics (Ignore for Now)

❌ Total users (doesn't matter if they churn)
❌ Social media followers (low signal)
❌ Press coverage (vanity, not validation)
❌ Website visits (unless converting to signups)

**Focus ruthlessly on retention and NPS.**

---

## Risks & Mitigation

### Risk 1: TickTick Adds AI Features

**Likelihood**: Medium (they already have basic AI for smart date parsing)
**Impact**: High (undercuts our moat—why use Context if TickTick does it?)
**Mitigation**:
- Build standalone capability (already storing tasks in PostgreSQL—can drop TickTick if needed)
- Focus on personality adaptation (TickTick won't do this—too niche for their mass market)
- Move fast (ship beta before they add more AI)
- Differentiate on "AI work twin" positioning, not just "smart task manager"

**Contingency plan**: If TickTick adds personality features, pivot to vertical (e.g., "Context for PMs" with Jira/Asana integration instead)

### Risk 2: LLM Costs Kill Margins

**Likelihood**: Low (OpenRouter free models exist)
**Impact**: Medium (can't scale profitably—become VC-dependent)
**Mitigation**:
- Default to cheap OpenRouter models (DeepSeek: ~$0.0001/message)
- Premium users pay for SOTA models (Claude/GPT)
- Monitor per-user costs obsessively (set up CloudWatch alerts)
- Optimize prompts (shorter context = lower cost)

**Break-even math**:
- At $0.50/user/month LLM cost, need $5/mo pricing to maintain 90% margin
- If costs spike to $2/user/month, raise Pro tier to $20/mo

**Worst case**: If LLM costs become unsustainable, offer "bring your own API key" option (users pay OpenAI/Anthropic directly)

### Risk 3: Can't Get Beta Users

**Likelihood**: Low (ISB network is warm, Srikar has direct access)
**Impact**: High (no feedback loop, can't iterate, building in vacuum)
**Mitigation**:
- Send personal emails (not mass blast—higher response rate)
- Offer "free forever" for first 100 users (even when paid tier launches)
- Leverage co-founder's network too
- Pay for interviews ($25 Amazon gift card per 30 min)

**Backup plan**: If ISB network doesn't respond, try:
- Product Hunt "Ship" page (collect waitlist)
- Reddit (r/productivity, r/ADHD, r/GetStudying)
- Indie Hackers community
- Twitter/X audience building

### Risk 4: Feature Creep (Trying to Build Too Much)

**Likelihood**: HIGH (Srikar wants email drafts, calendar sync, full Myers-Briggs, etc.)
**Impact**: High (miss Q1 deadline, burn out, never ship)
**Mitigation**:
- **Ruthless prioritization**: Agent CRUD + ONE insight (avoidance detection)
- Ship ugly but working (no pixel-perfect UI for V1)
- V2 features go in backlog, NOT V1
- Weekly "scope creep check" (co-founder holds Srikar accountable)

**Rule**: If feature takes >3 days to build, it's V2

**Mantra**: "Perfect is the enemy of shipped."

### Risk 5: Solo Founder Burnout

**Likelihood**: Medium (Srikar has day job, building nights/weekends)
**Impact**: High (project dies, momentum lost)
**Mitigation**:
- Co-founder helps share load (who does what? needs clarity)
- Set realistic hours (15-20 hrs/week, not 40)
- Take 1 day/week completely off (no Context work)
- If falling behind schedule, extend to 6-8 weeks (don't cut quality)

**Red flags**:
- Dreading working on Context
- Skipping weekends to catch up
- Fighting with co-founder over scope

**Quit criteria**: If Srikar stops using Context himself for 2 weeks, pause and re-evaluate

---

## Team & Resources

### Founders

**Srikar**:
- Role: Product + Full-stack dev
- Background: PM at large Indian corporate, vibe coder
- Time commitment: 15-20 hrs/week (nights/weekends)
- Strengths: Product sense, user empathy, rapid prototyping
- Weaknesses: Scaling/ops experience, can over-engineer

**Co-founder**:
- Role: [TBD - Technical or Marketing/GTM?]
- Time commitment: [TBD]
- Strengths: [TBD]
- Weaknesses: [TBD]

**Division of labor** (needs alignment):
- Who owns frontend? Backend? Ops?
- Who manages beta user outreach?
- Who does customer interviews?
- Who writes content/docs?

**Communication cadence**:
- Daily async updates (Slack/Discord)
- Weekly sync call (30 min, Sundays)
- Monthly retrospective (what's working, what's not)

### Time Commitment

**Q1 Sprint (4-6 weeks)**:
- Srikar: 15-20 hrs/week
- Co-founder: [TBD] hrs/week
- Mostly nights/weekends
- Day jobs continue (can't quit yet)

**Post-beta (Q2-Q3)**:
- If retention good: Consider going full-time
- If retention bad: Keep as side project or sunset

### Tech Stack

**Backend**:
- FastAPI (Python 3.11+)
- PostgreSQL 15+ (SQLAlchemy 2.0 async)
- Redis 7 (caching, Celery)
- LangGraph (agent orchestration)
- OpenRouter / Anthropic / OpenAI (LLMs)

**Frontend**:
- Next.js 14 (App Router, TypeScript)
- Tailwind CSS + shadcn/ui
- SSE for real-time chat

**Infra**:
- Railway (backend hosting)
- Vercel (frontend hosting)
- Docker Compose (local dev)

**Why this stack**:
- Fast iteration (no microservices complexity)
- Cheap hosting ($20-50/mo)
- Srikar already knows it
- Can scale to 1K users before re-architecting

### Funding

**Current**: Bootstrapped (no outside capital)

**Costs**:
- LLM: $0-50/mo (free tier initially)
- Hosting: $20-50/mo (Railway + Vercel)
- Tools: $0-20/mo (GitHub, Figma, etc.)
- **Total**: <$100/mo burn

**Runway**: Infinite (side project, funded by day jobs)

**Fundraising plan**:
- Don't raise until product-market fit (60%+ retention, 10+ paying customers)
- If traction good: Consider angel round ($50-100K) to quit day jobs
- If traction REALLY good: YC application (S26 batch, deadline March 2026)

**Philosophy**: Stay lean, don't give away equity until absolutely necessary.

---

## What Success Looks Like

### 1 Month (End of Jan 2026)

- ✅ Srikar uses Context daily (prefers it over TickTick alone)
- ✅ 10 beta users, 60% retained at Week 2 (6/10)
- ✅ 5 users say "I can't go back to my old system" (strong signal)
- ✅ First "aha moment" story (user completes avoided task after Context breakdown)

**Evidence of traction**: Users texting Srikar unsolicited feedback ("Dude, Context just called out a task I've been avoiding for a month—how did it know?")

### 3 Months (End of March 2026)

- ✅ 100 beta users (expanded from ISB network)
- ✅ 50% retained at Month 2 (50/100)
- ✅ NPS > 50 (strong word-of-mouth)
- ✅ First paying customer (even if just $5/mo—validates willingness to pay)
- ✅ 10+ "power users" (using daily, >50 tasks/week analyzed)

**Qualitative signal**: Users posting about Context on Twitter/LinkedIn without being asked

### 6 Months (Mid-2026) - The Vision

> "People speak about how they're getting more done, and worry less. They feel the app knows them, and even does some tasks for them—like research, draft emails. When they wake up, they know what to focus on for the day!"

- ✅ 500 users (mix of free + paid)
- ✅ $2K MRR (monthly recurring revenue)
- ✅ 40% Month-3 retention (sustained engagement)
- ✅ Personality features working (users notice Context adapting to their style)
- ✅ First case study (PM at tech company: "Context helped me ship 2 projects I'd been avoiding")

**Inflection point**: Organic growth (users inviting colleagues without prompting)

### 1 Year (End of 2026)

- ✅ 1,000 DAU (daily active users)
- ✅ $10K MRR
- ✅ Srikar quits day job to work on Context full-time
- ✅ Expanding beyond ISB network (Product Hunt launch, influencer partnerships)
- ✅ V2 features shipping (calendar sync, email drafts, mobile app)

**Narrative**: "The AI task manager that actually knows you" is resonating beyond early adopters

---

## Quit Criteria (Honesty Check)

**Srikar will quit if**:

1. **He stops using it himself** (1 month of not using Context)
   - If it doesn't solve his own problem, it won't solve others'

2. **Retention never improves** (3 months of <30% Week-2 retention)
   - Users trying it once and never coming back = no PMF

3. **He loses interest in the problem**
   - If building Context feels like a chore, not a passion project

4. **Co-founder drops out** (and Srikar can't carry it alone)
   - Solo founder risk is real

**BUT**: Even if only Srikar uses it long-term, it's still success (solved his own problem, learned a ton, built portfolio project)

**Sunk cost fallacy guard**: Every month, ask "If I were starting from scratch today, would I build this?" If answer is no 3 months in a row → quit.

---

## Next Actions (Start Today)

### This Week (Dec 16-22)

1. [ ] **Sign up for Motion** (free trial)
2. [ ] **Sign up for Reclaim.ai** (free account)
3. [ ] **Use each for 2 days** (document pros/cons in `docs/competitor_analysis.md`)
4. [ ] **Draft ISB alumni pitch message** (use template above, personalize for each recipient)
5. [ ] **Send to 20 warm contacts** (aim for 10 beta signups)
6. [ ] **Start building conversational agent** (task CRUD via chat)

### This Month (Dec 16 - Jan 12)

7. [ ] **Interview 5 beta users** (30 min each, $25 gift card)
8. [ ] **Build MVP** (agent + Eisenhower Matrix + TickTick sync)
9. [ ] **Dogfood daily** (Srikar uses Context for all task management)
10. [ ] **Launch to 10 beta users** (Jan 6-12)
11. [ ] **Collect feedback** (surveys + calls)
12. [ ] **Measure Week-2 retention** (target: 60%)

**First milestone**: 5 beta signups + working agent prototype (by Dec 22)

**First validation point**: 6/10 users still active after 2 weeks (by Jan 20)

---

## Appendix: Key Decisions Made

### Why Freemium (Not Paid-Only)?

- Lower barrier to entry (users try before committing)
- Free tier provides data to train personality models
- Premium features (SOTA models, advanced insights) justify upgrade
- LLM costs low enough to sustain free tier

### Why TickTick (Not Build from Scratch)?

- Users already have tasks there (no migration friction)
- Leverage their storage/sync infrastructure
- Can drop dependency later if needed
- Focus on AI layer, not task DB plumbing

### Why Conversation-First (Not UI Forms)?

- Feels more natural ("talk to assistant" vs. "fill form")
- Enables personality inference (how users phrase tasks)
- Lower friction (faster to say "Create task: X" than click through UI)
- Differentiates from Motion/Reclaim (UI-heavy)

### Why ISB Network First (Not Product Hunt)?

- Warm intros (higher response rate)
- Homogeneous ICP (easier to validate PMF)
- Built-in trust (Srikar is alum)
- Can iterate privately before public launch

### Why Q1 2026 (Not "Launch Fast")?

- Srikar has day job (can't sprint full-time)
- Need time for customer discovery (Motion/Reclaim testing)
- Want working MVP, not half-baked prototype
- 4-6 weeks is aggressive but realistic

---

## Revision History

| Date | Change | Reason |
|------|--------|--------|
| Dec 16, 2025 | Initial version | Synthesized strategy questionnaire answers |

---

*This is a living document. Update as assumptions change, features ship, and users give feedback. Re-read monthly to stay aligned with the vision.*

**Next review date**: January 15, 2026 (after beta launch)
