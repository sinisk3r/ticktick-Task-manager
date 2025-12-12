# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Context** is an LLM-powered task management system that sits on top of TickTick to auto-prioritize, schedule, and protect wellbeing. It acts as an intelligent middleware layer between TickTick and the user, with a configurable LLM backend (Ollama/Qwen3, OpenRouter, Claude API, OpenAI).

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
- **LLM Integration:** LangChain/LangGraph with multi-provider support (Ollama/Qwen3, OpenRouter, Anthropic Claude, OpenAI)
- **Agent System:** LangGraph-based conversational agent with tool calling (create/complete/delete/list tasks)
- **Database:** PostgreSQL 15+ (relational + JSONB), Redis 7 (cache), Docker Compose for local dev
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Real-time:** Server-Sent Events (SSE) for chat/agent streaming
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

### Agent System Testing (Ollama/Qwen3)

**Interactive testing workflow for the agentic assistant:**

```bash
# 1. Single query test (interactive)
./backend/scripts/test_agent.sh --query "Create task for meeting at 2pm"

# 2. Run all test cases
./backend/scripts/run_agent_tests.sh

# 3. Inspect raw Ollama behavior (debug model issues)
./backend/scripts/inspect_ollama.sh --prompt "Generate JSON plan" --think false

# 4. Compare before/after changes (regression testing)
./backend/scripts/test_agent.sh --batch --save results_v1.json
# (make code changes to planner.py or prompts)
./backend/scripts/test_agent.sh --batch --save results_v2.json --diff results_v1.json
```

**Note:** All scripts automatically activate the Python venv at `backend/venv` if it exists.

**Iteration workflow:**

1. **Test** - Run agent tests to see current behavior
2. **Read** - Examine output (thinking, tool calls, messages, errors)
3. **Modify** - Adjust prompts, token limits, or logic in `backend/app/agent/`
4. **Test Again** - Verify improvements, compare with previous results
5. **Document** - Update `docs/agentic-assistant-plan.md` with findings

**Key test scripts:**

- `backend/scripts/test_agent.sh` - Full-featured test runner with SSE capture
- `backend/scripts/inspect_ollama.sh` - Raw Ollama API inspector
- `backend/scripts/run_agent_tests.sh` - Automated test suite with reporting
- `backend/tests/agent_test_cases.json` - 20+ test scenarios

**What gets tested:**

- Tool calling accuracy (create/complete/delete/list tasks)
- Conversational responses (greetings, advice, questions)
- Response quality (no truncation, no thinking leaks)
- Edge cases (ambiguous input, long responses, empty queries)
- Performance metrics (duration, token usage, error rates)

**Test output:**

Results saved to `backend/test_results/` with:
- Full SSE event stream capture
- Tool call logs with args/results
- Thinking vs message separation
- Pass/fail criteria evaluation
- Regression comparison reports

## Project Structure

### Backend (`backend/app/`)

```
api/              # FastAPI routes
├── agent.py      # Conversational agent endpoint (SSE streaming)
├── auth.py       # OAuth flows (TickTick)
├── tasks.py      # Task CRUD operations
├── llm_configurations.py  # LLM provider management UI endpoints
└── settings.py   # User settings & personalization

agent/            # LangGraph-based agent system
├── graph.py      # LangGraph workflow definition
├── llm_factory.py # Multi-provider LLM factory
└── tools.py      # Tool definitions (create/list/complete/delete tasks)

services/         # Business logic layer
├── ticktick.py   # TickTick API integration
├── llm_ollama.py # Ollama/Qwen3 integration
├── workload_calculator.py
└── sync_service.py

models/           # SQLAlchemy models
├── user.py
├── task.py
├── project.py
└── llm_configuration.py

core/             # Configuration & utilities
├── config.py     # Environment variables
├── llm_config.py # LLM provider configuration
└── database.py   # DB session management

scripts/          # Development & testing scripts
├── test_agent.sh            # Single agent query test
├── run_agent_tests.sh       # Full test suite
└── inspect_ollama.sh        # Raw Ollama debugging
```

### Frontend (`frontend/`)

```
app/              # Next.js 14 app directory
├── (main)/       # Main authenticated app
│   ├── matrix/   # Eisenhower matrix view
│   ├── simple/   # Simple list view
│   └── settings/ # LLM & user settings
└── auth/         # Auth pages

components/
├── EisenhowerMatrix.tsx    # 2x2 quadrant grid with DnD
├── ChatPanel.tsx           # Agent chat interface with SSE
├── QuickAddTaskModal.tsx   # Inline task creation
├── UnsortedList.tsx        # Tasks pending quadrant assignment
├── LLMConfigurationManager.tsx  # Multi-provider LLM config
└── ui/                     # shadcn/ui components

lib/
├── api.ts              # Backend API client
├── useAgentStream.ts   # SSE streaming hook for agent
└── useChatStream.ts    # Chat streaming utilities
```

