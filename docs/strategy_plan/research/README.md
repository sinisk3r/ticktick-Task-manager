# Market Research Hub - Navigator

**Last Updated**: December 16, 2025
**Owner**: Srikar + Co-founder
**Purpose**: Central guide for all market research, customer discovery, and validation activities

---

## What This Folder Contains

This is the **research repository** for Context. All customer insights, competitor analysis, beta testing data, and validation metrics live here.

**Use this folder to**:
- Track what you're learning about users and competitors
- Document customer interviews and feedback
- Monitor beta testing progress and retention
- Make data-driven decisions about product direction

**Don't use this folder for**:
- Feature specifications (those go in `/docs/FEATURES.md`)
- Technical architecture (those go in `/docs/ARCHITECTURE.md`)
- Marketing content (those go in `/docs/strategy_plan/gtm/`)

---

## Folder Structure

```
research/
├── README.md                          # This file (navigator)
├── beta_pitch_v1.md                   # Beta user outreach messages (3 versions)
├── competitor_analysis.md             # Motion, Reclaim, Sunsama deep dives
├── competitor_notes.md                # Firsthand testing notes
├── customer_interviews/               # Interview notes and insights
│   ├── interview_template.md          # Standard interview script
│   ├── interview_001_john_doe.md      # Individual interview notes
│   └── synthesis.md                   # Cross-interview patterns
├── beta_testing/                      # Beta cohort tracking
│   ├── cohort_tracker.md              # User retention and engagement
│   ├── feedback_log.md                # Bug reports and feature requests
│   └── nps_survey_results.md          # Net Promoter Score data
└── metrics/                           # Analytics and KPIs
    ├── retention_analysis.md          # Day 2, Week 2, Month 1 retention
    ├── engagement_metrics.md          # Tasks analyzed, chat messages, etc.
    └── value_delivered.md             # "Avoided tasks" completed, etc.
```

---

## Core Research Files

### 1. `beta_pitch_v1.md`
**Purpose**: Outreach messages for recruiting ISB alumni as beta users

**What's inside**:
- Version A: Short email (3 sentences)
- Version B: LinkedIn DM (casual, 2 paragraphs)
- Version C: WhatsApp message (very casual, bullet points)

**When to update**:
- After first 20 outreach attempts (analyze response rates)
- When conversion drops below 30% (messaging not resonating)
- After beta signups hit 10 (create V2 for broader audience)

**How to use**:
- Copy/paste Version A/B/C based on relationship with contact
- Track which version has highest conversion in `beta_testing/cohort_tracker.md`
- A/B test messaging if response rate is low

**Common pitfall**: Sending same generic message to everyone. Personalize based on relationship (WhatsApp for close friends, LinkedIn for acquaintances).

---

### 2. `competitor_analysis.md`
**Purpose**: Deep dive on Motion, Reclaim.ai, Sunsama, and other task managers

**When to update**:
- During customer discovery (Week 1: Dec 16-22)
- When competitor ships new features (check their changelogs monthly)
- When beta users mention switching from competitor (capture why they left)

**How to use**:
- Sign up for free trials (Motion, Reclaim, Sunsama)
- Use each for 2-3 days as a real user
- Document: What works? What doesn't? Where's the gap Context can fill?
- Reference during feature prioritization ("We don't need calendar blocking - Reclaim already does this well")

**Common pitfall**: Copying competitors instead of differentiating. The goal isn't to build "Motion clone with AI" - it's to find what Motion/Reclaim DON'T do (personality adaptation).

**Template structure**:
```markdown
# Competitor Analysis: [Tool Name]

## Overview
- Pricing: [Free/Paid tiers]
- Core feature: [What's their main value prop?]
- Target user: [Who is this for?]

## Strengths (What they do well)
- [Feature 1]: Why users love it
- [Feature 2]: Why users love it

## Weaknesses (What users complain about)
- [Gap 1]: Reddit/Twitter complaints
- [Gap 2]: Reddit/Twitter complaints

## Context's Differentiation
- We do [X] better because [reason]
- We don't need [Y] because [competitor already does it]

## User migration opportunity
- Why would someone switch from [Tool] to Context?
- What's the "aha moment" that makes them leave?
```

---

### 3. `customer_interviews/` Folder
**Purpose**: Capture user pain points, work styles, and feature requests through 30-min interviews

