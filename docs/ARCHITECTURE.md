# Architecture

## System Overview

Context is a **semi-agentic task intelligence system** that acts as an intelligent middleware layer between TickTick and the user, powered by Claude LLM for contextual understanding and decision-making.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  TickTick  │  │  Context   │  │   Voice    │                │
│  │    App     │  │  Web UI    │  │  Capture   │                │
│  └──────┬─────┘  └─────┬──────┘  └──────┬─────┘                │
└─────────┼──────────────┼────────────────┼───────────────────────┘
          │              │                │
          │              ▼                │
          │    ┌─────────────────────┐   │
          │    │   Next.js Frontend  │   │
          │    │  - Matrix Dashboard │   │
          │    │  - Workload Charts  │   │
          │    │  - Email Drafts UI  │   │
          │    └──────────┬──────────┘   │
          │               │               │
          │               │ WebSocket     │
          │               │ + REST API    │
          │               ▼               │
          │    ┌─────────────────────┐   │
          └───▶│   FastAPI Backend   │◀──┘
               │  - Auth & Session   │
               │  - API Gateway      │
               │  - WebSocket Server │
               └──────────┬──────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │TickTick  │   │  Claude  │   │  Gmail   │
   │   API    │   │   API    │   │   API    │
   │          │   │          │   │          │
   │ OAuth2   │   │LLM Layer │   │ OAuth2   │
   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │              │              │
        ▼              ▼              ▼
   ┌────────────────────────────────────┐
   │      Service Layer (Business       │
   │           Logic)                   │
   │  ┌──────────┐  ┌──────────┐       │
   │  │ TickTick │  │   LLM    │       │
   │  │ Service  │  │ Service  │       │
   │  └──────────┘  └──────────┘       │
   │  ┌──────────┐  ┌──────────┐       │
   │  │Scheduler │  │  Email   │       │
   │  │ Service  │  │ Service  │       │
   │  └──────────┘  └──────────┘       │
   │  ┌──────────┐  ┌──────────┐       │
   │  │  Azure   │  │Workload  │       │
   │  │DevOps Svc│  │Analytics │       │
   │  └──────────┘  └──────────┘       │
   └───────────┬────────────────────────┘
               │
               ▼
   ┌───────────────────────────────────┐
   │      Data Layer                   │
   │  ┌──────────┐  ┌──────────┐      │
   │  │PostgreSQL│  │  Redis   │      │
   │  │          │  │          │      │
   │  │ Tasks    │  │  Cache   │      │
   │  │ Users    │  │  Queue   │      │
   │  │ Events   │  │Session   │      │
   │  └──────────┘  └──────────┘      │
   │  ┌──────────┐                    │
   │  │ChromaDB  │                    │
   │  │          │                    │
   │  │Embeddings│                    │
   │  └──────────┘                    │
   └───────────────────────────────────┘
        │
        ▼
   ┌────────────────┐
   │ Celery Workers │
   │                │
   │ - Sync Tasks   │
   │ - Analysis     │
   │ - Scheduling   │
   └────────────────┘
```

## Core Components

### 1. Frontend (Next.js)

**Purpose:** User interface for viewing and managing tasks

**Key Features:**
- Server-side rendering for fast initial load
- WebSocket connection for real-time updates
- Dark mode optimized UI with compact layout
- Responsive design (desktop primary, mobile secondary)

**Main Views:**
- `/` - Dashboard with Eisenhower matrix (matrix-first layout)
- `/tasks/[id]` - Task detail view with email draft generation
- `/analytics` - Workload intelligence charts
- `/settings` - Integration configuration

**State Management:**
- SWR for server state (tasks, user data)
- React Context for UI state (theme, sidebar)
- WebSocket for real-time task updates

### 2. Backend (FastAPI)

**Purpose:** API gateway, business logic, and orchestration

**Key Routes:**

```python
# Authentication
POST   /auth/ticktick/authorize     # Start OAuth flow
GET    /auth/ticktick/callback      # Handle OAuth callback
POST   /auth/logout                 # Logout user

# Tasks
GET    /api/tasks                   # List tasks with filters
GET    /api/tasks/{id}              # Get task details
PUT    /api/tasks/{id}/priority     # Manual priority override
PUT    /api/tasks/{id}/quadrant     # Move between quadrants
DELETE /api/tasks/{id}              # Delete task

# Sync
POST   /api/sync/ticktick           # Trigger manual sync
POST   /webhooks/ticktick           # Webhook receiver

# Analytics
GET    /api/analytics/workload      # Current workload stats
GET    /api/analytics/weekly        # Weekly summary
GET    /api/analytics/rest-score    # Rest recommendation score

# Email
POST   /api/email/draft/{task_id}   # Generate email draft
POST   /api/email/send              # Send email via Gmail

# Azure DevOps
POST   /api/azure/create-workitem   # Create work item from task
GET    /api/azure/workitems         # List synced work items

