"""
Persistent memory management for LangGraph agents.

Provides global instances of AsyncPostgresSaver and AsyncPostgresStore
with health checks and automatic reconnection.
"""

import asyncio
import logging
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore

from app.core.config import settings
from app.core.langgraph_utils import (
    format_pg_url_for_langgraph,
    check_checkpoint_tables_exist,
    check_store_tables_exist,
    check_checkpoint_schema_up_to_date,
)

logger = logging.getLogger(__name__)

# Global instances for Chat UX v2 persistent memory
# Initialized at application startup, cleaned up at shutdown
_checkpointer: Optional[AsyncPostgresSaver] = None
_store: Optional[AsyncPostgresStore] = None
_checkpointer_cm: Optional[AsyncPostgresSaver] = None  # Store the context manager to keep it alive
_store_cm: Optional[AsyncPostgresStore] = None  # Store the context manager to keep it alive


async def initialize_persistent_memory() -> tuple[bool, bool]:
    """
    Initialize persistent memory connections at application startup.
    
    Returns:
        Tuple of (checkpointer_initialized, store_initialized) booleans
    """
    global _checkpointer, _store, _checkpointer_cm, _store_cm
    
    checkpointer_ok = False
    store_ok = False
    
    try:
        logger.info("Initializing LangGraph persistent memory...")
        pg_url = format_pg_url_for_langgraph(settings.database_url)
        
        # Initialize checkpointer
        try:
            logger.info("Creating AsyncPostgresSaver...")
            _checkpointer_cm = AsyncPostgresSaver.from_conn_string(pg_url)
            _checkpointer = await _checkpointer_cm.__aenter__()
            logger.info("AsyncPostgresSaver context manager entered")
            
            # Check if tables exist and schema is up-to-date before calling setup()
            tables_exist = await check_checkpoint_tables_exist(pg_url)
            schema_up_to_date = await check_checkpoint_schema_up_to_date(pg_url) if tables_exist else False
            
            if tables_exist and schema_up_to_date:
                logger.info("Checkpoint tables exist with up-to-date schema, skipping setup()")
            else:
                if tables_exist and not schema_up_to_date:
                    logger.warning("Checkpoint tables exist but schema is outdated, running setup() to migrate...")
                else:
                    logger.info("Checkpoint tables don't exist, calling setup()...")
                try:
                    await asyncio.wait_for(_checkpointer.setup(), timeout=30.0)
                    logger.info("AsyncPostgresSaver setup() completed")
                except asyncio.TimeoutError:
                    logger.error("AsyncPostgresSaver setup() timed out after 30 seconds")
                    logger.warning("This may be due to stuck index creation operations.")
                    logger.warning("Run: python backend/scripts/fix_index_locks.py to fix stuck operations")
                    # Clean up on timeout
                    try:
                        await _checkpointer_cm.__aexit__(None, None, None)
                    except Exception:
                        pass
                    _checkpointer = None
                    _checkpointer_cm = None
                    raise
            logger.info("AsyncPostgresSaver initialized and ready")
            checkpointer_ok = True
        except Exception as e:
            logger.exception(f"Failed to initialize AsyncPostgresSaver: {e}")
            _checkpointer = None
            _checkpointer_cm = None
            logger.warning("Continuing without persistent memory checkpointer")
        
        # Initialize store
        try:
            logger.info("Creating AsyncPostgresStore...")
            _store_cm = AsyncPostgresStore.from_conn_string(pg_url)
            _store = await _store_cm.__aenter__()
            logger.info("AsyncPostgresStore context manager entered")
            
            # Check if tables exist before calling setup()
            tables_exist = await check_store_tables_exist(pg_url)
            if tables_exist:
                logger.info("Store tables already exist, skipping setup()")
            else:
                logger.info("Store tables don't exist, calling setup()...")
                try:
                    await asyncio.wait_for(_store.setup(), timeout=30.0)
                    logger.info("AsyncPostgresStore setup() completed")
                except asyncio.TimeoutError:
                    logger.error("AsyncPostgresStore setup() timed out after 30 seconds")
                    logger.warning("This may be due to stuck index creation operations.")
                    logger.warning("Run: python backend/scripts/fix_index_locks.py to fix stuck operations")
                    # Clean up on timeout
                    try:
                        await _store_cm.__aexit__(None, None, None)
                    except Exception:
                        pass
                    _store = None
                    _store_cm = None
                    raise
            logger.info("AsyncPostgresStore initialized and ready")
            store_ok = True
        except Exception as e:
            logger.exception(f"Failed to initialize AsyncPostgresStore: {e}")
            _store = None
            _store_cm = None
            logger.warning("Continuing without persistent memory store")
        
    except Exception as e:
        logger.exception(f"Unexpected error during persistent memory initialization: {e}")
    
    return checkpointer_ok, store_ok


async def cleanup_persistent_memory():
    """Clean up persistent memory connections at application shutdown."""
    global _checkpointer_cm, _store_cm
    
    if _checkpointer_cm is not None:
        try:
            logger.info("Closing AsyncPostgresSaver connection...")
            await _checkpointer_cm.__aexit__(None, None, None)
            logger.info("AsyncPostgresSaver connection closed")
        except Exception as e:
            logger.error(f"Error during checkpointer cleanup: {e}")
    
    if _store_cm is not None:
        try:
            logger.info("Closing AsyncPostgresStore connection...")
            await _store_cm.__aexit__(None, None, None)
            logger.info("AsyncPostgresStore connection closed")
        except Exception as e:
            logger.error(f"Error during store cleanup: {e}")