## Core Concepts

### LLM Provider System

Multi-provider LLM support configured via environment variables (`backend/app/core/llm_config.py`):

```bash
# Choose provider: ollama | openrouter | anthropic | openai
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b
LLM_BASE_URL=http://localhost:11434  # For Ollama
LLM_API_KEY=sk-xxx                   # For cloud providers
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=1000
```

**Runtime Switching:** Users can create saved LLM configurations in the UI and switch between providers without restarting.

### Agent System (LangGraph)

The conversational agent (`backend/app/agent/graph.py`) handles task management through natural language:

**Tools:**
- `create_task` - Create new task with optional quadrant/priority
- `list_tasks` - List tasks with filters (quadrant, status, project)
- `complete_task` - Mark task as complete
- `delete_task` - Delete task

**Streaming:** Uses Server-Sent Events (SSE) for real-time streaming:
- `thinking` - Model's internal reasoning (visible in debug mode)
- `message` - User-facing response chunks
- `tool_call` - Tool invocation with args/results

### Eisenhower Quadrant Assignment

Tasks are classified into 4 quadrants based on urgency/importance:
- **Q1 (Urgent & Important):** urgency ≥ 7 AND importance ≥ 7
- **Q2 (Not Urgent, Important):** urgency < 7 AND importance ≥ 7
- **Q3 (Urgent, Not Important):** urgency ≥ 7 AND importance < 7
- **Q4 (Neither):** urgency < 7 AND importance < 7

Users can manually override via drag-and-drop or quadrant picker.

### TickTick Synchronization

**Bi-directional Sync:**
- Context → TickTick: Manual sync endpoint (`POST /api/sync/ticktick/manual`)
- TickTick → Context: Webhook receiver (`POST /webhooks/ticktick`) - creates tasks in PostgreSQL
- Changes in Context (quadrant, priority, status) push back to TickTick

**Sync Strategy:**
- Manual trigger only (no automatic polling)
- Tasks stored in PostgreSQL with TickTick ID mapping
- Soft deletes supported (archive in TickTick = delete in Context)

### Port Management (init.sh)

The project uses dynamic port allocation managed by `init.sh`:

**Default Ports:**
- Backend: 5400
- Frontend: 5401
- PostgreSQL (Docker): 5432
- Redis (Docker): 6379

**Dynamic Allocation:** If default port is occupied, `init.sh` automatically finds next available port and updates `.ports.json` and `.env.runtime`.

**TickTick OAuth Caveat:** The redirect URI must match the backend port. If backend port changes, manually update `TICKTICK_REDIRECT_URI` in `backend/.env`.

## Key API Endpoints

```python
# Authentication
POST   /auth/ticktick/authorize    # Initiate OAuth flow
GET    /auth/ticktick/callback     # OAuth callback
GET    /auth/me                    # Current user info
POST   /auth/logout

# Tasks
GET    /api/tasks                  # List with filters (quadrant, project, status)
GET    /api/tasks/{id}
POST   /api/tasks                  # Create task
PUT    /api/tasks/{id}             # Update task
PUT    /api/tasks/{id}/quadrant    # Manual quadrant override
DELETE /api/tasks/{id}

# Agent (SSE streaming)
POST   /api/agent/chat             # Conversational agent (returns SSE stream)

# LLM Configuration
GET    /api/llm-configurations                    # List saved configs
POST   /api/llm-configurations                    # Create new config
PUT    /api/llm-configurations/{id}/activate      # Switch active provider
DELETE /api/llm-configurations/{id}               # Delete config
POST   /api/llm-configurations/test-connection    # Test provider connection

# Sync
POST   /api/sync/ticktick/manual   # Trigger manual TickTick sync
POST   /webhooks/ticktick          # TickTick webhook receiver

# Settings
GET    /api/settings/user          # User personalization settings
PUT    /api/settings/user          # Update settings
```

## Database Schema

**Key Models:**

**User:**
- `ticktick_access_token`, `ticktick_refresh_token` (encrypted)
- `default_view` - Preferred dashboard view (matrix/simple)
- `time_zone`, `work_hours_start`, `work_hours_end`

**Task:**
- TickTick sync: `title`, `description`, `due_date`, `ticktick_task_id`, `ticktick_project_id`
- Prioritization: `urgency_score`, `importance_score`, `eisenhower_quadrant`
- Metadata: `status`, `priority`, `tags` (JSONB), `manual_order` (for drag-drop sorting)
- Relations: `user_id`, `project_id`

