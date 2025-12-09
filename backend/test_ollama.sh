#!/bin/bash
# Holistic test hitting the backend API (port 8000) instead of Ollama directly.
# Verifies health and analyze JSON response.

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }

echo "=== Health check ==="
health_resp="$(curl -s "${BASE_URL}/health")"
echo "Response: ${health_resp}"

echo ""
echo "=== Analyze endpoint ==="
analyze_payload='{"description": "Prepare slides for board meeting tomorrow"}'
analyze_resp="$(curl -s -X POST "${BASE_URL}/api/analyze" -H "Content-Type: application/json" -d "${analyze_payload}")"
echo "Response: ${analyze_resp}"

echo ""
echo "=== Validation ==="
python3 - "$health_resp" "$analyze_resp" <<'PYCODE'
import json, sys
health_raw, analyze_raw = sys.argv[1], sys.argv[2]

def fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)

def ok(msg):
    print(f"[OK] {msg}")

try:
    health = json.loads(health_raw)
    if health.get("status") != "ok":
        fail("Health status not ok")
    ok("Health endpoint returned ok")
except Exception as e:
    fail(f"Health parse failed: {e}")

try:
    analyze = json.loads(analyze_raw)
    for key in ("urgency", "importance", "quadrant", "reasoning"):
        if key not in analyze:
            fail(f"Analyze missing key: {key}")
    ok("Analyze endpoint returned required keys")
except Exception as e:
    fail(f"Analyze parse failed: {e}")
PYCODE

echo ""
green "All checks passed."
