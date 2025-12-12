#!/bin/bash
# Wrapper script for agent testing with automatic venv activation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$BACKEND_DIR/venv"
PYTHON_SCRIPT="$SCRIPT_DIR/test_agent_core.py"

# Activate venv if it exists
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo -e "${YELLOW}⚠ Virtual environment not found at $VENV_DIR${NC}"
    echo -e "${YELLOW}  Using system Python...${NC}"
fi

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}✗ Python script not found: $PYTHON_SCRIPT${NC}"
    exit 1
fi

# Run the Python script with all arguments passed through
python "$PYTHON_SCRIPT" "$@"
