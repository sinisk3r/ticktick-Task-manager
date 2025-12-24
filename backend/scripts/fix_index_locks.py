#!/usr/bin/env python3
"""
Cleanup script to cancel stuck CREATE INDEX CONCURRENTLY operations
and verify database readiness for LangGraph setup.

Usage:
    python backend/scripts/fix_index_locks.py [--cancel-all] [--drop-indexes]
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


async def cancel_stuck_operations(cancel_all: bool = False):
    """Cancel stuck CREATE INDEX CONCURRENTLY operations."""
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Install with: pip install psycopg[binary]")
        return False
    
    pg_url = _format_pg_url_for_psycopg(settings.database_url)
    
    print("=" * 80)
    print("PostgreSQL Lock Cleanup Tool")
    print("=" * 80)
    print()
    
    try:
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                # Find stuck operations
                await cur.execute("""
                    SELECT pid, state, wait_event_type, wait_event, query_start, LEFT(query, 100)
                    FROM pg_stat_activity
                    WHERE query LIKE '%CREATE INDEX CONCURRENTLY%'
                    AND state != 'idle'
                    ORDER BY query_start;
                """)
                
                stuck_ops = await cur.fetchall()
                
                if not stuck_ops:
                    print("✓ No stuck CREATE INDEX CONCURRENTLY operations found")
                    return True
                
                print(f"Found {len(stuck_ops)} stuck operation(s):")
                print()
                
                cancelled_count = 0
                for pid, state, wait_type, wait_event, query_start, query_preview in stuck_ops:
                    print(f"  PID {pid}: {state} (waiting on {wait_event})")
                    print(f"    Query: {query_preview}...")
                    
                    if cancel_all:
                        try:
                            # Try cancel first (graceful)
                            await cur.execute(f"SELECT pg_cancel_backend({pid})")
                            result = await cur.fetchone()
                            if result and result[0]:
                                print(f"    ✓ Cancelled (graceful)")
                                cancelled_count += 1
                            else:
                                # If cancel failed, try terminate (forceful)
                                print(f"    Cancel failed, trying terminate...")
                                await cur.execute(f"SELECT pg_terminate_backend({pid})")
                                result = await cur.fetchone()
                                if result and result[0]:
                                    print(f"    ✓ Terminated (forceful)")
                                    cancelled_count += 1
                                else:
                                    print(f"    ✗ Failed to cancel/terminate")
                        except Exception as e:
                            error_str = str(e).lower()
                            if "canceling statement" in error_str:
                                # This means the cancel worked but we got interrupted
                                print(f"    ✓ Cancelled (operation was interrupted)")
                                cancelled_count += 1
                            elif "terminating connection" in error_str:
                                # This means terminate worked
                                print(f"    ✓ Terminated (connection closed)")
                                cancelled_count += 1
                            else:
                                print(f"    ✗ Error: {e}")
                                # Try terminate as fallback
                                try:
                                    await cur.execute(f"SELECT pg_terminate_backend({pid})")
                                    term_result = await cur.fetchone()
                                    if term_result and term_result[0]:
                                        print(f"    ✓ Terminated (fallback)")
                                        cancelled_count += 1
                                except Exception as term_e:
                                    print(f"    ✗ Terminate also failed: {term_e}")
                    else:
                        print(f"    (Use --cancel-all to cancel this operation)")
                    print()
                
                if cancel_all:
                    await conn.commit()
                    print(f"✓ Cancelled {cancelled_count} operation(s)")
                    return cancelled_count == len(stuck_ops)
                else:
                    print("⚠️  Run with --cancel-all to actually cancel operations")
                    return False
                    
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return False


async def drop_problematic_indexes(drop_indexes: bool = False):
    """Optionally drop problematic indexes if they're causing issues."""
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
                # Find checkpoint/store indexes
                await cur.execute("""
                    SELECT indexname, tablename
                    FROM pg_indexes
                    WHERE tablename LIKE 'checkpoint%' 
                       OR tablename LIKE 'store%'
                       OR indexname LIKE 'checkpoint%'
                       OR indexname LIKE 'store%'
                    ORDER BY tablename, indexname;
                """)
                
                indexes = await cur.fetchall()
                
                if not indexes:
                    print("✓ No checkpoint/store indexes found")
                    return True
                
                print(f"Found {len(indexes)} checkpoint/store index(es):")
                print()
                
                if drop_indexes:
                    dropped_count = 0
                    for indexname, tablename in indexes:
                        try:
                            # Drop index concurrently if possible
                            await cur.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {indexname}")
                            print(f"  ✓ Dropped index: {indexname} on {tablename}")
                            dropped_count += 1
                        except Exception as e:
                            # If CONCURRENTLY fails, try without it
                            try:
                                await cur.execute(f"DROP INDEX IF EXISTS {indexname}")
                                print(f"  ✓ Dropped index (non-concurrent): {indexname} on {tablename}")
                                dropped_count += 1
                            except Exception as e2:
                                print(f"  ✗ Failed to drop {indexname}: {e2}")
                    
                    await conn.commit()
                    print()
                    print(f"✓ Dropped {dropped_count} index(es)")
                    return True
                else:
                    for indexname, tablename in indexes:
                        print(f"  - {indexname} on {tablename}")
                    print()
                    print("⚠️  Run with --drop-indexes to actually drop indexes")
                    return False
                    
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return False


