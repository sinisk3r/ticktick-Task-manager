# Technology Stack

## Overview

This document explains the technology choices for Context and the rationale behind each decision.

---

## Backend: FastAPI + Python

### Why FastAPI?

**Chosen:** FastAPI  
**Alternatives Considered:** Flask, Django, Express.js

**Rationale:**
1. **Async Support:** Native async/await for concurrent LLM API calls
2. **Type Safety:** Pydantic models catch errors early
3. **Auto Documentation:** OpenAPI spec generated automatically
4. **Fast Development:** Less boilerplate than Django
5. **Performance:** Comparable to Node.js (Starlette + uvicorn)
6. **Python Ecosystem:** Easy integration with ML/AI libraries

**Trade-offs:**
- ❌ Smaller community than Flask/Django
- ❌ Fewer plugins/extensions
- ✅ But modern, well-designed, perfect for APIs

**Example:**
```python
@app.post("/api/tasks")
async def create_task(task: TaskCreate, user: User = Depends(get_current_user)):
    # Type checking at runtime
    # Async DB calls
    # Auto API docs
    return await task_service.create(task, user.id)
```

---

## Database: PostgreSQL

### Why PostgreSQL?

**Chosen:** PostgreSQL 15  
**Alternatives Considered:** MySQL, MongoDB, SQLite

**Rationale:**
1. **Relational Data:** Tasks, users, events have clear relationships
2. **JSON Support:** JSONB for flexible fields (tags, blockers)
3. **Full-Text Search:** For task search functionality
4. **Reliability:** ACID compliance, proven at scale
5. **Free Tier:** Railway provides free PostgreSQL

**Trade-offs:**
- ❌ More complex than SQLite for local dev
- ❌ Requires migration management
- ✅ But scales well, robust, industry standard

**Schema Example:**
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    urgency_score INT,
    importance_score INT,
    blockers JSONB,  -- Flexible storage
    tags JSONB,      -- Array of strings
    ...
);

CREATE INDEX idx_tasks_search ON tasks 
USING GIN (to_tsvector('english', title || ' ' || description));
```

---

## ORM: SQLAlchemy

### Why SQLAlchemy?

**Chosen:** SQLAlchemy 2.0  
**Alternatives Considered:** Django ORM, Tortoise ORM, raw SQL

**Rationale:**
1. **Mature:** 15+ years of development
2. **Flexible:** Can drop down to raw SQL when needed
3. **Async Support:** SQLAlchemy 2.0 has native async
4. **Migration Tools:** Alembic works seamlessly
5. **Type Hints:** Good IDE support

**Example:**
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_user_tasks(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(Task)
        .where(Task.user_id == user_id)
        .where(Task.status == 'pending')
        .order_by(Task.urgency_score.desc())
    )
    return result.scalars().all()
```

---

## Cache/Queue: Redis

### Why Redis?

**Chosen:** Redis 7  
**Alternatives Considered:** Memcached, Amazon SQS, RabbitMQ

**Rationale:**
1. **Dual Purpose:** Cache + message queue in one
2. **Simple:** Key-value store, easy to reason about
3. **Fast:** In-memory, microsecond latency
4. **Celery Integration:** Works perfectly with Celery
5. **Free Tier:** Railway provides free Redis

**Use Cases:**
```python
# Caching
await redis.set(f"user:{user_id}:tasks", json.dumps(tasks), ex=300)

# Rate limiting
count = await redis.incr(f"ratelimit:user:{user_id}:llm_calls")
await redis.expire(f"ratelimit:user:{user_id}:llm_calls", 3600)

# Celery task queue
@celery.task
def analyze_task(task_id):
    ...
```

---

## Background Jobs: Celery

### Why Celery?

**Chosen:** Celery 5  
**Alternatives Considered:** Huey, APScheduler, Dramatiq

**Rationale:**
1. **Battle-Tested:** Industry standard for Python async tasks
2. **Features:** Scheduling, retries, monitoring
3. **Redis Integration:** Use Redis as broker + result backend
4. **Scalable:** Can add workers horizontally
5. **Monitoring:** Flower dashboard included

