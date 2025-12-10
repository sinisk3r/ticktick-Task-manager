#!/bin/bash
# Test database connectivity
# Usage: ./scripts/test-db.sh

set -e

# Activate virtual environment
source venv/bin/activate

# Run the test script
python scripts/test_db_connection.py