async def verify_database_readiness():
    """Verify database is ready for LangGraph setup."""
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Install with: pip install psycopg[binary]")
        return False
    
    pg_url = _format_pg_url_for_psycopg(settings.database_url)
    
    print("Verifying database readiness...")
    print()
    
    try:
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                # Check for stuck operations
                await cur.execute("""
                    SELECT COUNT(*)
                    FROM pg_stat_activity
                    WHERE query LIKE '%CREATE INDEX CONCURRENTLY%'
                    AND state != 'idle';
                """)
                stuck_count = (await cur.fetchone())[0]
                
                if stuck_count > 0:
                    print(f"✗ Found {stuck_count} stuck operation(s) - database not ready")
                    return False
                
                # Check table existence
                await cur.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('checkpoints', 'checkpoint_writes', 'checkpoint_blobs', 'checkpoint_migrations', 'store', 'store_migrations');
                """)
                table_count = (await cur.fetchone())[0]
                
                if table_count == 0:
                    print("✓ No tables exist yet (will be created on first setup)")
                elif table_count == 6:
                    print("✓ All required tables exist")
                else:
                    print(f"⚠️  Partial table set exists ({table_count}/6 tables)")
                
                print()
                print("✓ Database is ready for LangGraph setup")
                return True
                
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"✗ ERROR: Failed to verify database: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="Clean up stuck PostgreSQL index operations"
    )
    parser.add_argument(
        "--cancel-all",
        action="store_true",
        help="Cancel all stuck CREATE INDEX CONCURRENTLY operations"
    )
    parser.add_argument(
        "--drop-indexes",
        action="store_true",
        help="Drop all checkpoint/store indexes (use with caution)"
    )
    
    args = parser.parse_args()
    
    success = True
    
    # Step 1: Cancel stuck operations
    if args.cancel_all:
        success = await cancel_stuck_operations(cancel_all=True)
        if not success:
            print("⚠️  Some operations could not be cancelled")
    else:
        await cancel_stuck_operations(cancel_all=False)
    
    print()
    
    # Step 2: Optionally drop indexes
    if args.drop_indexes:
        success = await drop_problematic_indexes(drop_indexes=True)
    else:
        await drop_problematic_indexes(drop_indexes=False)
    
    print()
    
    # Step 3: Verify readiness
    success = await verify_database_readiness() and success
    
    print()
    print("=" * 80)
    if success:
        print("✓ Cleanup complete! Database is ready for LangGraph setup.")
    else:
        print("⚠️  Cleanup completed with warnings. Review output above.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

