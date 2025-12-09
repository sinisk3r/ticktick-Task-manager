---
description: Debug LLM integration issues in the task analysis pipeline
---

Help me debug issues with the Claude API integration in the LLM service.

When I use this command, you should:

1. **Check the LLM service implementation**:
   - Review backend/app/services/llm.py
   - Verify prompt formatting and structure
   - Check error handling and retry logic
   - Validate JSON parsing of LLM responses

2. **Examine the analysis pipeline**:
   - Check Celery task: analyze_new_task
   - Verify webhook handling in backend/app/api/sync.py
   - Look at task storage in backend/app/models/task.py
   - Check WebSocket broadcasting

3. **Common issues to investigate**:
   - Is ANTHROPIC_API_KEY set correctly?
   - Are prompts producing valid JSON?
   - Is retry logic working (tenacity)?
   - Are tasks being queued to Celery correctly?
   - Is Redis connection working?
   - Are LLM responses being cached properly?
   - Is rate limiting blocking requests?

4. **Validate the data flow**:
   - TickTick webhook → FastAPI → Celery → LLM → Database → WebSocket
   - Check each step for failures
   - Review sync_logs table for error patterns

5. **Suggest fixes**:
   - Prompt improvements
   - Error handling enhancements
   - Fallback strategies
   - Logging additions for better debugging

6. **Test the fix**:
   - Suggest how to test locally
   - Provide curl commands or pytest examples
   - Recommend monitoring to add

Focus on the end-to-end flow from task creation to frontend display.
