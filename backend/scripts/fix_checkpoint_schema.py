#!/usr/bin/env python3
"""
Fix checkpoint table schema by checking for missing columns and either
running migrations or dropping/recreating tables.

Usage:
    python backend/scripts/fix_checkpoint_schema.py [--drop-tables]
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def _format_pg_url_for_psycopg(db_url: str) -> str:
    """Convert SQLAlchemy asyncpg URL to PostgreSQL URL format for psycopg."""
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(pg_url)
    query_params = parse_qs(parsed.query)
    
    if "sslmode" not in query_params:
        query_params["sslmode"] = ["disable"]
    
    new_query = urlencode(query_params, doseq=True)
    formatted_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
    return formatted_url


async def check_schema_version():
    """Check if checkpoint_writes has the task_path column."""
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Install with: pip install psycopg[binary]")
        return False
    
    pg_url = _format_pg_url_for_psycopg(settings.database_url)
    
    try:
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                # Check if task_path column exists
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
        print(f"ERROR: Failed to check schema: {e}")
        return False


async def drop_checkpoint_tables():
    """Drop all checkpoint and store tables."""
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Install with: pip install psycopg[binary]")
        return False
    
    pg_url = _format_pg_url_for_psycopg(settings.database_url)
    
    print("Dropping checkpoint and store tables...")
    
    try:
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                # Drop tables in reverse dependency order
                tables = [
                    'checkpoint_writes',
                    'checkpoint_blobs',
                    'checkpoints',
                    'checkpoint_migrations',
                    'store',
                    'store_migrations',
                ]
                
                for table in tables:
                    try:
                        await cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                        print(f"  ✓ Dropped table: {table}")
                    except Exception as e:
                        print(f"  ⚠️  Error dropping {table}: {e}")
                
                await conn.commit()
                print("✓ All tables dropped successfully")
                return True
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to drop tables: {e}")
        return False


async def check_stuck_operations():
    """Check for stuck CREATE INDEX CONCURRENTLY operations."""
    try:
        import psycopg
    except ImportError:
        return False
    
    pg_url = _format_pg_url_for_psycopg(settings.database_url)
    
    try:
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT COUNT(*)
                    FROM pg_stat_activity
                    WHERE query LIKE '%CREATE INDEX CONCURRENTLY%'
                    AND state != 'idle';
                """)
                result = await cur.fetchone()
                return (result[0] if result else 0) > 0
        finally:
            await conn.close()
    except Exception:
        return False


async def run_setup():
    """Run setup() to create/migrate tables using LangGraph."""
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.store.postgres import AsyncPostgresStore
    except ImportError:
        print("ERROR: langgraph-checkpoint-postgres not installed")
        return False
    
    pg_url = _format_pg_url_for_psycopg(settings.database_url)
    
    # Check for stuck operations first
    print("Checking for stuck database operations...")
    has_stuck_ops = await check_stuck_operations()
    if has_stuck_ops:
        print("  ⚠️  Found stuck operations!")
        print("  Please run: python backend/scripts/fix_index_locks.py --cancel-all")
        print("  Then run this script again.")
        return False
    print("  ✓ No stuck operations found")
    print()
    
    print("Running LangGraph setup() to create/migrate tables...")
    
    try:
        # Setup checkpointer
        print("Setting up AsyncPostgresSaver...")
        async with AsyncPostgresSaver.from_conn_string(pg_url) as checkpointer:
            try:
                await asyncio.wait_for(checkpointer.setup(), timeout=30.0)
                print("  ✓ Checkpoint tables setup complete")
            except asyncio.TimeoutError:
                print("  ✗ Checkpoint setup timed out")
                print("  This may be due to stuck index operations.")
                print("  Run: python backend/scripts/fix_index_locks.py --cancel-all")
                return False
        
        # Setup store
        print("Setting up AsyncPostgresStore...")
        async with AsyncPostgresStore.from_conn_string(pg_url) as store:
            try:
                await asyncio.wait_for(store.setup(), timeout=30.0)
                print("  ✓ Store tables setup complete")
            except asyncio.TimeoutError:
                print("  ✗ Store setup timed out")
                print("  This may be due to stuck index operations.")
                print("  Run: python backend/scripts/fix_index_locks.py --cancel-all")
                return False
        
        print("✓ All tables setup successfully")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to run setup(): {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="Fix checkpoint table schema issues"
    )
    parser.add_argument(
        "--drop-tables",
        action="store_true",
        help="Drop existing tables before recreating (use if schema is severely outdated)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Checkpoint Schema Fix Tool")
    print("=" * 80)
    print()
    
    # Check current schema
    print("1. Checking schema version...")
    has_task_path = await check_schema_version()
    
    if has_task_path:
        print("  ✓ Schema is up-to-date (task_path column exists)")
        print()
        print("Schema is already correct. No action needed.")
        return
    else:
        print("  ✗ Schema is outdated (task_path column missing)")
        print()
    
    # Fix schema
    if args.drop_tables:
        print("2. Dropping existing tables...")
        if not await drop_checkpoint_tables():
            print("Failed to drop tables")
            return
        print()
    
    print("3. Running setup() to create/migrate tables...")
    if await run_setup():
        print()
        print("=" * 80)
        print("✓ Schema fix complete!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Restart the backend: ./init.sh restart backend")
        print("2. Test the agent with persistent memory enabled")
    else:
        print()
        print("=" * 80)
        print("✗ Schema fix failed. Check errors above.")
        print("=" * 80)
        print()
        print("Troubleshooting:")
        print("1. Check for stuck database operations: python backend/scripts/diagnose_db_locks.py")
        print("2. Cancel stuck operations: python backend/scripts/fix_index_locks.py --cancel-all")
        print("3. Try again with --drop-tables if schema is severely outdated")


if __name__ == "__main__":
    asyncio.run(main())

