# 30-Day Beta Launch - Cheat Sheet

**Print this or keep it open. Your quick reference for the next 4 weeks.**

---

## Timeline at a Glance

```
Week 1 (Dec 16-22): Customer Discovery
→ Test Motion/Reclaim/Sunsama
→ Interview 5 users
→ Recruit 10 beta signups

Week 2-3 (Dec 23 - Jan 5): Build & Dogfood
→ Build agent core (create/list/complete tasks)
→ Add avoidance detection + task breakdown
→ Dogfood daily, fix bugs

Week 4 (Jan 6-12): Beta Launch
→ Launch to 10 users (Jan 6)
→ Fix bugs, collect feedback
→ Measure 60% Day 7 retention (Jan 12)
```

---

## Success Criteria (Check Weekly)

### Week 1 ✅
- [ ] 10+ beta signups
- [ ] 5 customer interviews
- [ ] Competitor analysis done

### Week 2-3 ✅
- [ ] Agent responds <3 sec
- [ ] Dogfooded 5+ days
- [ ] <3 critical bugs

### Week 4 ✅
- [ ] 80% login rate (8/10)
- [ ] 60% Day 7 retention (6/10)
- [ ] 3+ "I can't go back" reactions

---

## Daily Checklist

### Morning (5 min)
- [ ] Check tracker (signups/metrics)
- [ ] Triage critical bugs
- [ ] Respond to user messages

### Evening (30+ min)
- [ ] Code OR dogfood session
- [ ] Update logs (5 min)

### Sunday (1 hour)
- [ ] Weekly sync with co-founder
- [ ] Review metrics
- [ ] Adjust plan

---

## Key Files (Bookmark These)

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `30_DAY_TASK_LIST.md` | Master plan | Reference daily |
| `QUICK_START.md` | Getting started guide | Read once |
| `research/beta_signup_tracker.md` | Week 1 signups | Daily (Week 1) |
| `research/dogfood_log.md` | Week 2-3 testing | Daily (Week 2-3) |
| `research/beta_metrics_log.md` | Week 4 metrics | Daily (Week 4) |
| `research/README.md` | File navigator | Reference as needed |

---

## Owner Responsibilities

### Srikar (Developer/PM)
- Backend development (agent, tools)
- Bug fixes (critical/high)
- Dogfooding daily
- Customer interviews (technical)
- **Time**: 15-20 hrs/week

### Co-founder
**Option A (Technical)**:
- Frontend (ChatPanel, UI)
- Analytics setup
- Onboarding flow
- **Time**: 15-20 hrs/week

**Option B (Non-Technical)**:
- Customer interviews
- Marketing content
- Community management
- **Time**: 10-15 hrs/week

---

## Emergency Contacts

### If Behind Schedule
- **Week 1**: Extend 3 days, push launch to Jan 15
- **Week 2-3**: Cut scope (drop task breakdown)
- **Week 4**: Launch with 6-8 users (still valid)

### If Co-founder Drops Out
- Srikar continues solo
- Extend to 6 weeks
- Cut onboarding flow

### If Zero Beta Signups
- Mass email 50 ISB alumni
- Extend Week 1 by 1 week
- Backup: LinkedIn/Twitter outreach

### If 0% Retention (Jan 12)
- Emergency pivot meeting (2 hours)
- Decide: Persevere, Pivot, or Kill

---

## Week 1 Quick Actions

### Monday (Dec 16)
- [ ] Sign up: Motion, Reclaim, Sunsama
- [ ] Draft beta pitch
- [ ] Create Google Form

### Tuesday (Dec 17)
- [ ] Use Motion (2 hours)
- [ ] Finalize beta pitch

### Wednesday (Dec 18)
- [ ] Use Reclaim (2 hours)
- [ ] Send pitch to 20 people

### Thursday (Dec 19)
- [ ] Use Sunsama (2 hours)
- [ ] Schedule 5 interviews

### Friday (Dec 20)
- [ ] Interview #1
- [ ] Interview #2