**When to create**:
- Week 1 (Dec 16-22): 5 interviews before building MVP
- Week 4 (Jan 6-12): 5 interviews after beta launch
- Ongoing: Any time a user has interesting feedback (ask for 15-min call)

**How to use**:
- Use `interview_template.md` for consistency
- Create one file per interview: `interview_001_john_doe.md`
- After 5 interviews, synthesize patterns in `synthesis.md`
- Look for: Repeated pain points, unexpected use cases, feature requests

**Common pitfall**: Asking leading questions ("Would you like an AI that adapts to your work style?"). Instead, ask open-ended: "Walk me through your current task management system."

**Interview script** (`interview_template.md`):
```markdown
# Customer Interview Template

**Date**: [YYYY-MM-DD]
**Interviewee**: [Name, Role, Company]
**Duration**: 30 minutes
**Incentive**: $25 Amazon gift card

## Pre-Interview Prep
- Review their signup form answers
- Check their current task manager (Motion, TickTick, Notion?)
- Prepare 1-2 personalized questions

## Interview Questions (30 min)

**Section 1: Current System (10 min)**
1. Walk me through how you manage tasks today. Show me your screen if possible.
2. What tools do you use? (Motion, Reclaim, TickTick, Notion, pen & paper?)
3. What do you like about your current system?
4. What frustrates you?

**Section 2: Pain Points (10 min)**
5. Show me a task you've been avoiding. Why haven't you done it?
6. How do you decide what to work on each day?
7. Have you tried other task managers? (Motion, Reclaim, Sunsama?) What didn't work?
8. If you could wave a magic wand and fix ONE thing about task management, what would it be?

**Section 3: Context Pitch (5 min)**
9. [Demo Context briefly - 2 min]
10. What's your first reaction?
11. Would you use this? Why or why not?

**Section 4: Follow-Up (5 min)**
12. If I built this, would you pay $5-15/mo for it?
13. What feature would make this a "must-have" vs. "nice-to-have"?
14. Anyone else I should talk to? (referrals)

## Post-Interview Notes
- Key insights:
- Surprising quotes:
- Feature requests:
- Follow-up actions:
```

**Synthesis process** (`synthesis.md`):
- After 5 interviews, create summary doc
- Look for patterns: What did 3+ people say?
- Prioritize features based on frequency + intensity of pain
- Update product roadmap based on insights

---

### 4. `beta_testing/cohort_tracker.md`
**Purpose**: Monitor beta user retention, engagement, and feedback

**When to update**:
- Daily during beta launch week (Jan 6-12)
- Weekly during beta period (Jan 13 - Feb 28)
- After key milestones (Day 2, Week 2, Month 1)

**How to use**:
- Track each user's onboarding, engagement, and retention
- Flag churned users for follow-up interviews ("Why did you stop using it?")
- Celebrate wins (users who become power users)

**Common pitfall**: Only tracking vanity metrics (total signups). Focus on retention and engagement, not just activation.

**Template structure**:
```markdown
# Beta Cohort Tracker

## Cohort 1 (Jan 6-12, 2026) - 10 Users

| User | Signup Date | Onboarded | Day 2 | Week 2 | Month 1 | Status | Notes |
|------|-------------|-----------|-------|--------|---------|--------|-------|
| John Doe | Jan 6 | ✅ | ✅ | ✅ | ✅ | Active | Power user, 50+ tasks/week |
| Jane Smith | Jan 7 | ✅ | ✅ | ❌ | - | Churned | Follow up: why stopped? |
| ... | ... | ... | ... | ... | ... | ... | ... |

**Retention Metrics**:
- Onboarding: 10/10 (100%)
- Day 2: 7/10 (70%) ✅ Target: 70%
- Week 2: 6/10 (60%) ✅ Target: 60%
- Month 1: TBD (Target: 50%)

**Engagement Metrics** (Week 1 average):
- Tasks analyzed per user: 23 (target: 20+)
- Chat messages per user: 12 (target: 10+)
- "Avoided tasks" completed: 2.3 (target: 2-3)

**Top Feature Requests**:
1. Calendar sync (5 users)
2. Email drafting (3 users)
3. Mobile app (2 users)

**Churn Reasons** (from follow-up calls):
1. Jane Smith: "Too much setup friction, couldn't connect TickTick"
2. ...
```

