# Code Review Prompt

When reviewing code in the Context project, pay special attention to:

## Security
- Are API keys/secrets properly stored in environment variables?
- Are user tokens encrypted at rest?
- Is input validation performed on all endpoints?
- Are SQL injection vulnerabilities prevented (using SQLAlchemy properly)?
- Is rate limiting implemented for expensive operations?
- Are OAuth tokens refreshed securely?

## Architecture Patterns
- Does the code follow the service layer pattern?
- Are database operations properly async with SQLAlchemy 2.0?
- Are external API calls wrapped with retry logic (tenacity)?
- Are background tasks using Celery for async processing?
- Is Redis caching used appropriately with correct TTLs?
- Are WebSocket updates sent for real-time changes?

## Error Handling
- Are errors logged with appropriate context?
- Is there retry logic for transient failures?
- Are users shown meaningful error messages?
- Are LLM failures handled gracefully with fallbacks?
- Are database transactions properly rolled back on errors?

## Performance
- Are database queries using proper joins (not N+1 queries)?
- Are expensive operations cached in Redis?
- Are LLM calls minimized and cached when possible?
- Are database indexes present on foreign keys and frequently queried fields?
- Is pagination implemented for list endpoints?

## LLM Integration
- Are prompts versioned in backend/app/prompts/?
- Is the LLM response validated before parsing?
- Is there a fallback if JSON parsing fails?
- Are token counts optimized?
- Is response caching implemented?

## Testing
- Are there tests for happy path and error cases?
- Are external APIs properly mocked?
- Are database transactions tested?
- Are async operations tested correctly?

## Code Style
- Are type hints used throughout (Python and TypeScript)?
- Are async/await used consistently?
- Are imports organized properly?
- Is the code following existing patterns in the codebase?

Prioritize feedback on security, data integrity, and user experience over stylistic preferences.
