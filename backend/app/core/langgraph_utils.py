"""
Shared utilities for LangGraph PostgreSQL integration.

Provides helper functions for formatting connection strings and checking table existence.
"""

import logging
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

logger = logging.getLogger(__name__)


def format_pg_url_for_langgraph(db_url: str) -> str:
    """
    Convert SQLAlchemy asyncpg URL to PostgreSQL URL format expected by LangGraph.
    
    LangGraph uses psycopg3 which expects:
    - postgresql:// (not postgresql+asyncpg://)
    - SSL parameters in query string (sslmode=disable for local dev)
    
    Args:
        db_url: SQLAlchemy database URL (e.g., postgresql+asyncpg://user:pass@host:port/db)
        
    Returns:
        PostgreSQL connection string for LangGraph
    """
    # Replace asyncpg driver
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Parse URL to add SSL parameters if not present
    parsed = urlparse(pg_url)
    query_params = parse_qs(parsed.query)
    
    # Add sslmode=disable for local development if not specified
    if "sslmode" not in query_params:
        query_params["sslmode"] = ["disable"]
    
    # Reconstruct URL with updated query
    new_query = urlencode(query_params, doseq=True)
    formatted_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    
    logger.debug(f"Formatted DB URL for LangGraph: {formatted_url.replace(parsed.password if parsed.password else '', '***')}")
    return formatted_url


async def check_checkpoint_tables_exist(pg_url: str) -> bool:
    """
    Check if checkpoint tables already exist in the database.
    
    This allows us to skip setup() if tables exist, avoiding hangs
    on stuck index creation operations.
    """
    try:
        import psycopg
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('checkpoints', 'checkpoint_writes', 'checkpoint_blobs', 'checkpoint_migrations')
                """)
                result = await cur.fetchone()
                if result and result[0] is not None:
                    return result[0] >= 4  # All 4 tables should exist
                return False
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Failed to check checkpoint tables: {e}, will try setup()")
        return False


async def check_checkpoint_schema_up_to_date(pg_url: str) -> bool:
    """
    Check if checkpoint_writes table has the task_path column (required by LangGraph 3.0.2+).
    
    Returns:
        True if schema is up-to-date, False if it needs migration
    """
    try:
        import psycopg
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                # Check if task_path column exists in checkpoint_writes
                await cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = 'checkpoint_writes'
                    AND column_name = 'task_path';
                """)
                result = await cur.fetchone()
                return result is not None
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Failed to check checkpoint schema: {e}, will assume outdated")
        return False


async def check_store_tables_exist(pg_url: str) -> bool:
    """
    Check if store tables already exist in the database.
    
    This allows us to skip setup() if tables exist, avoiding hangs
    on stuck index creation operations.
    """
    try:
        import psycopg
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('store', 'store_migrations')
                """)
                result = await cur.fetchone()
                if result and result[0] is not None:
                    return result[0] >= 2  # Both tables should exist
                return False
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Failed to check store tables: {e}, will try setup()")
        return False

