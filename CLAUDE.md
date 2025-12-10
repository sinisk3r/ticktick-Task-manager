# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Key points to follow when working
- Always use context7 when I need code generation, setup or configuration steps, or library/API documentation. This means you should automatically use the Context7 MCP tools to resolve library id and get library docs without me having to explicitly ask.

## Project Overview

**Context** is an LLM-powered task management system that sits on top of TickTick to auto-prioritize, schedule, and protect wellbeing. It acts as an intelligent middleware layer between TickTick and the user, powered by Claude API for contextual understanding.

## Architecture

### System Components

```
Frontend (Next.js) ↔ Backend (FastAPI) ↔ External APIs (TickTick, Claude, Gmail, Azure DevOps)
                            ↓
                Data Layer (PostgreSQL, Redis, ChromaDB)
                            ↓
                Background Workers (Celery)
```

**Key Flow:**
1. User creates task in TickTick
2. TickTick webhook → FastAPI endpoint
3. Celery worker analyzes task via Claude API
4. Task stored in PostgreSQL with analysis (urgency/importance/quadrant)
5. WebSocket pushes update to Next.js frontend
6. User sees task appear in Eisenhower matrix

### Tech Stack

- **Backend:** FastAPI (Python 3.11+), SQLAlchemy 2.0 (async), Alembic for migrations
- **Database:** PostgreSQL 15+ (relational + JSONB), Redis 7 (cache + queue), ChromaDB (embeddings)
- **LLM:** Claude Sonnet 4.5 (task analysis, email drafts, workload analysis)
- **Background Jobs:** Celery 5 with Redis broker
- **Frontend:** Next.js 14 (App Router), React, TypeScript, Tailwind CSS, shadcn/ui
- **State:** SWR for server state, WebSocket for real-time updates
- **Deployment:** Railway (backend), Vercel (frontend)

## Development Commands

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Database Operations

```bash
# Run migrations
cd backend
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback
alembic downgrade -1
```

### Running Development Servers

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

**Terminal 3 - Redis:**
```bash
redis-server
```

**Terminal 4 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`, backend on `http://localhost:8000`

### Service orchestration (init.sh)

From repo root:
```bash
./init.sh <start|stop|restart> [all|docker|backend|frontend]
```
- Default target is `all`.
- Requires Docker Desktop running; backend venv at `backend/venv`.
- Logs: `backend/uvicorn.log`, `frontend/next-dev.log`; PID files in `.pids/`.

### Testing

```bash
# Backend tests
cd backend
pytest -v

# Single test file
pytest tests/test_llm_service.py -v

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## Project Structure

### Backend (`backend/`)

```
app/
├── api/              # FastAPI routes
│   ├── auth.py       # OAuth flows (TickTick, Google)
│   ├── tasks.py      # Task CRUD operations
│   ├── calendar.py   # Calendar blocking
│   ├── analytics.py  # Workload intelligence
│   └── sync.py       # Webhook handlers
├── services/         # Business logic layer
│   ├── ticktick.py   # TickTick API integration
│   ├── llm.py        # Claude API calls & prompt management
│   ├── scheduler.py  # Calendar blocking logic
│   ├── email.py      # Gmail draft generation
│   └── azure.py      # Azure DevOps integration
├── models/           # SQLAlchemy models
│   ├── user.py
│   ├── task.py
│   ├── calendar_event.py
│   └── sync_log.py
├── workers/          # Celery background tasks
│   ├── celery_app.py
│   ├── sync_tasks.py
│   └── analysis.py
├── core/             # Configuration & utilities
│   ├── config.py     # Environment variables
│   ├── database.py   # DB session management
│   └── security.py   # JWT, OAuth utilities
├── prompts/          # Versioned LLM prompts
│   ├── task_analysis_v1.txt
│   ├── email_draft_v1.txt
│   ├── workload_analysis_v1.txt
│   └── weekly_review_v1.txt
└── main.py           # FastAPI app initialization
```

### Frontend (`frontend/`)

```
src/
├── app/              # Next.js 13+ app directory
│   ├── page.tsx      # Dashboard (Eisenhower matrix)
│   ├── tasks/        # Task detail views
│   └── settings/     # Integration configuration
├── components/
│   ├── TaskBoard.tsx      # Eisenhower matrix grid
│   ├── TaskCard.tsx       # Individual task display
│   ├── WeeklyView.tsx     # Weekly planning view
│   ├── WorkloadChart.tsx  # Analytics charts
│   └── EmailDraftModal.tsx # Email generation UI
└── lib/
    ├── api.ts        # Backend API client
    ├── hooks.ts      # Custom React hooks
    └── utils.ts      # Utilities