**Example:**
```python
@celery.task(bind=True, max_retries=3)
def analyze_new_task(self, task_id: str):
    try:
        task = Task.get(task_id)
        analysis = llm_service.analyze(task)
        task.update(analysis)
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

**Trade-offs:**
- ❌ Requires separate worker process
- ❌ Can be complex to debug
- ✅ But worth it for reliability and features

---

## LLM: Claude API (Anthropic)

### Why Claude?

**Chosen:** Claude Sonnet 4.5  
**Alternatives Considered:** GPT-4, GPT-4o, Llama 3, Gemini

**Rationale:**
1. **Long Context:** 200K tokens (can include entire task history)
2. **Structured Output:** JSON mode works reliably
3. **Safety:** Less prone to jailbreaking
4. **Speed:** Fast inference times
5. **Cost:** Competitive pricing ($3/M input tokens)
6. **Personal Preference:** You're already familiar with it

**Use Cases:**
```python
# Task analysis
response = await anthropic.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{
        "role": "user",
        "content": f"Analyze this task: {task.title}\n{task.description}"
    }],
    system=TASK_ANALYSIS_PROMPT
)

# Email drafting
response = await anthropic.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=500,
    messages=[{
        "role": "user",
        "content": f"Draft email for: {task.title}"
    }],
    system=EMAIL_DRAFT_PROMPT
)
```

**Cost Estimation:**
- Task analysis: ~500 tokens in, ~200 out = $0.0021/task
- Email draft: ~300 tokens in, ~300 out = $0.0015/email
- **Monthly (100 tasks, 20 emails):** ~$0.20

**Fallback Plan:**
- If Claude API is down → queue tasks for later
- If costs spike → switch to GPT-4o-mini

---

## Embeddings: ChromaDB

### Why ChromaDB?

**Chosen:** ChromaDB (self-hosted)  
**Alternatives Considered:** Pinecone, Weaviate, FAISS

**Rationale:**
1. **Simple:** Embedded database, no separate service
2. **Free:** Open-source, self-hosted
3. **Python-Native:** Easy integration
4. **Fast:** Good enough for single-user scale
5. **Persistent:** Stores on disk

**Use Case:**
```python
# Store task embedding
import chromadb
client = chromadb.Client()
collection = client.create_collection("tasks")

# Add task
embedding = get_embedding(task.title + task.description)
collection.add(
    ids=[task.id],
    embeddings=[embedding],
    metadatas=[{"user_id": user.id, "quadrant": task.quadrant}]
)

# Find similar tasks
results = collection.query(
    query_embeddings=[new_task_embedding],
    n_results=5
)
```

**Trade-offs:**
- ❌ Not as scalable as Pinecone
- ❌ No managed hosting
- ✅ But free and simple for MVP

---

## Frontend: Next.js 14 + React

### Why Next.js?

**Chosen:** Next.js 14 (App Router)  
**Alternatives Considered:** Vite + React, SvelteKit, Remix

**Rationale:**
1. **Full-Stack:** API routes + React in one framework
2. **SSR:** Fast initial page load
3. **Routing:** File-based routing is intuitive
4. **Optimization:** Image optimization, code splitting built-in
5. **Deployment:** Vercel integration is seamless
6. **TypeScript:** First-class support

**Example:**
```tsx
// app/page.tsx (Server Component)
export default async function Dashboard() {
  const tasks = await getTasks() // Runs on server
  return <EisenhowerMatrix tasks={tasks} />
}