# Voice
POST   /api/voice/transcribe        # Transcribe audio → tasks
```

### 3. LLM Service Layer

**Purpose:** Claude API integration for intelligent analysis

**Core Functions:**

```python
class LLMService:
    async def analyze_task(self, task_description: str) -> TaskAnalysis:
        """
        Analyzes task and returns:
        - urgency_score: 1-10
        - importance_score: 1-10
        - effort_hours: estimated hours
        - blockers: list of potential blockers
        - tags: suggested tags
        - eisenhower_quadrant: Q1/Q2/Q3/Q4
        """
        
    async def generate_email_draft(
        self, 
        task: Task, 
        context: str,
        recipient: str
    ) -> EmailDraft:
        """
        Generates contextual email draft
        """
        
    async def analyze_workload(
        self, 
        tasks: List[Task],
        calendar_events: List[CalendarEvent]
    ) -> WorkloadAnalysis:
        """
        Returns:
        - hours_scheduled: total hours
        - hours_available: free hours
        - overcommitment_risk: low/medium/high
        - rest_recommendation: bool
        """
        
    async def weekly_review(
        self,
        last_week_tasks: List[Task]
    ) -> WeeklyReview:
        """
        Reviews completion, suggests priorities
        """
```

**Prompt Engineering:**

All prompts are versioned and stored in `backend/app/prompts/`:
- `task_analysis_v1.txt` - Task intake prompt
- `email_draft_v1.txt` - Email generation prompt
- `workload_analysis_v1.txt` - Workload evaluation prompt
- `weekly_review_v1.txt` - Weekly planning prompt

### 4. TickTick Integration

**Sync Strategy:**
- **Real-time:** Webhook from TickTick → immediate analysis
- **Polling:** Every 5 minutes as backup (in case webhook fails)
- **Bi-directional:** Changes in Context update TickTick

**Data Flow:**

```
TickTick Task Created
    ↓
Webhook POST to /webhooks/ticktick
    ↓
Parse task data (title, description, due_date, tags)
    ↓
Queue Celery task: analyze_and_store
    ↓
Background: Call Claude API for analysis
    ↓
Store task + analysis in PostgreSQL
    ↓
WebSocket push to frontend
    ↓
User sees task appear in matrix
```

### 5. Database Schema (PostgreSQL)

**Key Tables:**

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY,
    ticktick_user_id VARCHAR(255) UNIQUE,
    email VARCHAR(255),
    ticktick_access_token TEXT,
    ticktick_refresh_token TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    ticktick_task_id VARCHAR(255) UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    due_date TIMESTAMP,
    
    -- LLM Analysis
    urgency_score INT,
    importance_score INT,
    effort_hours DECIMAL,
    eisenhower_quadrant VARCHAR(2), -- Q1, Q2, Q3, Q4
    blockers JSONB,
    tags JSONB,
    
    -- Calendar
    calendar_event_id VARCHAR(255),
    scheduled_start TIMESTAMP,
    scheduled_end TIMESTAMP,
    
    -- Status
    status VARCHAR(50), -- pending, in_progress, completed
    completed_at TIMESTAMP,
    
    -- Overrides
    manual_priority_override BOOLEAN DEFAULT FALSE,
    manual_quadrant_override BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    INDEX idx_user_quadrant (user_id, eisenhower_quadrant),
    INDEX idx_user_status (user_id, status),
    INDEX idx_due_date (due_date)
);

-- Calendar Events (from Google Calendar)
CREATE TABLE calendar_events (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    google_event_id VARCHAR(255),
    title TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    is_all_day BOOLEAN,
    created_at TIMESTAMP
);

-- Sync Logs
CREATE TABLE sync_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    sync_type VARCHAR(50), -- ticktick, google_calendar, azure_devops
    status VARCHAR(50), -- success, failure
    tasks_synced INT,
    error_message TEXT,
    created_at TIMESTAMP
);

-- Email Drafts
CREATE TABLE email_drafts (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    task_id UUID REFERENCES tasks(id),
    subject TEXT,
    body TEXT,
    recipient VARCHAR(255),
    status VARCHAR(50), -- draft, sent
    created_at TIMESTAMP
);

-- Azure DevOps Work Items
CREATE TABLE azure_workitems (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    task_id UUID REFERENCES tasks(id),
    azure_workitem_id INT,
    azure_url TEXT,
    created_at TIMESTAMP
);
```

### 6. Caching Strategy (Redis)

**Cache Keys:**

```python
# User tasks cache (5 min TTL)
f"user:{user_id}:tasks:all"
f"user:{user_id}:tasks:quadrant:{q}"

# Workload analysis cache (10 min TTL)
f"user:{user_id}:workload:current"

# LLM response cache (24 hour TTL)
f"llm:analysis:{task_hash}"

# Session storage
f"session:{session_id}"

# Rate limiting
f"ratelimit:user:{user_id}:llm_calls"
```

### 7. Background Jobs (Celery)

**Tasks:**

