#!/usr/bin/env python3
"""
Test database connectivity for both sync and async connections.
Usage: python scripts/test_db_connection.py
"""
import asyncio
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

# Database URLs
SYNC_DB_URL = "postgresql://context:context_dev@localhost:5432/context"
ASYNC_DB_URL = "postgresql+asyncpg://context:context_dev@localhost:5432/context"


def test_sync_connection():
    """Test synchronous PostgreSQL connection."""
    print("Testing synchronous connection...")
    try:
        engine = create_engine(SYNC_DB_URL, echo=False)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✓ Sync connection successful!")
            print(f"  PostgreSQL version: {version[:50]}...")
            return True
    except Exception as e:
        print(f"✗ Sync connection failed: {e}")
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()


async def test_async_connection():
    """Test asynchronous PostgreSQL connection with asyncpg."""
    print("\nTesting asynchronous connection...")
    try:
        engine = create_async_engine(ASYNC_DB_URL, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✓ Async connection successful!")
            print(f"  PostgreSQL version: {version[:50]}...")
            return True
    except Exception as e:
        print(f"✗ Async connection failed: {e}")
        return False
    finally:
        if 'engine' in locals():
            await engine.dispose()


async def test_database_operations():
    """Test basic database operations."""
    print("\nTesting database operations...")
    try:
        engine = create_async_engine(ASYNC_DB_URL, echo=False)
        async with engine.connect() as conn:
            # Create a test table
            await conn.execute(text(
                "CREATE TABLE IF NOT EXISTS _test_table (id SERIAL PRIMARY KEY, name VARCHAR(50))"
            ))
            await conn.commit()

            # Insert data
            await conn.execute(text(
                "INSERT INTO _test_table (name) VALUES ('test') ON CONFLICT DO NOTHING"
            ))
            await conn.commit()

            # Query data
            result = await conn.execute(text("SELECT COUNT(*) FROM _test_table"))
            count = result.scalar()

            # Cleanup
            await conn.execute(text("DROP TABLE _test_table"))
            await conn.commit()

            print(f"✓ Database operations successful! (inserted/queried {count} rows)")
            return True
    except Exception as e:
        print(f"✗ Database operations failed: {e}")
        return False
    finally:
        if 'engine' in locals():
            await engine.dispose()


def main():
    """Run all database tests."""
    print("=" * 60)
    print("Database Connection Test Suite")
    print("=" * 60)

    results = []

    # Test sync connection
    results.append(test_sync_connection())

    # Test async connection
    results.append(asyncio.run(test_async_connection()))

    # Test database operations
    results.append(asyncio.run(test_database_operations()))

    print("\n" + "=" * 60)
    if all(results):
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