### Weekend (Dec 21-22)
- [ ] Interview #3, #4, #5
- [ ] Synthesize insights
- [ ] Retrospective

---

## Week 4 Quick Metrics

### Daily Metrics to Track
- **DAU**: Daily active users
- **Login rate**: % who logged in
- **Tasks created**: Total count
- **Agent queries**: Total count
- **Errors**: Backend crashes

### Week 1 Summary (Jan 12)
- **Day 7 Retention**: [X]% (target: 60%)
- **NPS**: [X] (target: ≥40)
- **Power users**: [X]/10 (5+ days active)
- **Churned users**: [X]/10 (didn't return)

---

## Decision Tree (Jan 12)

### If Retention ≥ 50% → SCALE
- [ ] Expand to 50 users
- [ ] Add top 2 features
- [ ] Test paywall ($5/mo)

### If Retention 30-50% → ITERATE
- [ ] Interview power + churned users
- [ ] Narrow ICP (who loves it?)
- [ ] Rebuild for that segment

### If Retention <30% → PIVOT/KILL
- [ ] Root cause analysis
- [ ] Pivot meeting (2 hours)
- [ ] Decide: Persevere, Pivot, Kill

---

## Key Mantras

1. **Ship fast, learn faster**
   - Beta = learning vehicle, not finished product

2. **Ruthless prioritization**
   - Only build features for "Aha Moment"

3. **Honest communication**
   - Tell users "This is rough, help me fix it"

4. **Retention > Features**
   - 6 users who love it > 10 users who tried it once

5. **Fix bugs same-day**
   - Critical bugs = fix within 24 hours (no excuses)

---

## Competitor Feature Gaps (Steal Ideas)

| Gap | Motion | Reclaim | Sunsama | Context |
|-----|--------|---------|---------|---------|
| Personality adaptation | ❌ | ❌ | ❌ | ✅ |
| Avoidance detection | ❌ | ❌ | ❌ | ✅ |
| Task breakdown | ⚠️ | ❌ | ❌ | ✅ |
| Conversational UI | ⚠️ | ❌ | ⚠️ | ✅ |
| Affordable ($5-10) | ❌ | ✅ | ❌ | ✅ |

---

## Interview Quick Questions

1. Current task management tool?
2. Biggest frustration?
3. Task you're avoiding? Why?
4. Ideal "Aha Moment"?
5. Would you pay? How much?

---

## Dogfooding Bug Severity

- **Critical (P0)**: Core workflow broken → Fix within 24 hours
- **High (P1)**: Major friction → Fix within 3 days
- **Medium (P2)**: Annoying but usable → Fix before beta launch
- **Low (P3)**: Nice-to-have → Post-launch backlog

---

## Beta Launch Day Checklist (Jan 6)

### Pre-Launch (Morning)
- [ ] Backend deployed (Railway)
- [ ] Frontend deployed (Vercel)
- [ ] TickTick OAuth working
- [ ] Analytics tracking (PostHog)
- [ ] Database backups enabled

### Launch (Evening)
- [ ] Send access to 10 users (personalized emails)
- [ ] Set up monitoring alerts
- [ ] Post in WhatsApp group: "We're live!"

---

## Next 30 Days (If Retention Good)

### Week 5 (Jan 13-19)
- [ ] Expand to 50 ISB alumni
- [ ] Add top 2 requested features
- [ ] Test soft paywall ($5/mo)

### Week 6 (Jan 20-26)
- [ ] Product Hunt prep (assets, copy)
- [ ] Build email waitlist (target: 100)
- [ ] Measure 50-user retention

---

## Resources

- **Main Plan**: `docs/strategy_plan/30_DAY_TASK_LIST.md`
- **Quick Start**: `docs/strategy_plan/QUICK_START.md`
- **Research Hub**: `docs/strategy_plan/research/README.md`
- **Project Context**: `CLAUDE.md` (root)

---

**Print this. Pin it to your wall. Reference it daily.**

**You got this. 28 days. Let's ship. 🚀**
