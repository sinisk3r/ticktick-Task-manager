#!/usr/bin/env python3
"""
Diagnostic script to identify stuck CREATE INDEX CONCURRENTLY operations
and list checkpoint/store related indexes in PostgreSQL.

Usage:
    python backend/scripts/diagnose_db_locks.py
"""

import asyncio
import sys
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


async def diagnose_stuck_operations():
    """Query PostgreSQL for stuck index creation operations."""
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Install with: pip install psycopg[binary]")
        return
    
    pg_url = _format_pg_url_for_psycopg(settings.database_url)
    
    print("=" * 80)
    print("PostgreSQL Lock Diagnostic Tool")
    print("=" * 80)
    print(f"Database URL: {pg_url.split('@')[0]}@***")
    print()
    
    try:
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                # Find stuck CREATE INDEX CONCURRENTLY operations
                print("1. Checking for stuck CREATE INDEX CONCURRENTLY operations...")
                await cur.execute("""
                    SELECT 
                        pid,
                        state,
                        wait_event_type,
                        wait_event,
                        query_start,
                        state_change,
                        LEFT(query, 100) as query_preview
                    FROM pg_stat_activity
                    WHERE query LIKE '%CREATE INDEX CONCURRENTLY%'
                    AND state != 'idle'
                    ORDER BY query_start;
                """)
                
                stuck_ops = await cur.fetchall()
                
                if stuck_ops:
                    print(f"   ⚠️  Found {len(stuck_ops)} stuck operation(s):")
                    print()
                    for pid, state, wait_type, wait_event, query_start, state_change, query_preview in stuck_ops:
                        print(f"   PID: {pid}")
                        print(f"   State: {state}")
                        print(f"   Wait Event: {wait_type}/{wait_event}")
                        print(f"   Started: {query_start}")
                        print(f"   Query: {query_preview}...")
                        print(f"   Cancel command: SELECT pg_cancel_backend({pid});")
                        print(f"   Terminate command: SELECT pg_terminate_backend({pid});")
                        print()
                else:
                    print("   ✓ No stuck CREATE INDEX CONCURRENTLY operations found")
                print()
                
                # List checkpoint/store related indexes
                print("2. Listing checkpoint/store related indexes...")
                await cur.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE tablename LIKE 'checkpoint%' 
                       OR tablename LIKE 'store%'
                       OR indexname LIKE 'checkpoint%'
                       OR indexname LIKE 'store%'
                    ORDER BY tablename, indexname;
                """)
                
                indexes = await cur.fetchall()
                
                if indexes:
                    print(f"   Found {len(indexes)} related index(es):")
                    print()
                    for schema, table, index, definition in indexes:
                        print(f"   Table: {schema}.{table}")
                        print(f"   Index: {index}")
                        print(f"   Definition: {definition[:100]}...")
                        print()
                else:
                    print("   ℹ️  No checkpoint/store indexes found (tables may not exist yet)")
                print()
                
                # Check for locks on checkpoint/store tables
                print("3. Checking for locks on checkpoint/store tables...")
                await cur.execute("""
                    SELECT 
                        l.locktype,
                        l.relation::regclass as relation,
                        l.mode,
                        l.granted,
                        a.pid,
                        a.state,
                        a.query_start,
                        LEFT(a.query, 100) as query_preview
                    FROM pg_locks l
                    JOIN pg_stat_activity a ON l.pid = a.pid
                    WHERE l.relation::regclass::text LIKE '%checkpoint%'
                       OR l.relation::regclass::text LIKE '%store%'
                    ORDER BY l.granted, a.query_start;
                """)
                
                locks = await cur.fetchall()
                
                if locks:
                    print(f"   ⚠️  Found {len(locks)} lock(s) on checkpoint/store tables:")
                    print()
                    for locktype, relation, mode, granted, pid, state, query_start, query_preview in locks:
                        status = "GRANTED" if granted else "WAITING"
                        print(f"   {status}: {mode} on {relation}")
                        print(f"   PID: {pid}, State: {state}")
                        print(f"   Query: {query_preview}...")
                        print()
                else:
                    print("   ✓ No locks found on checkpoint/store tables")
                print()
                
                # Check table existence
                print("4. Checking if checkpoint/store tables exist...")
                await cur.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND (table_name LIKE 'checkpoint%' OR table_name LIKE 'store%')
                    ORDER BY table_name;
                """)
                
                tables = await cur.fetchall()
                
                if tables:
                    print(f"   ✓ Found {len(tables)} table(s):")
                    for (table_name,) in tables:
                        print(f"     - {table_name}")
                else:
                    print("   ℹ️  No checkpoint/store tables found (will be created on first setup)")
                print()
                
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        print()
        print("Troubleshooting:")
        print("1. Ensure PostgreSQL is running")
        print("2. Check DATABASE_URL in backend/.env")
        print("3. Verify database credentials are correct")
        return
    
    print("=" * 80)
    print("Diagnostic complete!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. If stuck operations found, run: python backend/scripts/fix_index_locks.py")
    print("2. If no stuck operations, proceed with enabling persistent memory")


if __name__ == "__main__":
    asyncio.run(diagnose_stuck_operations())

