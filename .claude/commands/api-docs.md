---
description: Generate or update API documentation for endpoints
---

Help me document API endpoints with comprehensive details.

When I use this command for an endpoint or module, you should:

1. **Review the FastAPI route**:
   - Locate the endpoint in backend/app/api/
   - Understand its purpose and business logic
   - Identify request/response models
   - Check authentication requirements

2. **Generate OpenAPI documentation**:
   - Add detailed docstrings to route functions
   - Document request body with Pydantic models
   - Document response with response_model
   - Add example values using Field(example=...)
   - Document possible error responses

   Example:
   ```python
   @router.post(
       "/api/tasks/{task_id}/priority",
       response_model=TaskResponse,
       summary="Override task priority",
       description="Manually override the LLM-assigned priority scores",
       responses={
           200: {"description": "Task updated successfully"},
           404: {"description": "Task not found"},
           429: {"description": "Rate limit exceeded"}
       }
   )
   async def override_priority(
       task_id: str = Path(..., description="UUID of the task"),
       priority: PriorityOverride = Body(..., example={
           "urgency_score": 8,
           "importance_score": 9,
           "reasoning": "Critical for Q4 revenue"
       }),
       user: User = Depends(get_current_user)
   ):
       """
       Override the LLM-assigned priority scores for a task.

       This endpoint allows users to manually adjust urgency and importance
       scores when they disagree with the LLM's analysis. The override
       flag is set to prevent future LLM updates from changing these values.
       """
       # Implementation
   ```

3. **Document authentication flow**:
   - OAuth scopes required
   - JWT token format
   - Token refresh process
   - Rate limiting rules

4. **Create example requests**:
   - curl commands
   - Python requests examples
   - Frontend API client usage

5. **Update the FastAPI app** to enhance auto-docs:
   - Add tags to group related endpoints
   - Include version information
   - Add contact/license info
   - Configure OpenAPI metadata

6. **Generate Postman/Insomnia collection** if needed:
   - Export OpenAPI spec
   - Add environment variables
   - Include example requests

The auto-generated docs will be available at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)
