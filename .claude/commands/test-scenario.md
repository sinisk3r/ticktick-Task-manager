---
description: Create comprehensive tests for a specific scenario or feature
---

Help me create thorough tests for a feature or user scenario.

When I use this command with a feature/scenario, you should:

1. **Identify test types needed**:
   - Unit tests (backend services, utility functions)
   - Integration tests (API endpoints with database)
   - E2E tests (full user flows)
   - LLM mocking strategies

2. **For backend tests** (pytest):
   - Create fixtures for common test data
   - Mock external API calls (TickTick, Claude, Gmail, Azure)
   - Test happy path and error cases
   - Test retry logic and timeouts
   - Test database transactions and rollbacks
   - Verify Celery task queuing

   Example structure:
   ```python
   # tests/test_feature.py

   @pytest.fixture
   async def mock_llm_response():
       return {...}

   @pytest.mark.asyncio
   async def test_task_analysis_success(mock_llm_response):
       # Test implementation
       pass

   @pytest.mark.asyncio
   async def test_task_analysis_llm_failure():
       # Test failure handling
       pass
   ```

3. **For frontend tests** (Jest/React Testing Library):
   - Test component rendering
   - Test user interactions
   - Mock API responses (SWR)
   - Test WebSocket updates
   - Test error states and loading states

4. **For E2E tests**:
   - Map out complete user journey
   - Test critical paths (login → create task → see in matrix)
   - Test real-time updates
   - Test error recovery

5. **Mock external services**:
   - Claude API: Return realistic analysis JSON
   - TickTick API: Simulate webhook payloads
   - Gmail API: Mock draft creation
   - WebSocket: Test real-time updates

6. **Edge cases to cover**:
   - Empty/null data
   - Extremely long inputs
   - Special characters
   - Concurrent requests
   - Rate limiting
   - Network failures

7. **Create the test files** in:
   - `backend/tests/` for pytest
   - `frontend/__tests__/` for Jest

Run tests with:
```bash
# Backend
pytest tests/test_feature.py -v

# Frontend
npm test -- feature.test.tsx
```
