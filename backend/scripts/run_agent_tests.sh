#!/bin/bash
# Automated test suite for Context agent system
# Runs all test cases and generates a comprehensive report

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RESULTS_DIR="$BACKEND_DIR/test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="$RESULTS_DIR/agent_tests_$TIMESTAMP.json"
REPORT_FILE="$RESULTS_DIR/agent_report_$TIMESTAMP.txt"

# Load runtime config if available
RUNTIME_ENV="$(cd "$SCRIPT_DIR/../.." && pwd)/.env.runtime"
if [ -f "$RUNTIME_ENV" ]; then
    source "$RUNTIME_ENV"
fi

# Backend and Ollama URLs
BACKEND_URL="${BACKEND_URL:-http://localhost:5405}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"

# Python environment
if [ -d "$BACKEND_DIR/venv" ]; then
    source "$BACKEND_DIR/venv/bin/activate"
fi

# Create results directory
mkdir -p "$RESULTS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Context Agent Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if backend is running
echo -e "${YELLOW}Checking backend status...${NC}"
if ! curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}✗ Backend not reachable at $BACKEND_URL${NC}"
    echo -e "${YELLOW}  Please start the backend first:${NC}"
    echo -e "  cd backend && uvicorn app.main:app --reload --port 5405"
    exit 1
fi
echo -e "${GREEN}✓ Backend is running${NC}"

# Check if Ollama is running
echo -e "${YELLOW}Checking Ollama status...${NC}"
if ! curl -s "$OLLAMA_URL/api/version" > /dev/null 2>&1; then
    echo -e "${RED}✗ Ollama not reachable at $OLLAMA_URL${NC}"
    echo -e "${YELLOW}  Please start Ollama first${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Ollama is running${NC}"

# Check model availability
echo -e "${YELLOW}Checking qwen3:4b model...${NC}"
if ! curl -s "$OLLAMA_URL/api/tags" | grep -q "qwen3:4b"; then
    echo -e "${YELLOW}⚠ qwen3:4b not found, trying to pull...${NC}"
    ollama pull qwen3:4b
fi
echo -e "${GREEN}✓ Model ready${NC}"
echo ""

# Run tests
echo -e "${BLUE}Running agent tests...${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$BACKEND_DIR"

# Run batch tests (using shell wrapper that handles venv)
"$SCRIPT_DIR/test_agent.sh" \
    --batch \
    --save "$RESULTS_FILE" \
    --url "$BACKEND_URL" \
    --verbose