async def _check_connection_health(checkpointer: AsyncPostgresSaver) -> bool:
    """
    Check if the checkpointer connection is healthy.
    
    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        # Try a simple operation to verify connection
        # We'll try to list checkpoints (this is a lightweight operation)
        # If it fails, the connection is likely closed
        # Use aiter() to get the async iterator and try to get first item
        iterator = checkpointer.alist({"configurable": {"thread_id": "__health_check__"}})
        try:
            await iterator.__anext__()
        except StopAsyncIteration:
            pass  # Empty list is fine, connection works
        return True
    except Exception as e:
        # Check for specific connection errors
        error_str = str(e).lower()
        if "connection is closed" in error_str or "connection" in error_str:
            logger.warning(f"Checkpointer connection health check failed: {e}")
            return False
        # Other errors might be okay (e.g., table doesn't exist yet)
        logger.debug(f"Checkpointer health check returned error (may be okay): {e}")
        return True  # Assume connection is okay if error is not connection-related


async def _check_store_connection_health(store: AsyncPostgresStore) -> bool:
    """
    Check if the store connection is healthy.
    
    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        # Try a simple operation to verify connection
        # We'll try to get a non-existent key (this is a lightweight operation)
        await store.aget(["__health_check__"])
        return True
    except Exception as e:
        # It's okay if the key doesn't exist, we just want to verify the connection works
        error_str = str(e).lower()
        if "not found" in error_str or "does not exist" in error_str:
            return True  # Connection works, key just doesn't exist
        logger.warning(f"Store connection health check failed: {e}")
        return False


async def _reconnect_checkpointer() -> bool:
    """
    Attempt to reconnect the checkpointer if it's unhealthy.
    
    Returns:
        True if reconnection succeeded, False otherwise
    """
    global _checkpointer, _checkpointer_cm
    
    try:
        logger.info("Attempting to reconnect AsyncPostgresSaver...")
        pg_url = format_pg_url_for_langgraph(settings.database_url)
        
        # Clean up old connection if it exists
        if _checkpointer_cm is not None:
            try:
                await _checkpointer_cm.__aexit__(None, None, None)
            except Exception:
                pass
        
        # Create new connection
        _checkpointer_cm = AsyncPostgresSaver.from_conn_string(pg_url)
        _checkpointer = await _checkpointer_cm.__aenter__()
        
        # Verify connection is healthy
        if await _check_connection_health(_checkpointer):
            logger.info("AsyncPostgresSaver reconnected successfully")
            return True
        else:
            logger.error("AsyncPostgresSaver reconnected but health check failed")
            return False
            
    except Exception as e:
        logger.exception(f"Failed to reconnect AsyncPostgresSaver: {e}")
        _checkpointer = None
        _checkpointer_cm = None
        return False


async def _reconnect_store() -> bool:
    """
    Attempt to reconnect the store if it's unhealthy.
    
    Returns:
        True if reconnection succeeded, False otherwise
    """
    global _store, _store_cm
    
    try:
        logger.info("Attempting to reconnect AsyncPostgresStore...")
        pg_url = format_pg_url_for_langgraph(settings.database_url)
        
        # Clean up old connection if it exists
        if _store_cm is not None:
            try:
                await _store_cm.__aexit__(None, None, None)
            except Exception:
                pass
        
        # Create new connection
        _store_cm = AsyncPostgresStore.from_conn_string(pg_url)
        _store = await _store_cm.__aenter__()
        
        # Verify connection is healthy
        if await _check_store_connection_health(_store):
            logger.info("AsyncPostgresStore reconnected successfully")
            return True
        else:
            logger.error("AsyncPostgresStore reconnected but health check failed")
            return False
            
    except Exception as e:
        logger.exception(f"Failed to reconnect AsyncPostgresStore: {e}")
        _store = None
        _store_cm = None
        return False


def get_checkpointer() -> Optional[AsyncPostgresSaver]:
    """
    Get the global AsyncPostgresSaver instance (initialized at startup).
    
    Returns None if initialization failed or connection is unhealthy.
    """
    return _checkpointer


def get_store() -> Optional[AsyncPostgresStore]:
    """
    Get the global AsyncPostgresStore instance (initialized at startup).
    
    Returns None if initialization failed or connection is unhealthy.
    """
    return _store


async def ensure_checkpointer_healthy() -> Optional[AsyncPostgresSaver]:
    """
    Get checkpointer, checking health and reconnecting if necessary.
    
    Returns:
        Healthy AsyncPostgresSaver instance, or None if unavailable
    """
    global _checkpointer
    
    if _checkpointer is None:
        return None
    
    # Check connection health
    if not await _check_connection_health(_checkpointer):
        logger.warning("Checkpointer connection unhealthy, attempting reconnection...")
        if not await _reconnect_checkpointer():
            logger.error("Failed to reconnect checkpointer, returning None")
            return None
    
    return _checkpointer


async def ensure_store_healthy() -> Optional[AsyncPostgresStore]:
    """
    Get store, checking health and reconnecting if necessary.
    
    Returns:
        Healthy AsyncPostgresStore instance, or None if unavailable
    """
    global _store
    
    if _store is None:
        return None
    
    # Check connection health
    if not await _check_store_connection_health(_store):
        logger.warning("Store connection unhealthy, attempting reconnection...")
        if not await _reconnect_store():
            logger.error("Failed to reconnect store, returning None")
            return None
    
    return _store

