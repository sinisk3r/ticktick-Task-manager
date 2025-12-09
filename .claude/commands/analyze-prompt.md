---
description: Analyze and improve an LLM prompt for accuracy and effectiveness
---

You are a prompt engineering expert. Help me analyze and improve an LLM prompt from the backend/app/prompts/ directory.

When I use this command, I want you to:

1. **Read the specified prompt file** from backend/app/prompts/
2. **Analyze its effectiveness** by evaluating:
   - Clarity of instructions
   - Specificity of output format requirements
   - Handling of edge cases
   - Potential for ambiguous interpretations
   - JSON schema validation (if applicable)

3. **Suggest improvements** including:
   - More specific instructions
   - Better examples or few-shot prompting
   - Explicit handling of edge cases
   - Structured output validation
   - Cost optimization (token reduction)

4. **Test variations** if needed by:
   - Creating alternative versions
   - Explaining trade-offs between versions
   - Recommending which to A/B test

5. **Document changes** by:
   - Updating the prompt file with version number
   - Adding a changelog comment at the top
   - Explaining the reasoning behind changes

Focus on making prompts that produce consistent, parseable JSON output since the backend expects structured responses.