---

### 5. `metrics/retention_analysis.md`
**Purpose**: Deep dive on retention cohorts and patterns

**When to update**:
- Weekly during beta (track Day 2, Week 2 retention)
- Monthly post-beta (track Month 1, Month 2, Month 3 retention)
- After major feature launches (did retention improve?)

**How to use**:
- Cohort analysis: Compare Cohort 1 vs. Cohort 2 retention
- Identify drop-off points: "50% churn between Day 3-7 - why?"
- A/B test retention tactics (e.g., email reminders, onboarding tweaks)

**Common pitfall**: Blaming product quality for churn without investigating root cause. Always follow up with churned users.

**Template structure**:
```markdown
# Retention Analysis

## Cohort 1 (Jan 6-12, 2026)

**Retention Curve**:
- Day 0 (signup): 10 users (100%)
- Day 1: 9 users (90%)
- Day 2: 7 users (70%) ✅
- Day 7: 6 users (60%) ✅
- Day 14: 5 users (50%) ⚠️ (target: 60%)
- Day 30: TBD (target: 40%)

**Drop-off Analysis**:
- 1 user churned Day 0-1: Why? (follow up)
- 2 users churned Day 2-7: Why? (follow up)
- 1 user churned Day 7-14: Why? (follow up)

**Churn Reasons**:
1. Setup friction (TickTick OAuth failed) - 1 user
2. "Didn't see value" - 1 user (need better onboarding)
3. "Too busy to test" - 1 user (timing issue, not product)

**Retained User Patterns** (What do power users have in common?):
- All connected TickTick successfully
- All sent 10+ chat messages in Week 1
- All had "aha moment" (avoided task completed) by Day 5

**Retention Improvement Tactics**:
- Fix TickTick OAuth (technical issue)
- Add onboarding tutorial (show value faster)
- Send Day 3 reminder email ("Try asking 'What's urgent today?'")
```

---

### 6. `metrics/engagement_metrics.md`
**Purpose**: Track how users interact with Context (tasks analyzed, chat messages, etc.)

**When to update**:
- Weekly during beta
- Monthly post-beta

**How to use**:
- Identify "power users" (top 10% engagement) - interview them for testimonials
- Identify "at-risk users" (low engagement, likely to churn) - send nudge emails
- Correlate engagement with retention: "Users who send 10+ chat messages in Week 1 have 80% Week 2 retention"

**Common pitfall**: Tracking vanity metrics (total tasks created) instead of value metrics (avoided tasks completed).

**Template structure**:
```markdown
# Engagement Metrics

## Week 1 (Jan 6-12, 2026)

**Average per user**:
- Tasks analyzed: 23 (target: 20+) ✅
- Chat messages sent: 12 (target: 10+) ✅
- "Avoided tasks" completed: 2.3 (target: 2-3) ✅
- Eisenhower Matrix interactions: 8 (drag-drop, quadrant changes)

**Power Users** (top 10%):
- John Doe: 67 tasks, 34 chat messages, 5 avoided tasks completed
- Sarah Lee: 52 tasks, 28 chat messages, 4 avoided tasks completed

**At-Risk Users** (bottom 10%):
- Jane Smith: 3 tasks, 1 chat message, 0 avoided tasks (churned Day 5)
- Bob Chen: 8 tasks, 2 chat messages, 0 avoided tasks (send nudge email)

**Correlation Analysis**:
- Users with 10+ chat messages in Week 1: 80% Week 2 retention
- Users with <5 chat messages in Week 1: 20% Week 2 retention
- **Insight**: Chat engagement predicts retention - focus on driving chat habit

**Engagement Drivers**:
- Onboarding tutorial completion: 9/10 users (90%)
- First "avoided task" flagged: 7/10 users (70%)
- First task breakdown suggestion: 6/10 users (60%)
```

---

## When to Update Research Files

### Daily (During Beta Launch Week)
- `beta_testing/cohort_tracker.md`: Track user onboarding and Day 2 retention

### Weekly (During Beta Period)
- `beta_testing/feedback_log.md`: Log bug reports and feature requests
- `metrics/engagement_metrics.md`: Monitor tasks analyzed, chat messages
- `metrics/retention_analysis.md`: Update retention curves