TEST_EXIT_CODE=$?

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Generating Report${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Parse results and generate report
python - <<EOF
import json
import sys
from pathlib import Path
from datetime import datetime

results_file = Path("$RESULTS_FILE")

if not results_file.exists():
    print("${RED}✗ Results file not found${NC}")
    sys.exit(1)

with open(results_file) as f:
    data = json.load(f)

# Generate report
report_lines = []
report_lines.append("="*80)
report_lines.append("CONTEXT AGENT TEST REPORT")
report_lines.append("="*80)
report_lines.append(f"Timestamp: {data['timestamp']}")
report_lines.append(f"Total Tests: {data['total_tests']}")
report_lines.append(f"Passed: {data['passed']}")
report_lines.append(f"Failed: {data['failed']}")
report_lines.append(f"Pass Rate: {data['passed']/data['total_tests']*100:.1f}%")
report_lines.append("")

# Category breakdown
tool_tests = [r for r in data['results'] if 'Tool Call' in r.get('test_name', '')]
conv_tests = [r for r in data['results'] if 'Conversational' in r.get('test_name', '')]
edge_tests = [r for r in data['results'] if 'Edge Case' in r.get('test_name', '')]

report_lines.append("Category Breakdown:")
report_lines.append(f"  Tool Calling: {sum(1 for t in tool_tests if t.get('passed', t['success']))}/{len(tool_tests)} passed")
report_lines.append(f"  Conversational: {sum(1 for t in conv_tests if t.get('passed', t['success']))}/{len(conv_tests)} passed")
report_lines.append(f"  Edge Cases: {sum(1 for t in edge_tests if t.get('passed', t['success']))}/{len(edge_tests)} passed")
report_lines.append("")

# Failed tests
failed = [r for r in data['results'] if not r.get('passed', r['success'])]
if failed:
    report_lines.append("Failed Tests:")
    for r in failed:
        report_lines.append(f"  ✗ {r['test_name']}")
        report_lines.append(f"    Query: {r['query']}")
        if r['errors']:
            report_lines.append(f"    Errors: {r['errors'][0]}")
        report_lines.append("")

# Performance metrics
avg_duration = sum(r['duration_seconds'] for r in data['results']) / len(data['results'])
report_lines.append(f"Performance:")
report_lines.append(f"  Average duration: {avg_duration:.2f}s")
report_lines.append(f"  Min: {min(r['duration_seconds'] for r in data['results']):.2f}s")
report_lines.append(f"  Max: {max(r['duration_seconds'] for r in data['results']):.2f}s")
report_lines.append("")

# Tool call accuracy
tool_call_tests = [r for r in data['results']
                   if r.get('expected', {}).get('should_call_tools') is True]
if tool_call_tests:
    correct_tool_calls = sum(1 for r in tool_call_tests if len(r['tool_calls']) > 0)
    report_lines.append(f"Tool Call Accuracy:")
    report_lines.append(f"  {correct_tool_calls}/{len(tool_call_tests)} tests correctly called tools")
    report_lines.append(f"  Accuracy: {correct_tool_calls/len(tool_call_tests)*100:.1f}%")
    report_lines.append("")

# Conversational accuracy
conv_only_tests = [r for r in data['results']
                   if r.get('expected', {}).get('should_call_tools') is False]
if conv_only_tests:
    correct_conv = sum(1 for r in conv_only_tests if len(r['tool_calls']) == 0)
    report_lines.append(f"Conversational Accuracy:")
    report_lines.append(f"  {correct_conv}/{len(conv_only_tests)} tests correctly avoided tools")
    report_lines.append(f"  Accuracy: {correct_conv/len(conv_only_tests)*100:.1f}%")
    report_lines.append("")

# Response quality
truncated = sum(1 for r in data['results']
                if r['message'] and not r['message'].rstrip()[-1:] in '.!?')
report_lines.append(f"Response Quality:")
report_lines.append(f"  Truncated responses: {truncated}/{data['total_tests']}")

thinking_leaks = sum(1 for r in data['results']
                     if any(kw in r['message'] for kw in ['I should', 'I will', 'Let me', 'First I']))
report_lines.append(f"  Thinking leaks: {thinking_leaks}/{data['total_tests']}")
report_lines.append("")

report_lines.append("="*80)
report_lines.append(f"Results saved to: $RESULTS_FILE")
report_lines.append(f"Report saved to: $REPORT_FILE")
report_lines.append("="*80)

# Write report
report_text = '\n'.join(report_lines)
with open("$REPORT_FILE", 'w') as f:
    f.write(report_text)

# Print to console
print(report_text)

# Exit with pass/fail
sys.exit(0 if data['failed'] == 0 else 1)
EOF

REPORT_EXIT_CODE=$?

# Final summary
echo ""
if [ $REPORT_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${YELLOW}⚠ Some tests failed. See report for details.${NC}"
fi

echo ""
echo -e "${BLUE}Files created:${NC}"
echo -e "  Results: ${GREEN}$RESULTS_FILE${NC}"
echo -e "  Report:  ${GREEN}$REPORT_FILE${NC}"
echo ""

# Offer to view report
if [ -t 0 ]; then  # Check if running interactively
    read -p "View full report? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat "$REPORT_FILE"
    fi
fi

exit $REPORT_EXIT_CODE
