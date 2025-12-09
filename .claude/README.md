# Claude Code Configuration for Context

This directory contains custom commands and prompts to help Claude Code work more effectively with the Context project.

## Available Commands

### Feature Development
- `/new-feature` - Scaffold a new feature following Context's architecture
- `/analyze-prompt` - Analyze and improve LLM prompts for better accuracy
- `/test-scenario` - Create comprehensive tests for a feature or scenario
- `/api-docs` - Generate or update API documentation for endpoints

### Debugging & Optimization
- `/debug-llm` - Debug LLM integration issues in the task analysis pipeline
- `/celery-debug` - Debug Celery background task and queue problems
- `/optimize` - Identify and fix performance bottlenecks

### Database
- `/migration` - Create and review Alembic database migrations safely

## Usage Examples

```bash
# Start implementing a new feature
/new-feature Add a feature to suggest task dependencies based on embeddings

# Debug why tasks aren't being analyzed
/debug-llm

# Improve the task analysis prompt
/analyze-prompt task_analysis_v1.txt

# Create comprehensive tests
/test-scenario email draft generation

# Optimize database queries
/optimize

# Create a database migration
/migration Add priority_score_history JSONB field to tasks table

# Debug stuck Celery tasks
/celery-debug

# Document a new API endpoint
/api-docs /api/analytics/workload
```

## Prompts

- `code-review.md` - Guidelines for reviewing code in this project, focusing on security, architecture patterns, and Context-specific concerns

## Directory Structure

```
.claude/
├── commands/           # Custom slash commands
│   ├── new-feature.md
│   ├── analyze-prompt.md
│   ├── debug-llm.md
│   ├── migration.md
│   ├── optimize.md
│   ├── test-scenario.md
│   ├── api-docs.md
│   └── celery-debug.md
├── prompts/           # Reusable prompts
│   └── code-review.md
└── README.md          # This file
```

## Best Practices

1. **Use /new-feature** for any significant new functionality to ensure architectural consistency
2. **Use /analyze-prompt** before deploying new LLM prompts to production
3. **Use /migration** for all database schema changes to catch issues early
4. **Use /test-scenario** to ensure thorough test coverage for critical flows
5. **Use /optimize** periodically to keep the application performant
6. **Use /debug-llm** and /celery-debug** as first stops when encountering issues

## Contributing New Commands

When creating new commands:
1. Add a clear description in the frontmatter
2. Provide step-by-step instructions for Claude
3. Include code examples where appropriate
4. Reference relevant files in the codebase
5. Focus on Context-specific patterns and architecture