**Project:**
- `name`, `color`, `ticktick_project_id`
- `is_inbox` - Flag for default inbox project

**LLMConfiguration:**
- `provider` - ollama/openrouter/anthropic/openai
- `model`, `base_url`, `api_key` (encrypted), `temperature`, `max_tokens`
- `is_active` - Current active config per user

**Indexes:**
- `idx_user_quadrant` on `(user_id, eisenhower_quadrant)`
- `idx_user_status` on `(user_id, status)`
- `idx_user_project` on `(user_id, project_id)`

## Environment Variables

Required in `backend/.env`:

```bash
# Database (Docker Compose)
DATABASE_URL=postgresql+asyncpg://context:context_dev@127.0.0.1:5433/context
REDIS_URL=redis://127.0.0.1:6379

# LLM Provider (choose one or configure multiple in UI)
LLM_PROVIDER=ollama              # ollama | openrouter | anthropic | openai
LLM_MODEL=qwen3:8b               # Model identifier
LLM_BASE_URL=http://127.0.0.1:11434  # For Ollama
LLM_API_KEY=sk-xxx               # For cloud providers
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=1000

# TickTick OAuth
TICKTICK_CLIENT_ID=your_client_id
TICKTICK_CLIENT_SECRET=your_client_secret
# IMPORTANT: Update this if backend port changes (see .env.runtime)
TICKTICK_REDIRECT_URI=http://localhost:5400/auth/ticktick/callback

# App
SECRET_KEY=your_secret_key_min_32_chars
FRONTEND_URL=http://localhost:5401
```

Frontend in `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:5400
```

**Note:** Actual runtime ports are in `.env.runtime` (auto-generated by `init.sh`).

## Important Implementation Notes

1. **SSL/TLS Certificate Handling (macOS):** The backend uses a custom CA bundle path (`backend/certs/combined.pem` or certifi) to handle corporate proxies like Zscaler. Set via `SSL_CERT_FILE` environment variable in `backend/app/core/llm_config.py` and `init.sh`.

2. **LLM Provider Connections:** Test connections before activating a provider config. The UI provides a test endpoint (`POST /api/llm-configurations/test-connection`) that verifies API keys and network connectivity.

3. **Agent Tool Calling:** LangGraph agent uses function calling. Ensure the LLM model supports tool/function calling (Qwen3, Claude, GPT-4, etc.). Smaller models may struggle with complex JSON schemas.

4. **Task Manual Ordering:** Drag-and-drop in the UI updates `manual_order` field. This is independent of priority/urgency scores and takes precedence in UI sorting.

5. **TickTick Sync Conflicts:** The app doesn't auto-merge conflicts. If a task is modified in both TickTick and Context, manual sync will use Context's version (last write wins).

6. **SSE Streaming:** The agent endpoint returns Server-Sent Events. Frontend must handle reconnection logic and parse `event: thinking|message|tool_call` types.

7. **OAuth Tokens:** TickTick tokens are encrypted at rest in PostgreSQL. Token refresh is automatic but check for 401 errors.

8. **Manual Overrides Win:** If user manually sets quadrant/priority via UI, don't override with LLM analysis.

## Documentation

Detailed documentation is in the `docs/` folder:

- `docs/agentic-assistant-plan.md` - LangGraph agent architecture and iteration plan
- `docs/langchain-migration-plan.md` - Migration from raw Ollama API to LangChain
- `docs/ARCHITECTURE.md` - System design, data flows
- `docs/FEATURES.md` - Feature specifications
- `docs/API_INTEGRATION.md` - TickTick OAuth setup guide

## Development Principles

- **No Secrets in Git:** This is a public project - never commit API keys, tokens, or credentials
- **Feedback-Driven:** Prioritize quick iterations and user feedback over perfection
- **Use Context7:** Always use Context7 MCP for library documentation and code generation assistance

## Remediation Log (Qwen3 / Ollama)
- **Issue 1:** Qwen3 returned empty `content` while JSON landed in `thinking` when `format:"json"` was used.
  - **Fix:** Send requests with `think:false` (keep `format:"json"`); fallback to `thinking` only if ever returned.
- **Issue 2:** qwen3:4b echoed back complex JSON prompts instead of generating tool plans (Dec 12, 2025)
  - **Root Cause:** Small model treats nested JSON input as schema to copy, not instructions
  - **Fix:** Upgraded to qwen3:8b which handles complex JSON correctly
  - **Config:** `OLLAMA_MODEL=qwen3:8b` in `backend/.env`
  - **Trade-off:** ~50% slower but fully functional for tool calling