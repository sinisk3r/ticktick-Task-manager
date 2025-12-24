# TODO: Fix and Re-enable Persistent Memory for Chat UX v2

## Current State

The Chat UX v2 agent is working but **persistent memory is temporarily disabled** to avoid connection issues with `AsyncPostgresSaver` and `AsyncPostgresStore`.

**Location:** `backend/app/api/agent.py`
- Flag: `DISABLE_PERSISTENT_MEMORY_TEMPORARILY = True` (line ~53)
- When this is `False`, the agent will attempt to use persistent memory

## The Problem

When persistent memory is enabled, the agent hangs with the error: **"the connection is closed"** (`psycopg.OperationalError`).

### Root Causes Identified

1. **Stuck Index Creation Operations**: Multiple `CREATE INDEX CONCURRENTLY` operations are stuck waiting on locks in the database, causing `setup()` to hang indefinitely.

2. **Connection Lifecycle Issue**: When manually calling `__aenter__()` on the `AsyncPostgresSaver`/`AsyncPostgresStore` context managers and storing them as singletons, the connection pool may be getting closed or not properly maintained.

3. **Context Manager Pattern**: The LangGraph documentation shows using `async with` blocks, but we're manually entering context managers to keep them alive as singletons. This may not be the correct pattern for long-lived connections.

## What's Already Implemented

✅ **Table Existence Checks**: Code checks if tables exist before calling `setup()`, avoiding hangs on stuck index operations.

✅ **Connection String Formatting**: Properly formats database URLs for LangGraph (adds `sslmode=disable`).

✅ **Timeout Protection**: 30-second timeout on `setup()` calls.

✅ **Graceful Degradation**: Agent continues without persistent memory if initialization fails.

✅ **Context Manager Storage**: Both the context manager and instance are stored to keep connections alive.

## What Needs to Be Fixed

### Option 1: Fix Stuck Index Operations (Recommended First Step)

1. **Cancel stuck operations**:
   ```bash
   cd backend
   # Connect to PostgreSQL and cancel stuck CREATE INDEX operations
   psql -h localhost -p 5433 -U context -d context
   ```
   
   Then run:
   ```sql
   -- Find stuck operations
   SELECT pid, state, wait_event_type, wait_event, query
   FROM pg_stat_activity
   WHERE query LIKE '%CREATE INDEX CONCURRENTLY%'
   AND state != 'idle';
   
   -- Cancel them (replace PID with actual process IDs)
   SELECT pg_cancel_backend(PID);
   ```

2. **Or drop and recreate indexes** if they're not critical:
   ```sql
   -- Check existing indexes
   SELECT indexname FROM pg_indexes 
   WHERE tablename LIKE 'checkpoint%' OR tablename LIKE 'store%';
   
   -- Drop problematic indexes if needed
   DROP INDEX CONCURRENTLY IF EXISTS <index_name>;
   ```

### Option 2: Fix Connection Lifecycle (If Option 1 Doesn't Work)

The issue might be that `AsyncPostgresSaver`/`AsyncPostgresStore` aren't designed to be used as long-lived singletons. Consider:

1. **Use connection pooling directly**: Instead of storing context managers, use psycopg connection pools and pass them to LangGraph.

2. **Recreate on connection errors**: Catch "connection is closed" errors and recreate the checkpointer/store instances.

3. **Use request-scoped connections**: Create checkpointer/store per request instead of as singletons (less efficient but more reliable).

### Option 3: Alternative Memory Backend

If PostgreSQL persistent memory continues to be problematic:

1. **Use Redis for checkpoints**: LangGraph supports Redis checkpoints
2. **Use in-memory with periodic saves**: Use MemorySaver but periodically save to database
3. **Use file-based checkpoints**: For development, use file-based checkpointing

## Testing Steps

Once you've made changes:

1. **Set the flag to False**:
   ```python
   DISABLE_PERSISTENT_MEMORY_TEMPORARILY = False
   ```

2. **Restart the backend**:
   ```bash
   ./init.sh restart backend
   ```

3. **Test the agent**:
   ```bash
   curl -X POST http://localhost:5400/api/agent/stream \
     -H "Content-Type: application/json" \
     -d '{"goal": "list my tasks", "user_id": 1, "use_v2_agent": true}'
   ```

4. **Check logs** for:
   - "Step 7: Checkpoint tables already exist, skipping setup()" (good)
   - "AsyncPostgresSaver initialized and ready" (good)
   - "the connection is closed" (bad - connection issue)
   - "setup() timed out" (bad - stuck operations)

5. **Test conversation persistence**:
   - Send a message: "Remember that I prefer morning meetings"
   - Send another message: "What did I tell you about meetings?"
   - The agent should remember the preference (if persistent memory is working)

## Key Files to Modify

- `backend/app/api/agent.py`:
  - `get_checkpointer()` function (lines ~150-234)
  - `get_store()` function (lines ~237-321)
  - `stream_agent()` function - persistent memory usage (lines ~362-391)

- `backend/app/main.py`:
  - Lifespan cleanup for context managers (lines ~44-68)

## Reference Documentation

- LangGraph AsyncPostgresSaver: https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/README.md
- LangGraph Memory: https://python.langchain.com/docs/langgraph/how-tos/memory/add-memory
- psycopg3 Connection Pooling: https://www.psycopg.org/psycopg3/docs/api/pool.html

## Success Criteria

✅ Agent responds without hanging  
✅ No "connection is closed" errors  
✅ Conversation history persists across requests (same thread_id)  
✅ User preferences are remembered across sessions  
✅ No stuck database operations  

## Notes

- The tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`, `checkpoint_migrations`, `store`, `store_migrations`) already exist in the database
- The connection string format is correct (`postgresql://...?sslmode=disable`)
- The issue is specifically with maintaining the connection pool lifecycle

