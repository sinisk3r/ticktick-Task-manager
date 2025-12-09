---
description: Scaffold a new feature following Context's architecture patterns
---

Help me implement a new feature following the Context project architecture.

When I use this command with a feature description, you should:

1. **Analyze the feature requirements** and determine:
   - Which layer(s) it affects (backend API, service, model, frontend, Celery worker)
   - Whether it needs LLM integration
   - Database schema changes required
   - External API integrations needed

2. **Create the implementation plan** as a todo list:
   - Database migrations (if needed)
   - Backend models (SQLAlchemy)
   - Service layer implementation
   - API endpoints (FastAPI routes)
   - Celery background tasks (if async processing needed)
   - Frontend components (React/Next.js)
   - API client updates (lib/api.ts)
   - Tests (backend pytest, frontend jest)

3. **Follow existing patterns**:
   - Use async/await throughout
   - Add proper error handling with retry logic
   - Include Redis caching where appropriate
   - Use TypeScript types in frontend
   - Follow the existing file structure in CLAUDE.md
   - Use shadcn/ui components for UI
   - Add WebSocket updates for real-time features

4. **Check for integration points**:
   - Does this affect task analysis flow?
   - Does it need to be triggered by webhooks?
   - Should it cache results in Redis?
   - Does it need rate limiting?

5. **Create the files** in the correct locations based on the architecture

After planning, ask me which components to implement first, then proceed systematically.
