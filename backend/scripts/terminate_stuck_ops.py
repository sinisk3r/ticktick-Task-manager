#!/usr/bin/env python3
"""
Quick script to terminate stuck PostgreSQL operations.

Usage:
    python backend/scripts/terminate_stuck_ops.py
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


async def terminate_stuck_operations():
    """Terminate all stuck CREATE INDEX CONCURRENTLY operations."""
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg not installed. Install with: pip install psycopg[binary]")
        return False
    
    pg_url = _format_pg_url_for_psycopg(settings.database_url)
    
    print("Terminating stuck PostgreSQL operations...")
    print()
    
    try:
        conn = await psycopg.AsyncConnection.connect(pg_url)
        try:
            async with conn.cursor() as cur:
                # Find stuck operations
                await cur.execute("""
                    SELECT pid, state, wait_event_type, wait_event, query_start, LEFT(query, 100)
                    FROM pg_stat_activity
                    WHERE (query LIKE '%CREATE INDEX CONCURRENTLY%' OR query LIKE '%CREATE INDEX%')
                    AND state != 'idle'
                    AND pid != pg_backend_pid()
                    ORDER BY query_start;
                """)
                
                stuck_ops = await cur.fetchall()
                
                if not stuck_ops:
                    print("✓ No stuck operations found")
                    return True
                
                print(f"Found {len(stuck_ops)} stuck operation(s):")
                print()
                
                terminated_count = 0
                for pid, state, wait_type, wait_event, query_start, query_preview in stuck_ops:
                    print(f"  PID {pid}: {state}")
                    print(f"    Query: {query_preview}...")
                    
                    try:
                        # Try terminate (forceful)
                        await cur.execute(f"SELECT pg_terminate_backend({pid})")
                        result = await cur.fetchone()
                        if result and result[0]:
                            print(f"    ✓ Terminated")
                            terminated_count += 1
                        else:
                            print(f"    ✗ Failed to terminate")
                    except Exception as e:
                        error_str = str(e).lower()
                        if "terminating connection" in error_str or "connection" in error_str:
                            print(f"    ✓ Terminated (connection closed)")
                            terminated_count += 1
                        else:
                            print(f"    ✗ Error: {e}")
                    print()
                
                await conn.commit()
                
                if terminated_count == len(stuck_ops):
                    print(f"✓ Successfully terminated {terminated_count} operation(s)")
                    return True
                else:
                    print(f"⚠️  Terminated {terminated_count}/{len(stuck_ops)} operation(s)")
                    return False
                    
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        print()
        print("Troubleshooting:")
        print("1. Ensure PostgreSQL is running: docker ps | grep context_postgres")
        print("2. Check DATABASE_URL in backend/.env")
        return False


if __name__ == "__main__":
    success = asyncio.run(terminate_stuck_operations())
    sys.exit(0 if success else 1)