```

## Core Concepts

### Task Analysis (LLM Service)

The `LLMService` (`backend/app/services/llm.py`) is central to the system:

```python
async def analyze_task(task_description: str) -> TaskAnalysis:
    """
    Returns:
    - urgency_score: 1-10
    - importance_score: 1-10
    - effort_hours: estimated hours
    - blockers: list of potential blockers
    - tags: suggested tags
    - eisenhower_quadrant: Q1/Q2/Q3/Q4
    """
```

**Quadrant Assignment:**
- **Q1 (Urgent & Important):** urgency ≥ 7 AND importance ≥ 7
- **Q2 (Not Urgent, Important):** urgency < 7 AND importance ≥ 7
- **Q3 (Urgent, Not Important):** urgency ≥ 7 AND importance < 7
- **Q4 (Neither):** urgency < 7 AND importance < 7

**Prompts are versioned** in `backend/app/prompts/` for tracking performance over time.

### Data Synchronization

**Real-time Sync:**
- TickTick webhook → `/webhooks/ticktick` → Celery task → LLM analysis → PostgreSQL → WebSocket → Frontend

**Polling Fallback:**
- Celery job runs every 5 minutes to catch missed webhooks

**Bi-directional:**
- Changes in Context dashboard update TickTick via API

### Caching Strategy (Redis)

```python
# User tasks cache (5 min TTL)
f"user:{user_id}:tasks:all"
f"user:{user_id}:tasks:quadrant:{q}"

# Workload analysis (10 min TTL)
f"user:{user_id}:workload:current"

# LLM responses (24 hour TTL)
f"llm:analysis:{task_hash}"
```

### Background Jobs (Celery)

**High Priority (immediate):**
- `analyze_new_task(task_id)` - Called on task creation
- `sync_ticktick_realtime(user_id)` - Webhook trigger

**Medium Priority (every 5 min):**
- `sync_all_users_ticktick()` - Backup sync
- `update_workload_analytics(user_id)` - Recalculate stats

**Low Priority (daily):**
- `generate_weekly_reviews()` - Sunday 6pm
- `cleanup_old_sync_logs()` - Delete logs >30 days

## Key API Endpoints

```python
# Authentication
POST   /auth/ticktick/authorize
GET    /auth/ticktick/callback
POST   /auth/logout

# Tasks
GET    /api/tasks                   # List with filters
GET    /api/tasks/{id}
PUT    /api/tasks/{id}/priority     # Manual override
PUT    /api/tasks/{id}/quadrant
DELETE /api/tasks/{id}

# Sync
POST   /api/sync/ticktick           # Trigger manual sync
POST   /webhooks/ticktick           # Webhook receiver

# Analytics
GET    /api/analytics/workload
GET    /api/analytics/weekly
GET    /api/analytics/rest-score

# Email
POST   /api/email/draft/{task_id}   # Generate with Claude
POST   /api/email/send

# Azure DevOps
POST   /api/azure/create-workitem
GET    /api/azure/workitems
```

## Database Schema

**Key Models:**

**User:**
- `ticktick_access_token`, `ticktick_refresh_token` (encrypted)
- `google_access_token`, `google_refresh_token`
- OAuth tokens for all integrations

**Task:**
- TickTick data: `title`, `description`, `due_date`, `ticktick_task_id`
- LLM analysis: `urgency_score`, `importance_score`, `effort_hours`, `eisenhower_quadrant`, `blockers` (JSONB), `tags` (JSONB)
- Overrides: `manual_priority_override`, `manual_quadrant_override`
- Calendar: `calendar_event_id`, `scheduled_start`, `scheduled_end`

**Indexes:**
- `idx_user_quadrant` on `(user_id, eisenhower_quadrant)`
- `idx_user_status` on `(user_id, status)`
- `idx_due_date` on `due_date`

## Environment Variables

Required in `backend/.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/context
REDIS_URL=redis://localhost:6379

# APIs
TICKTICK_CLIENT_ID=your_client_id
TICKTICK_CLIENT_SECRET=your_client_secret
TICKTICK_REDIRECT_URI=http://localhost:8000/auth/callback