// components/TaskCard.tsx (Client Component)
'use client'
export function TaskCard({ task }: { task: Task }) {
  const [isEditing, setIsEditing] = useState(false)
  // Interactive client-side logic
}
```

**Trade-offs:**
- ❌ Server Components learning curve
- ❌ Heavier than plain Vite
- ✅ But production-ready out of the box

---

## Styling: Tailwind CSS

### Why Tailwind?

**Chosen:** Tailwind CSS 3  
**Alternatives Considered:** CSS Modules, Styled Components, vanilla CSS

**Rationale:**
1. **Fast Development:** No need to name classes
2. **Consistency:** Design system built-in
3. **Dark Mode:** First-class support
4. **Compact:** Purges unused CSS
5. **Popular:** Large community, good docs

**Dark Mode Example:**
```tsx
<div className="bg-gray-800 dark:bg-gray-900 text-gray-50">
  <h1 className="text-2xl font-bold text-blue-400">Context</h1>
  <div className="grid grid-cols-2 gap-4">
    {/* Responsive grid */}
  </div>
</div>
```

**Trade-offs:**
- ❌ HTML gets verbose
- ❌ Not semantic
- ✅ But very fast to iterate

---

## UI Components: shadcn/ui

### Why shadcn/ui?

**Chosen:** shadcn/ui  
**Alternatives Considered:** Material UI, Chakra UI, Ant Design

**Rationale:**
1. **Copy-Paste:** No npm dependencies, you own the code
2. **Tailwind-Based:** Consistent with styling approach
3. **Accessible:** Built on Radix UI primitives
4. **Customizable:** Easy to modify
5. **Modern:** Clean, minimal design

**Example:**
```tsx
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader } from '@/components/ui/dialog'

<Dialog>
  <DialogContent>
    <DialogHeader>Edit Task</DialogHeader>
    <Button>Save Changes</Button>
  </DialogContent>
</Dialog>
```

**Trade-offs:**
- ❌ Manual updates (not npm package)
- ❌ Smaller component library than MUI
- ✅ But lightweight and flexible

---

## State Management: SWR + React Context

### Why SWR?

**Chosen:** SWR (Vercel)  
**Alternatives Considered:** React Query, Redux, Zustand

**Rationale:**
1. **Simple:** Minimal boilerplate
2. **Cache Management:** Automatic revalidation
3. **TypeScript:** Excellent type inference
4. **Small:** 4kb gzipped
5. **Vercel-Made:** Plays well with Next.js

**Example:**
```tsx
import useSWR from 'swr'

function Dashboard() {
  const { data: tasks, error, mutate } = useSWR('/api/tasks', fetcher)
  
  if (!tasks) return <Loading />
  if (error) return <Error />
  
  return <EisenhowerMatrix tasks={tasks} onUpdate={mutate} />
}
```

**For UI State:**
```tsx
// React Context for simple UI state
const ThemeContext = createContext()

// No need for Redux/Zustand for MVP
```

**Trade-offs:**
- ❌ Less powerful than React Query
- ❌ No dev tools
- ✅ But sufficient for our needs

---

## Deployment: Railway

### Why Railway?

**Chosen:** Railway  
**Alternatives Considered:** Heroku, Render, AWS, DigitalOcean

**Rationale:**
1. **Simple:** Deploy from GitHub in minutes
2. **All-in-One:** Database + Redis + App in one platform
3. **Free Tier:** $5/month credit (enough for MVP)
4. **Automatic Deploys:** Push to main → auto-deploy
5. **Environment Variables:** Easy management

**Services:**
```yaml
# railway.json
services:
  - name: backend
    source: ./backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    
  - name: worker
    source: ./backend
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A app.workers.celery_app worker
    
  - name: postgres
    image: postgres:15
    
  - name: redis
    image: redis:7
