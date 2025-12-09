---
description: Debug Celery background task issues and queue problems
---

Help me debug Celery worker and task execution issues.

When I use this command, you should:

1. **Check Celery infrastructure**:
   - Verify Redis connection (REDIS_URL)
   - Check if Celery worker is running
   - Review worker logs for errors
   - Check task queue length

   ```bash
   # Check if workers are running
   celery -A app.workers.celery_app inspect active

   # Check queue length
   redis-cli llen celery

   # Monitor in real-time
   celery -A app.workers.celery_app events
   ```

2. **Analyze task definitions**:
   - Review backend/app/workers/
   - Check task signatures and decorators
   - Verify retry logic configuration
   - Check for serialization issues

3. **Common issues to investigate**:
   - Tasks stuck in queue (not being picked up)
   - Tasks failing silently
   - Tasks timing out
   - Retry logic not working
   - Task results not being stored
   - Dead letter queue buildup

4. **Review task execution flow**:
   - How tasks are queued (background_tasks.add_task vs .delay())
   - Worker concurrency settings
   - Task routing (if using multiple queues)
   - Task priority settings

5. **Check for specific problems**:
   - **analyze_new_task**: LLM API failures, parsing errors
   - **sync_ticktick_realtime**: Webhook processing issues
   - **update_workload_analytics**: Database query performance
   - **generate_weekly_reviews**: Scheduled task not running

6. **Debugging techniques**:
   - Add more logging to tasks
   - Use celery.utils.log.get_task_logger
   - Test task execution directly:
   ```python
   from app.workers.analysis import analyze_new_task
   result = analyze_new_task.apply(args=['task_id']).get()
   ```

7. **Suggest fixes**:
   - Worker count adjustments
   - Task timeout configuration
   - Better error handling
   - Task result backend configuration
   - Monitoring improvements (Flower)

8. **Set up Flower** for monitoring if not installed:
   ```bash
   pip install flower
   celery -A app.workers.celery_app flower
   # Access at http://localhost:5555
   ```

Focus on getting visibility into what's happening with background tasks.