ANTHROPIC_API_KEY=your_claude_api_key

GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret

AZURE_DEVOPS_ORG=your_org
AZURE_DEVOPS_PAT=your_personal_access_token

# App
SECRET_KEY=your_secret_key_min_32_chars
FRONTEND_URL=http://localhost:3000
```

Frontend in `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Error Handling Patterns

**LLM API Failures:**
1. Retry 3x with exponential backoff
2. If still failing, mark task for manual review
3. User sees "Analysis pending" state

**TickTick Sync Failures:**
1. Log to `sync_logs` table
2. Retry in next 5-min cycle
3. Alert user if >3 consecutive failures

**Rate Limiting:**
- 100 API requests/min per user
- 50 LLM calls/hour per user
- Enforced via Redis counters

## Development Workflow

1. **Feature Branch:** Create from `main`
2. **Develop:** Write code + tests
3. **Test Locally:** `pytest` (backend), `npm test` (frontend)
4. **Commit:** Use conventional commits (`feat:`, `fix:`, `refactor:`)
5. **PR:** Open pull request to `main`
6. **Deploy:** Merge triggers CI/CD

## UI Design System

**Color Scheme (Dark Mode):**
- Background: `#1f2937` (gray-800)
- Cards: `#374151` (gray-700)
- Accents: `#60a5fa` (blue-400)
- Text: `#f9fafb` (gray-50)

**Layout:** Compact, matrix-first (Eisenhower matrix is primary view)
**Button Style:** Minimal with subtle hover states

## Important Implementation Notes

1. **All LLM calls are async** and run in Celery workers to avoid blocking the API
2. **WebSocket connection** handles real-time task updates (auto-reconnect on disconnect)
3. **Token refresh** is automatic - check for 401 errors and refresh OAuth tokens
4. **Manual overrides always win** - if user manually sets priority, don't override with LLM
5. **Embeddings for similarity** - ChromaDB stores task embeddings for finding similar tasks
6. **Retry logic** - Use `tenacity` library for API call retries with exponential backoff
7. **All API tokens encrypted at rest** using AES-256

## Phase Breakdown

**Phase 1 (Weeks 1-4):** Smart Task Intake, Dashboard, Manual Overrides
**Phase 2 (Weeks 5-8):** Workload Intelligence, Rest Reminders, Email Drafts
**Phase 3 (Weeks 9-10.5):** Azure DevOps Integration, Weekly Planning, Voice Capture

See `MVP_ROADMAP.md` for detailed week-by-week implementation plan.

## API Integration References

- **TickTick API:** https://developer.ticktick.com/api
- **Claude API:** Uses Anthropic Python SDK
- **Google Calendar/Gmail:** Uses `google-api-python-client`
- **Azure DevOps:** Uses `azure-devops` Python package
- **Whisper (Voice):** OpenAI Whisper API for transcription

Full OAuth setup and code examples in `API_INTEGRATION.md`.

## Documentation

All detailed documentation is in the `docs/` folder:

- `docs/ARCHITECTURE.md` - System design, data flows, deployment
- `docs/FEATURES.md` - Detailed feature specifications
- `docs/TECH_STACK.md` - Technology choices and rationale
- `docs/API_INTEGRATION.md` - External API setup guides
- `docs/MVP_ROADMAP.md` - Week-by-week implementation plan

## Claude Code Slash Commands

Custom slash commands are available in `.claude/commands/` to accelerate development:

- `/new-feature` - Scaffold features following the architecture
- `/analyze-prompt` - Improve LLM prompts for better accuracy
- `/debug-llm` - Debug Claude API integration issues
- `/celery-debug` - Debug background task problems
- `/migration` - Create safe database migrations
- `/optimize` - Identify and fix performance bottlenecks
- `/test-scenario` - Create comprehensive tests
- `/api-docs` - Generate API documentation

See `.claude/README.md` for detailed usage and examples.

Remember:
- We DONT add any keys into git - since its a public project
- The goal is to have feedback driven execution that works at speed to deliver quick value to users

## Remediation Log (Qwen3 / Ollama)
- Issue: Qwen3 returned empty `content` while JSON landed in `thinking` when `format:"json"` was used.
- Fix: Send requests with `think:false` (keep `format:"json"`); fallback to `thinking` only if ever returned.