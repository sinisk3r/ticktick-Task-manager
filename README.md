# Context - AI Task Intelligence Layer

> LLM-powered task management system that sits on top of TickTick to auto-prioritize, schedule, and protect your wellbeing.

## 🎯 Vision

Stop losing time to endless meetings and manual planning. Context intelligently manages your tasks across work, your wife's dental clinic, and personal life - all while ensuring you don't burn out.

## ✨ What It Does

- **Smart Task Intake**: Automatically analyzes tasks from TickTick, extracts urgency/importance, assigns to Eisenhower matrix
- **Workload Intelligence**: Tracks your capacity and warns when you're over-committed
- **Rest Reminders**: Actually tells you to take breaks based on work intensity
- **Email Drafts**: Generates context-aware emails for your tasks
- **Weekly Planning**: AI-powered weekly reviews and priority suggestions
- **Voice Capture**: Speak your tasks, they're transcribed and intelligently processed
- **Azure DevOps Sync**: Auto-creates work items from your tasks

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- TickTick account
- Claude API key (Anthropic)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/context.git
cd context

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
```

### 2. Environment Variables

Create `.env` files in both backend and frontend:

**backend/.env:**
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

**frontend/.env.local:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Database Setup

```bash
cd backend
alembic upgrade head
```

### 4. Run Development Servers

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

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 4 - Redis:**
```bash
redis-server
```

Navigate to `http://localhost:3000`

## 📁 Project Structure

```
context/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes
│   │   │   ├── auth.py       # OAuth flows
│   │   │   ├── tasks.py      # Task CRUD
│   │   │   ├── calendar.py   # Calendar operations
│   │   │   ├── analytics.py  # Workload intelligence
│   │   │   └── sync.py       # Webhook handlers
│   │   ├── services/         # Business logic
│   │   │   ├── ticktick.py   # TickTick integration
│   │   │   ├── llm.py        # Claude API calls
│   │   │   ├── scheduler.py  # Calendar blocking
│   │   │   ├── email.py      # Email draft generation
│   │   │   └── azure.py      # Azure DevOps integration
│   │   ├── models/           # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── task.py
│   │   │   ├── calendar_event.py
│   │   │   └── sync_log.py
│   │   ├── workers/          # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   ├── sync_tasks.py
│   │   │   └── analysis.py
│   │   ├── core/             # Config & utilities
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   └── main.py           # FastAPI app
│   ├── alembic/              # Database migrations
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js 13+ app directory
│   │   │   ├── page.tsx      # Dashboard
│   │   │   ├── tasks/
│   │   │   └── settings/
│   │   ├── components/
│   │   │   ├── TaskBoard.tsx      # Eisenhower matrix
│   │   │   ├── TaskCard.tsx
│   │   │   ├── WeeklyView.tsx
│   │   │   ├── WorkloadChart.tsx
│   │   │   └── EmailDraftModal.tsx
│   │   ├── lib/
│   │   │   ├── api.ts        # Backend API client
│   │   │   ├── hooks.ts      # React hooks
│   │   │   └── utils.ts
│   │   └── styles/
│   ├── public/
│   └── package.json
│
└── docs/                     # Documentation (you are here)
    ├── README.md
    ├── ARCHITECTURE.md
    ├── FEATURES.md
    ├── TECH_STACK.md
    ├── API_INTEGRATION.md
    ├── MVP_ROADMAP.md
    ├── DATABASE_SCHEMA.md
    ├── BACKEND_STRUCTURE.md
    ├── FRONTEND_STRUCTURE.md
    └── DEVELOPMENT_GUIDE.md
```

## 🎨 UI Design

**Color Scheme:** Dark Mode
- Background: `#1f2937` (gray-800)
- Cards: `#374151` (gray-700)
- Accents: `#60a5fa` (blue-400)
- Text: `#f9fafb` (gray-50)

**Button Style:** Minimal - clean, flat buttons with subtle hover states

**Layout:** Compact - maximize information density, minimal whitespace

**Dashboard:** Matrix First - Eisenhower matrix is the primary view

## 📊 Features by Phase

### Phase 1: MVP (Weeks 1-4)
- ✅ Smart Task Intake
- ✅ Basic Dashboard  
- ✅ Manual Overrides

### Phase 2: Integrations (Weeks 5-8)
- ✅ Contextual Email Drafts
- ✅ Workload Intelligence
- ✅ Rest Reminders

### Phase 3: Advanced (Weeks 9-10.5)
- ✅ Auto Azure DevOps Creation
- ✅ Weekly Planning Assistant
- ✅ Voice Note Capture

**Estimated Timeline:** 10.5 weeks  
**Average Complexity:** Medium

## 🔧 Development Workflow

1. **Feature Branch**: Create from `main`
```bash
git checkout -b feature/task-intake
```

2. **Develop**: Write code + tests
3. **Test Locally**: Run test suite
```bash
# Backend
pytest

# Frontend
npm test
```

4. **Commit**: Use conventional commits
```bash
git commit -m "feat: implement LLM priority scoring"
```

5. **PR**: Open pull request to `main`
6. **Deploy**: Merge triggers CI/CD pipeline

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest -v

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## 📖 Documentation

- [Architecture](./ARCHITECTURE.md) - System design and data flows
- [Features](./FEATURES.md) - Detailed feature specifications
- [Tech Stack](./TECH_STACK.md) - Technology choices and rationale
- [API Integration](./API_INTEGRATION.md) - External API setup guides
- [MVP Roadmap](./MVP_ROADMAP.md) - Week-by-week implementation plan
- [Database Schema](./DATABASE_SCHEMA.md) - Database design
- [Backend Structure](./BACKEND_STRUCTURE.md) - Backend code organization
- [Frontend Structure](./FRONTEND_STRUCTURE.md) - Frontend code organization
- [Development Guide](./DEVELOPMENT_GUIDE.md) - Setup and debugging

## 🤝 Contributing

This is a personal project, but feedback and suggestions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

MIT License - feel free to use this for your own productivity system!

## 🙏 Acknowledgments

- TickTick for the excellent task management API
- Anthropic for Claude API
- Motion and Reclaim.ai for inspiration

---

**Built by Srikar Kandikonda** | [GitHub](https://github.com/yourusername) | [LinkedIn](https://linkedin.com/in/yourprofile)
