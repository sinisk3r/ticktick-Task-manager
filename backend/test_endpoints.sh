#!/bin/bash
# Test script for Context API endpoints
# Make sure the server is running: uvicorn app.main:app --reload --port 8000
# Make sure PostgreSQL is running on port 5433

BASE_URL="http://127.0.0.1:8000"

echo "========================================="
echo "Testing Context API Endpoints"
echo "========================================="
echo ""

# Test 1: Health Check
echo "1. Testing /health endpoint..."
curl -s "${BASE_URL}/health" | python -m json.tool
echo -e "\n"

# Test 2: LLM Health
echo "2. Testing /api/llm/health endpoint..."
curl -s "${BASE_URL}/api/llm/health" | python -m json.tool
echo -e "\n"

# Test 3: LLM Models
echo "3. Testing /api/llm/models endpoint..."
curl -s "${BASE_URL}/api/llm/models" | python -m json.tool
echo -e "\n"

# Test 4: Analyze Task
echo "4. Testing POST /api/analyze endpoint..."
curl -s -X POST "${BASE_URL}/api/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"description\": \"Finish quarterly report by Friday EOD\"}" | python -m json.tool
echo -e "\n"

# Test 5: Get Settings (requires database)
echo "5. Testing GET /api/settings endpoint (requires PostgreSQL)..."
curl -s "${BASE_URL}/api/settings?user_id=1" | python -m json.tool
echo -e "\n"

# Test 6: Update Settings (requires database)
echo "6. Testing PUT /api/settings endpoint (requires PostgreSQL)..."
curl -s -X PUT "${BASE_URL}/api/settings?user_id=1" \
  -H "Content-Type: application/json" \
  -d "{\"llm_provider\": \"ollama\", \"ollama_model\": \"qwen3:8b\"}" | python -m json.tool
echo -e "\n"

# Test 7: Create Task (requires database)
echo "7. Testing POST /api/tasks endpoint (requires PostgreSQL)..."
curl -s -X POST "${BASE_URL}/api/tasks" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Finish quarterly report\", \"description\": \"Complete Q4 financial report and submit to management\", \"user_id\": 1}" | python -m json.tool
echo -e "\n"

# Test 8: List Tasks (requires database)
echo "8. Testing GET /api/tasks endpoint (requires PostgreSQL)..."
curl -s "${BASE_URL}/api/tasks?user_id=1" | python -m json.tool
echo -e "\n"

# Test 9: Get Single Task (requires database and task_id)
echo "9. Testing GET /api/tasks/{id} endpoint (requires PostgreSQL)..."
echo "   (Replace 1 with actual task ID)"
curl -s "${BASE_URL}/api/tasks/1" | python -m json.tool
echo -e "\n"

# Test 10: Update Task (requires database and task_id)
echo "10. Testing PUT /api/tasks/{id} endpoint (requires PostgreSQL)..."
echo "    (Replace 1 with actual task ID)"
curl -s -X PUT "${BASE_URL}/api/tasks/1" \
  -H "Content-Type: application/json" \
  -d "{\"status\": \"completed\"}" | python -m json.tool
echo -e "\n"

# Test 11: Delete Task (requires database and task_id)
echo "11. Testing DELETE /api/tasks/{id} endpoint (requires PostgreSQL)..."
echo "    (Replace 1 with actual task ID)"
curl -s -X DELETE "${BASE_URL}/api/tasks/1?soft_delete=true" -v
echo -e "\n"

echo "========================================="
echo "Testing Complete"
echo "========================================="
echo ""
echo "Note: Tests 5-11 require PostgreSQL to be running on port 5433"
echo "To start PostgreSQL: docker compose up -d postgres"
echo ""
echo "View API documentation: ${BASE_URL}/docs"
echo "View API schema: ${BASE_URL}/openapi.json"
