"""
PostgreSQL-backed memory store for LangGraph agent.

Wraps AsyncPostgresStore from langgraph-checkpoint-postgres to provide
cross-session memory persistence for user preferences and learned facts.
"""
import logging
from typing import Optional
from langgraph.store.postgres import AsyncPostgresStore

logger = logging.getLogger(__name__)


# Global store instance (singleton pattern)
_store_instance: Optional[AsyncPostgresStore] = None


async def get_memory_store(connection_string: str) -> AsyncPostgresStore:
    """
    Get or create the global AsyncPostgresStore instance.

    This store is used for cross-session memory persistence:
    - User preferences (tone, work style)
    - Learned facts (project names, recurring patterns)
    - Work patterns (task creation times, completion rates)

    Args:
        connection_string: PostgreSQL connection URL

    Returns:
        Initialized AsyncPostgresStore instance

    Usage:
        store = await get_memory_store(settings.database_url)
        # Store is ready to use - tables created automatically
    """
    global _store_instance

    if _store_instance is None:
        logger.info("Initializing AsyncPostgresStore for agent memory")
        # from_conn_string() returns an async context manager - we need to enter it
        store_cm = AsyncPostgresStore.from_conn_string(connection_string)
        _store_instance = await store_cm.__aenter__()

        # Create tables if they don't exist (safe to call multiple times)
        await _store_instance.setup()

        logger.info("AsyncPostgresStore initialized and tables created")

    return _store_instance


async def initialize_store(connection_string: str) -> AsyncPostgresStore:
    """
    Initialize and set up the memory store with schema creation.

    This is a convenience function that both gets the store and
    ensures the database schema is created.

    Args:
        connection_string: PostgreSQL connection URL

    Returns:
        Initialized AsyncPostgresStore with tables created
    """
    store = await get_memory_store(connection_string)
    await store.setup()
    logger.info("AsyncPostgresStore schema initialized")
    return store