```

**Trade-offs:**
- ❌ Less control than AWS
- ❌ Can get expensive at scale
- ✅ But perfect for MVP

---

## Frontend Deployment: Vercel

### Why Vercel?

**Chosen:** Vercel  
**Alternatives Considered:** Netlify, Cloudflare Pages, self-host

**Rationale:**
1. **Next.js Creator:** Built for Next.js
2. **Free Tier:** Generous (100GB bandwidth/month)
3. **Fast:** Edge network worldwide
4. **Preview Deploys:** Every PR gets a URL
5. **Zero Config:** Push and deploy

**Trade-offs:**
- ❌ Vendor lock-in
- ❌ Expensive beyond free tier
- ✅ But unbeatable developer experience

---

## CI/CD: GitHub Actions

### Why GitHub Actions?

**Chosen:** GitHub Actions  
**Alternatives Considered:** CircleCI, Travis CI, GitLab CI

**Rationale:**
1. **Integrated:** Built into GitHub
2. **Free:** 2000 minutes/month on free plan
3. **Simple YAML:** Easy to configure
4. **Marketplace:** Tons of pre-built actions

**Example Workflow:**
```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest
      
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm install
      - run: npm test
```

---

## Monitoring: Sentry

### Why Sentry?

**Chosen:** Sentry  
**Alternatives Considered:** LogRocket, Rollbar, DataDog

**Rationale:**
1. **Error Tracking:** Catches backend + frontend errors
2. **Free Tier:** 5K errors/month
3. **Context:** Full stack traces, user context
4. **Integrations:** Slack notifications
5. **Performance:** Tracks slow API calls

**Setup:**
```python
# Backend
import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1
)

# Frontend
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
})
```

---

## Voice Transcription: Whisper API

### Why Whisper?

**Chosen:** OpenAI Whisper API  
**Alternatives Considered:** Google Speech-to-Text, AWS Transcribe, AssemblyAI

**Rationale:**
1. **Accuracy:** State-of-the-art transcription
2. **Cost:** $0.006/minute (very cheap)
3. **Simple:** Single API call
4. **Languages:** Supports 50+ languages
5. **No Training:** Works out of the box

**Usage:**
```python
import openai

audio_file = open("voice_note.mp3", "rb")
transcript = openai.Audio.transcribe("whisper-1", audio_file)
# Returns: { "text": "..." }
```

**Cost Estimation:**
- 30-second voice note = $0.003
- 50 voice notes/month = $0.15

---

## Decision Matrix

| Need | Options | Choice | Why |
|------|---------|--------|-----|
| Backend Framework | Flask, Django, FastAPI | **FastAPI** | Async, type-safe, modern |
| Database | MySQL, PostgreSQL, MongoDB | **PostgreSQL** | Relational + JSON, reliable |
| Cache/Queue | Redis, Memcached, RabbitMQ | **Redis** | Simple, dual-purpose |
| LLM | Claude, GPT-4, Gemini | **Claude** | Long context, reliable |
| Frontend | Vite, Next.js, SvelteKit | **Next.js** | Full-stack, SSR, popular |
| Styling | Tailwind, CSS Modules, Styled | **Tailwind** | Fast dev, consistent |
| Deployment | Heroku, Railway, AWS | **Railway** | Simple, all-in-one |

---

## Cost Breakdown (Monthly)

**Free Tier:**
- Railway: $5 credit (enough for MVP)
- Vercel: Free (under 100GB bandwidth)
- GitHub Actions: Free (under 2000 minutes)
- Sentry: Free (under 5K errors)

**Paid Services:**
- Claude API: ~$0.20 (100 tasks/month)
- Whisper API: ~$0.15 (50 voice notes/month)
- **Total: ~$0.35/month** 🎉

**At Scale (1000 users):**
- Railway: ~$50/month (upgraded plan)
- Claude API: ~$200/month
- Whisper API: ~$15/month
- Vercel: ~$20/month
- **Total: ~$285/month**

---

## Future Considerations

**If scaling beyond MVP:**
1. **Move to AWS/GCP** for more control
2. **Add read replicas** for PostgreSQL
3. **Redis cluster** for high availability
4. **CDN for static assets** (CloudFlare)
5. **Prometheus + Grafana** for metrics

**If costs are too high:**
1. **Switch to GPT-4o-mini** ($0.15/M tokens)
2. **Cache LLM responses** more aggressively
3. **Batch process** instead of real-time

---

**Last Updated:** 2024-12-09
