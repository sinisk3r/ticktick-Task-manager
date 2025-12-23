# Fix AsyncPostgresSaver Database Connection Issue

## Problem Statement

After implementing Chat UX v2 with AsyncPostgresSaver and AsyncPostgresStore, the database has become very slow and basic commands like "get tasks" are not working. The issue is caused by **incorrect async context manager usage**.

## Root Cause Analysis

**Current (Incorrect) Pattern:**
```python
# In create_context_agent() function
checkpointer_cm = AsyncPostgresSaver.from_conn_string(pg_connection_string)
checkpointer = await checkpointer_cm.__aenter__()  # ❌ NEVER exits!
```

**Problems:**
1. We enter the context manager but **never exit it**
2. Database connections remain open indefinitely
3. Connection pool exhaustion causes slowness
4. No proper cleanup on errors

**Correct Pattern (from LangChain docs):**
```python
# At APPLICATION level (API endpoint)
async with (
    AsyncPostgresStore.from_conn_string(DB_URI) as store,
    AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer,
):
    # Use checkpointer/store here
    graph = builder.compile(checkpointer=checkpointer, store=store)
    result = await graph.ainvoke(...)
# Connections automatically closed when exiting context
```

## Solution Design

### Option 1: Pass Checkpointer/Store as Parameters (RECOMMENDED)

**Approach:**
1. Create checkpointer/store **once** at application startup or API level
2. Pass them as parameters to `create_context_agent()`
3. Reuse the same instances across requests
4. Let the API framework manage lifecycle

**Pros:**
- Proper connection management
- Reuses connections (better performance)
- Follows LangChain best practices
- Simpler code

**Cons:**
- Requires managing global/request-scoped instances

### Option 2: Remove Persistent Memory Temporarily

**Approach:**
1. Disable AsyncPostgresSaver and AsyncPostgresStore
2. Fall back to MemorySaver (in-memory only)
3. Get the app working again quickly
4. Re-add persistent memory later with correct pattern

**Pros:**
- Quick fix
- No database connection issues
- Agent still works

**Cons:**
- Loses persistent memory features
- Temporary workaround only

## Recommended Implementation: Option 1

### Changes Required

#### 1. Update `backend/app/agent/main_agent.py`

**Remove:**
- All async context manager `__aenter__()` calls
- `setup()` calls inside agent creation

**Change:**
```python
async def create_context_agent(
    user_id: int,
    db: AsyncSession,
    llm: Optional[BaseChatModel] = None,
    checkpointer: Optional[AsyncPostgresSaver] = None,  # NEW: Accept as param
    store: Optional[AsyncPostgresStore] = None,  # NEW: Accept as param
) -> Any:
    """Create Chat UX v2 agent with optional persistent memory."""

    # Use provided checkpointer/store or fall back to None
    # (agent works fine without them, just no persistence)

    agent = create_react_agent(
        model=llm,
        tools=tools_list,
        prompt=full_system_prompt,
        checkpointer=checkpointer,  # Use passed instance
    )

    agent._store = store  # Use passed instance
    return agent
```

#### 2. Update `backend/app/api/agent.py`

**Add module-level singletons:**
```python
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

# Global instances (created once, reused)
_checkpointer: Optional[AsyncPostgresSaver] = None
_store: Optional[AsyncPostgresStore] = None
_checkpointer_lock = asyncio.Lock()
_store_lock = asyncio.Lock()

async def get_checkpointer() -> AsyncPostgresSaver:
    """Get or create global checkpointer instance."""
    global _checkpointer
    if _checkpointer is None:
        async with _checkpointer_lock:
            if _checkpointer is None:
                pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
                cm = AsyncPostgresSaver.from_conn_string(pg_url)
                _checkpointer = await cm.__aenter__()
                await _checkpointer.setup()
    return _checkpointer

async def get_store() -> AsyncPostgresStore:
    """Get or create global store instance."""
    global _store
    if _store is None:
        async with _store_lock:
            if _store is None:
                pg_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
                cm = AsyncPostgresStore.from_conn_string(pg_url)
                _store = await cm.__aenter__()
                await _store.setup()
    return _store
```

**Update stream_agent() endpoint:**
```python
@router.post("/stream")
async def stream_agent(payload: StreamRequest, db: AsyncSession = Depends(get_db)):
    """Stream agent events with proper connection management."""

    async def event_generator():
        try:
            # Get or create global instances
            checkpointer = await get_checkpointer()
            store = await get_store()

            if payload.use_v2_agent:
                agent = await create_context_agent(
                    user_id=payload.user_id,
                    db=db,
                    checkpointer=checkpointer,  # Pass instance
                    store=store,  # Pass instance
                )
            else:
                agent = await create_agent(user_id=payload.user_id, db=db)

            # ... rest of the streaming logic
```

#### 3. Add Cleanup on Application Shutdown (Optional but Recommended)

**In `backend/app/main.py`:**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown - cleanup connections
    from app.api.agent import _checkpointer, _store
    if _checkpointer:
        try:
            await _checkpointer.__aexit__(None, None, None)
        except:
            pass
    if _store:
        try:
            await _store.__aexit__(None, None, None)
        except:
            pass

app = FastAPI(lifespan=lifespan)
```

## Alternative: Simpler Quick Fix (If Option 1 is Complex)

**Disable persistent memory temporarily:**

```python
# In create_context_agent()
checkpointer = None  # Disable for now
store = None  # Disable for now

# Agent still works, just no persistence
agent = create_react_agent(
    model=llm,
    tools=tools_list,
    prompt=full_system_prompt,
    checkpointer=None,  # Use MemorySaver in create_react_agent by default
)
```

This gets the app working immediately while we implement the proper fix.

## Testing Plan

1. **Test basic agent functionality** - "get tasks" should work
2. **Test chat** - Should respond without slowness
3. **Test memory (if enabled)** - Conversation history persists
4. **Monitor database connections** - Should not accumulate
5. **Test under load** - Multiple concurrent requests

## Success Criteria

- ✅ "get tasks" and basic commands work normally
- ✅ No database connection leaks
- ✅ Agent responds quickly (< 2 seconds for simple queries)
- ✅ Memory persists across sessions (if enabled)
- ✅ No errors in logs about connection pool exhaustion

## Critical Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/agent/main_agent.py` | MODIFY | Accept checkpointer/store as parameters |
| `backend/app/agent/memory/store.py` | REMOVE | Delete singleton pattern (not needed) |
| `backend/app/api/agent.py` | MODIFY | Create global checkpointer/store instances |
| `backend/app/main.py` | MODIFY | Add lifespan cleanup (optional) |

## Rollback Plan

If the fix doesn't work:
1. Set `use_v2_agent: false` in frontend (use legacy agent)
2. Or disable checkpointer/store in `create_context_agent()` (pass None)
3. App works normally without persistent memory