### Monthly (Post-Beta)
- `competitor_analysis.md`: Check if Motion/Reclaim shipped new features
- `customer_interviews/synthesis.md`: Synthesize learnings from latest interviews
- Review all metrics and update `VISION_AND_PLAN.md` with new insights

### Ad-Hoc (As Needed)
- `customer_interviews/`: After each user interview
- `beta_testing/nps_survey_results.md`: After sending NPS surveys

---

## How to Use Research Together

**Scenario 1: Deciding on Next Feature**
1. Check `beta_testing/feedback_log.md` for most-requested features
2. Cross-reference with `customer_interviews/synthesis.md` for pain intensity
3. Review `competitor_analysis.md` to see if competitor already does this
4. Prioritize based on: High demand + High pain + Differentiation

**Scenario 2: Low Retention (Troubleshooting)**
1. Check `metrics/retention_analysis.md` for drop-off points
2. Review `beta_testing/cohort_tracker.md` for churn reasons
3. Interview churned users (add notes to `customer_interviews/`)
4. Identify root cause and fix (onboarding friction? value unclear?)

**Scenario 3: Preparing for Product Hunt Launch**
1. Pull testimonials from `customer_interviews/` and `beta_testing/feedback_log.md`
2. Review `metrics/retention_analysis.md` for retention stats to share
3. Check `competitor_analysis.md` for positioning ("Unlike Motion, we adapt to your work style")
4. Draft launch post using insights from research

**Scenario 4: Pitching to Investors (Future)**
1. Show `metrics/retention_analysis.md` (60% Week 2 retention = strong signal)
2. Share `customer_interviews/synthesis.md` (pattern validation)
3. Reference `competitor_analysis.md` (differentiation vs. Motion/Reclaim)
4. Show NPS from `beta_testing/nps_survey_results.md` (word-of-mouth potential)

---

## Common Pitfalls to Avoid

### 1. Analysis Paralysis
**Pitfall**: Spending weeks on competitor research instead of shipping

**Fix**: Limit competitor deep dives to 2-3 days max. Then ship and learn from users.

### 2. Confirmation Bias
**Pitfall**: Only interviewing users who love Context, ignoring churned users

**Fix**: Actively seek out churned users for interviews. They have the most valuable feedback.

### 3. Vanity Metrics Trap
**Pitfall**: Celebrating "100 signups!" when retention is 10%

**Fix**: Focus on retention and engagement, not just activation. 10 retained users > 100 churned users.

### 4. Ignoring Patterns
**Pitfall**: Treating each interview as isolated feedback instead of looking for trends

**Fix**: After 5 interviews, always create `synthesis.md` to spot patterns.

### 5. Over-Indexing on One User
**Pitfall**: Building feature X because one power user requested it

**Fix**: Wait for 3+ users to request same feature before prioritizing.

---

## Research Cadence (Weekly Routine)

**Every Monday**:
- Review `beta_testing/cohort_tracker.md` for weekend activity
- Update `metrics/retention_analysis.md` with latest drop-offs
- Plan week's customer interviews (aim for 1-2 per week)

**Every Friday**:
- Update `metrics/engagement_metrics.md` with weekly stats
- Review `beta_testing/feedback_log.md` and prioritize bugs vs. features
- Send weekly summary to co-founder (retention, engagement, insights)

**Every Month**:
- Create `customer_interviews/synthesis.md` from latest interviews
- Update `competitor_analysis.md` (check changelogs, Twitter, Reddit)
- Review all metrics and update `VISION_AND_PLAN.md` if assumptions changed

---

## Success Criteria for Research Phase

**Good research looks like**:
- 5+ customer interviews completed before MVP ships
- Competitor analysis covers 3+ direct competitors (Motion, Reclaim, Sunsama)
- Beta cohort tracker updated daily during launch week
- Retention data tracked for 4+ weeks (Day 2, Week 2, Month 1)
- At least 3 "aha moment" stories captured from beta users

**Bad research looks like**:
- No customer interviews (building in vacuum)
- Only using competitors from marketing site (no hands-on testing)
- Tracking signups but not retention
- No churn reason follow-up (just letting users disappear)
- No synthesis (just raw data, no insights)

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| Dec 16, 2025 | V1 | Initial research hub structure |

**Next review**: January 15, 2026 (after beta launch)

---

*This is a living document. Update as research evolves and new files are added to `/research/` folder.*
