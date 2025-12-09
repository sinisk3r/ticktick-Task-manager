---
description: Identify and fix performance bottlenecks in the application
---

Help me optimize performance across the Context application.

When I use this command, you should:

1. **Analyze potential bottlenecks**:
   - Database queries (N+1 queries, missing indexes)
   - LLM API calls (unnecessary calls, caching opportunities)
   - Redis usage (TTL optimization, cache hit rates)
   - Frontend rendering (unnecessary re-renders, bundle size)
   - Celery task queuing (queue buildup, worker count)

2. **Database optimization**:
   - Review SQLAlchemy queries for eager loading opportunities
   - Check for missing indexes on frequently queried fields
   - Look for opportunities to use database-level aggregations
   - Suggest connection pool tuning

3. **LLM cost optimization**:
   - Review prompts for token reduction
   - Identify redundant LLM calls that could be cached
   - Check if cache TTLs are appropriate
   - Suggest batching opportunities

4. **Redis caching strategy**:
   - Review current cache keys and TTLs
   - Identify frequently accessed data that isn't cached
   - Suggest cache warming strategies
   - Check for cache stampede issues

5. **Frontend optimization**:
   - Check for unnecessary API calls
   - Review React component re-render patterns
   - Suggest SWR configuration improvements
   - Analyze bundle size and suggest code splitting

6. **Celery worker optimization**:
   - Review task queue lengths
   - Suggest worker count adjustments
   - Identify tasks that could be combined
   - Check for tasks that should be deprioritized

7. **Provide metrics to track**:
   - What to monitor (API latency, LLM calls/hour, cache hit rate)
   - How to measure improvements
   - Suggested alerting thresholds

Focus on the highest-impact optimizations first (80/20 rule).