```python
# High Priority (executed immediately)
@celery.task
def analyze_new_task(task_id: str):
    """Called on task creation"""

@celery.task
def sync_ticktick_realtime(user_id: str):
    """Called by webhook"""

# Medium Priority (every 5 minutes)
@celery.task
def sync_all_users_ticktick():
    """Backup sync for all users"""

@celery.task
def update_workload_analytics(user_id: str):
    """Recalculate workload stats"""

# Low Priority (daily)
@celery.task
def generate_weekly_reviews():
    """Generate weekly review for all users"""

@celery.task
def cleanup_old_sync_logs():
    """Delete logs older than 30 days"""
```

## Data Flow Diagrams

### Task Creation Flow

```
User creates task in TickTick
    ↓
TickTick sends webhook to Context
    ↓
FastAPI /webhooks/ticktick receives POST
    ↓
Extract: title, description, due_date, project, tags
    ↓
Queue Celery task: analyze_new_task(task_id)
    ↓
[Async] Celery worker picks up task
    ↓
Call LLMService.analyze_task()
    ↓
Claude API analyzes:
  - Urgency (1-10)
  - Importance (1-10)
  - Effort (hours)
  - Blockers
  - Quadrant (Q1/Q2/Q3/Q4)
    ↓
Store analysis in PostgreSQL tasks table
    ↓
Generate embedding for task similarity
    ↓
Store embedding in ChromaDB
    ↓
Check if calendar blocking needed (Q1, Q2)
    ↓
If yes: SchedulerService.block_calendar()
    ↓
WebSocket broadcast to user's frontend
    ↓
Frontend receives update
    ↓
React component re-renders matrix
    ↓
User sees task in appropriate quadrant
```

### Weekly Planning Flow

```
Sunday 6pm (scheduled)
    ↓
Celery task: generate_weekly_reviews()
    ↓
For each user:
    ↓
Fetch last week's tasks from PostgreSQL
    ↓
Call LLMService.weekly_review()
    ↓
Claude analyzes:
  - Completion rate
  - Time spent per quadrant
  - Patterns (overcommitment, procrastination)
  - Blockers that repeated
    ↓
Generate recommendations:
  - Top 3 priorities for next week
  - Tasks to delegate
  - Rest days needed
  - Risks to watch
    ↓
Store in weekly_reviews table
    ↓
Send notification to user
    ↓
User opens Context
    ↓
Dashboard shows weekly review banner
```

## Security Considerations

### Authentication
- OAuth 2.0 for TickTick, Gmail, Azure DevOps
- JWT tokens for session management
- Refresh token rotation every 7 days

### Data Protection
- All API keys stored in environment variables
- Database credentials in secrets manager
- User tokens encrypted at rest (AES-256)
- HTTPS only in production

### Rate Limiting
- 100 API requests per minute per user
- 50 LLM calls per hour per user
- 10 email drafts per hour per user

### Privacy
- No task content sent to 3rd parties except Claude API
- User can delete all data via `/settings/privacy`
- Data retention: 90 days after account deletion

## Deployment Architecture

**Production Stack:**

```
┌─────────────────────────────────────────┐
│           Cloudflare CDN                │
│         (Frontend + Assets)             │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│         Vercel (Next.js)                │
│    - Static Site Generation             │
│    - API Routes (Edge Functions)        │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│      Railway (Backend)                  │
│  ┌──────────┐  ┌──────────┐            │
│  │ FastAPI  │  │  Celery  │            │
│  │Container │  │ Workers  │            │
│  └──────────┘  └──────────┘            │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│        Managed Services                 │
│  ┌──────────┐  ┌──────────┐            │
│  │PostgreSQL│  │  Redis   │            │
│  │ (Railway)│  │(Railway) │            │
│  └──────────┘  └──────────┘            │
│  ┌──────────┐                          │
│  │ChromaDB  │                          │
│  │(Self-host│                          │
│  └──────────┘                          │
└─────────────────────────────────────────┘
```

## Scalability Plan

**Current (Single User):**
- 1 FastAPI instance
- 1 Celery worker
- Shared PostgreSQL

**Future (10-100 Users):**
- 3 FastAPI instances (load balanced)
- 5 Celery workers
- Dedicated PostgreSQL instance
- Redis cluster

**Enterprise (1000+ Users):**
- Auto-scaling FastAPI (5-20 instances)
- Celery worker pool (10-50 workers)
- PostgreSQL read replicas
- Redis cluster with Sentinel
- ChromaDB cluster

## Monitoring & Observability

**Metrics:**
- Request latency (p50, p95, p99)
- LLM API call duration
- Task sync success rate
- Celery queue length
- Database query performance

**Logging:**
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Centralized via Logtail or DataDog

**Alerts:**
- LLM API failure rate > 5%
- Database connection pool exhausted
- Celery queue length > 1000
- Sync failure rate > 10%

## Error Handling

**LLM API Failures:**
1. Retry 3 times with exponential backoff
2. If still failing, mark task for manual review
3. User sees "Analysis pending" state

**TickTick Sync Failures:**
1. Log error to sync_logs table
2. Retry sync in next 5-minute cycle
3. Alert user if >3 consecutive failures

**Database Connection Loss:**
1. Connection pool handles reconnection
2. Transactions are atomic (rollback on failure)
3. Background jobs retry automatically

---

**Last Updated:** 2024-12-09
