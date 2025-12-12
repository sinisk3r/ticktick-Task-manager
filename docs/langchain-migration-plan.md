# LangChain/LangGraph Migration Plan

## Executive Summary

**Decision:** Migrate custom agent implementation to LangChain + LangGraph framework.

**Reason:** Current custom implementation has reached complexity where maintaining it costs more than adopting a battle-tested framework.

**Timeline:** 2-3 days for full migration

**Risk:** Low - LangChain is mature, widely used, and well-documented

---

## Why Migrate Now?

### 1. We're Reinventing Framework Features

**Current custom code (~1,500 lines):**
- ✅ Custom conversation history tracking (we're about to build this)
- ✅ Manual tool registry and validation
- ✅ Custom SSE streaming implementation
- ✅ Hand-coded retry logic with tenacity
- ✅ Custom state management
- ✅ Manual message formatting for LLM

**LangChain already provides:**
- ✅ `ConversationBufferWindowMemory` - Built-in conversation history
- ✅ `@tool` decorator - Automatic tool schema generation from Python functions
- ✅ Streaming callbacks - Built-in SSE/WebSocket streaming
- ✅ Built-in retry logic - Exponential backoff, fallbacks
- ✅ LangGraph state - Persistent conversation state with checkpoints
- ✅ Message templates - Structured prompt management

### 2. Current Blockers

**Issues we discovered:**
1. ❌ **No conversation history** - Agent can't reference previous messages
   - User: "Create a task to talk to Sanath"
   - User: "Add today's date to that task"
   - Agent: "Found 2 tasks" (doesn't know which "that task" refers to)

2. ❌ **Missing update_task tool** - Can't modify existing tasks
   - We started adding it manually (150+ lines of code)
   - LangChain: `@tool` decorator = 10 lines

3. ❌ **Thinking not visible** - UI auto-collapses reasoning
   - Need custom state management to track visibility
   - LangChain: Built-in streaming callbacks handle this

4. ❌ **UI always shows "AGENT ACTIONS"** - Conditional rendering issues
   - Frontend complexity managing agent state
   - LangChain: Cleaner event model

5. ❌ **Model struggles with complex JSON prompts** - qwen3:4b/8b issues
   - Custom prompt engineering to work around limitations
   - LangChain: Better prompt templates, easier to switch models

### 3. Technical Debt is Growing

**Evidence from codebase:**

`backend/app/agent/planner.py` (477 lines):
- Manual message formatting
- Custom JSON parsing with try/except fallbacks
- Heuristic fallback when LLM fails
- Manual conversation context building (we're about to add this)

`backend/app/agent/tools.py` (current: 461 lines, growing):
- Manual Pydantic validation for each tool
- Custom validators for cleaning inputs
- Hand-coded tool registry dict
- Adding update_task would be +80 lines

`backend/app/agent/dispatcher.py`:
- Custom pre-execution hooks
- Manual tool invocation
- Custom error handling

`docs/agentic-assistant-plan.md` line 133-136:
```
Known Issues & Limitations:
1. Small model (qwen3:4b) struggles with complex JSON generation
2. Tool calling still inconsistent - may require more prompt tuning
3. No conversation state management (each request is stateless)
4. No top work items context passed to agent
```

**All 4 issues above are solved by LangChain out of the box.**

---

## Migration Benefits

### 1. **Faster Development**
- Stop building infrastructure, focus on business logic
- `@tool` decorator vs 80 lines per tool
- Built-in memory vs building state management

### 2. **Better Reliability**
- Battle-tested framework used by millions
- Edge cases already handled
- Community support and bug fixes

### 3. **Easier Model Switching**
- Plugin architecture for LLM providers
- Switch Ollama → OpenRouter → Claude → GPT with config change
- No code changes needed

### 4. **Observability**
- LangSmith integration for debugging
- Trace every LLM call, tool execution
- See exactly what the agent is thinking

### 5. **Future-Proof**
- LangGraph for complex workflows
- Multi-agent systems
- Human-in-the-loop confirmations
- Streaming with real-time updates

---

## Architecture Design

### Plugin-Based LLM Provider System

**Goal:** Switch between Ollama, OpenRouter, Claude, OpenAI with just config changes.

**Implementation:**

```python
# backend/app/core/llm_config.py

from typing import Literal
from pydantic_settings import BaseSettings

class LLMSettings(BaseSettings):
    provider: Literal["ollama", "openrouter", "anthropic", "openai"]
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 1000

    class Config:
        env_file = ".env"
        env_prefix = "LLM_"

# Usage in .env:
# LLM_PROVIDER=ollama
# LLM_MODEL=qwen3:8b
# LLM_BASE_URL=http://localhost:11434

# Or switch to OpenRouter:
# LLM_PROVIDER=openrouter
# LLM_MODEL=meta-llama/llama-3.2-3b-instruct
# LLM_API_KEY=your_key
```

**Provider Factory:**

```python
# backend/app/agent/llm_factory.py

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

def get_llm_provider(settings: LLMSettings):
    """Factory to create LLM provider based on config."""

    if settings.provider == "ollama":
        return ChatOllama(
            model=settings.model,
            base_url=settings.base_url or "http://localhost:11434",
            temperature=settings.temperature,
            num_predict=settings.max_tokens,
        )

    elif settings.provider == "openrouter":
        return ChatOpenAI(
            model=settings.model,
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    elif settings.provider == "anthropic":
        return ChatAnthropic(
            model=settings.model,
            api_key=settings.api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    elif settings.provider == "openai":
        return ChatOpenAI(
            model=settings.model,
            api_key=settings.api_key,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {settings.provider}")
```

**Benefits:**
- ✅ Single config change to switch models
- ✅ Easy to test different providers
- ✅ No code changes in agent logic
- ✅ Can use cheaper models for testing, expensive for production

---

## Migration Plan

### Phase 1: Setup LangChain (Day 1 Morning)

**Install dependencies:**
```bash
pip install langchain==0.1.0 \
    langchain-community==0.0.13 \
    langchain-ollama==0.1.0 \
    langgraph==0.0.20 \
    langsmith==0.0.77
```

**Create provider factory:**
- `backend/app/agent/llm_factory.py` - LLM provider abstraction
- `backend/app/core/llm_config.py` - Settings management

**Keep existing:**
- ✅ API contracts (`/api/agent/stream`)
- ✅ Frontend unchanged
- ✅ Database models unchanged
- ✅ Test infrastructure

### Phase 2: Convert Tools (Day 1 Afternoon)

**Replace manual tool definitions with `@tool` decorator:**

**Before (80 lines):**
```python
class CreateTaskInput(BaseModel):
    user_id: int = Field(...)
    title: str = Field(...)
    # ... 20 more lines of validation

    @validator("title")
    def clean_title(cls, v):
        # 15 lines of cleaning logic
        pass

async def create_task(payload: CreateTaskInput, db: AsyncSession):
    # 30 lines of implementation
    pass

TOOL_REGISTRY = {
    "create_task": {
        "model": CreateTaskInput,
        "callable": create_task,
        "description": "...",
        # ... more metadata
    }
}
```

**After (10 lines):**
```python
from langchain.tools import tool

@tool
async def create_task(
    user_id: int,
    title: str,
    description: str = None,
    due_date: str = None,
    priority: int = 0,
    tags: list[str] = None
) -> dict:
    """Create a new task for the user.

    Args:
        user_id: User ID
        title: Task title (max 120 chars, no quotes)
        description: Optional details that differ from title
        due_date: ISO 8601 datetime string
        priority: 0 (none), 1 (low), 3 (medium), 5 (high)
        tags: List of tag strings
    """
    # Same implementation as before
    # LangChain generates schema from signature + docstring
```

**Convert all tools:**
- `fetch_tasks` → `@tool`
- `fetch_task` → `@tool`
- `create_task` → `@tool`
- `update_task` → `@tool` (new, trivial to add)
- `complete_task` → `@tool`
- `delete_task` → `@tool`

**Delete:**
- All Pydantic Input classes (150+ lines)
- `TOOL_REGISTRY` dict (80+ lines)
- `dispatcher.py` (entire file, 100+ lines)

### Phase 3: Replace Planner with LangGraph Agent (Day 2)

**Replace custom planner with LangGraph agent:**

```python
# backend/app/agent/graph.py

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage

async def create_agent(llm, tools, user_id: int):
    """Create LangGraph agent with conversation memory."""

    system_message = """You are Context, an agentic task copilot.

    When user mentions creating/updating/completing tasks, call the appropriate tool.
    For general questions, respond conversationally.

    Keep responses concise (1-3 sentences) unless more detail is needed.
    """

    # LangGraph creates agent with built-in conversation memory
    return create_react_agent(
        llm,
        tools,
        state_modifier=system_message,
        checkpointer=MemorySaver(),  # Built-in conversation state
    )
```

**Update API endpoint:**

```python
# backend/app/api/agent.py

@router.post("/stream")
async def stream_agent(payload: StreamRequest, db: AsyncSession):
    """Stream agent events with conversation history."""

    # Get LLM provider
    llm_settings = LLMSettings()
    llm = get_llm_provider(llm_settings)

    # Get tools (auto-discovered from @tool decorators)
    tools = [fetch_tasks, create_task, update_task, complete_task, delete_task]

    # Create agent with conversation memory
    agent = await create_agent(llm, tools, payload.user_id)

    # Build conversation history
    messages = [
        HumanMessage(content=msg["content"])
        for msg in payload.messages  # Frontend sends history
    ]
    messages.append(HumanMessage(content=payload.goal))

    # Stream events
    async def event_generator():
        config = {"configurable": {"thread_id": f"user_{payload.user_id}"}}

        async for event in agent.astream_events(
            {"messages": messages},
            config=config,
            version="v1"
        ):
            # Transform LangGraph events to our SSE format
            yield format_sse_event(event)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Delete:**
- `planner.py` (entire file, 477 lines)
- Custom retry logic (using tenacity)
- Heuristic fallback
- Manual conversation state building

### Phase 4: Update Frontend (Day 2 Afternoon)

**Add conversation history to requests:**

```typescript
// frontend/lib/useAgentStream.ts

const streamAgent = async (input: string, messages: Message[]) => {
  const response = await fetch('/api/agent/stream', {
    method: 'POST',
    body: JSON.stringify({
      goal: input,
      messages: messages.map(m => ({
        role: m.role,
        content: m.content
      })),
      user_id: 1
    })
  });
  // ... rest unchanged
};
```

**Minor changes, frontend mostly unchanged.**

### Phase 5: Test & Validate (Day 3)

**Run existing test suite:**
```bash
./backend/scripts/run_agent_tests.sh
```

**Validate:**
- ✅ Tool calling works with conversation history
- ✅ All 20 test cases pass
- ✅ Thinking visible in UI
- ✅ No regressions

**Test provider switching:**
```bash
# Test with Ollama
LLM_PROVIDER=ollama LLM_MODEL=qwen3:8b ./backend/scripts/test_agent.sh -q "Create task"

# Test with OpenRouter
LLM_PROVIDER=openrouter LLM_MODEL=meta-llama/llama-3.2-3b-instruct ./backend/scripts/test_agent.sh -q "Create task"
```

---

## Code Reduction Estimate

| Component | Before (Custom) | After (LangChain) | Reduction |
|-----------|----------------|-------------------|-----------|
| **Planner** | 477 lines | ~50 lines | **-89%** |
| **Tools** | 461 lines | ~150 lines | **-67%** |
| **Dispatcher** | 100 lines | 0 lines | **-100%** |
| **Hooks** | 80 lines | 0 lines | **-100%** |
| **Total** | **~1,118 lines** | **~200 lines** | **-82%** |

**Plus we get:**
- ✅ Conversation history (free)
- ✅ Better streaming (free)
- ✅ Retry logic (free)
- ✅ Observability (free)
- ✅ Model switching (free)

---

## Risk Mitigation

### Risk 1: Learning Curve
**Mitigation:** LangChain has excellent docs, huge community, many examples

### Risk 2: Breaking Changes
**Mitigation:** Keep API contracts unchanged, frontend unaffected

### Risk 3: Performance
**Mitigation:** LangChain adds minimal overhead (~50ms), worth the benefits

### Risk 4: Vendor Lock-in
**Mitigation:** LangChain is open source, provider-agnostic by design

---

## Success Criteria

**Minimum:**
- ✅ All 20 existing test cases pass
- ✅ Conversation history works ("Update that task" references previous)
- ✅ Can switch between Ollama, OpenRouter, OpenAI with config change
- ✅ No regressions in tool calling accuracy

**Ideal:**
- ✅ 80%+ code reduction
- ✅ Tool call accuracy improves (better prompts from LangChain)
- ✅ Easier to add new tools (5 minutes vs 1 hour)
- ✅ LangSmith tracing enabled for debugging

---

## Migration Checklist

### Pre-Migration
- [ ] Document current behavior (screenshots, test results)
- [ ] Ensure all tests pass with current implementation
- [ ] Back up code (git branch: `pre-langchain-migration`)

### During Migration
- [ ] Install LangChain dependencies
- [ ] Create LLM provider factory
- [ ] Convert tools to `@tool` decorators
- [ ] Replace planner with LangGraph agent
- [ ] Update API endpoint for conversation history
- [ ] Update frontend to send message history
- [ ] Test each step incrementally

### Post-Migration
- [ ] Run full test suite
- [ ] Test provider switching (Ollama → OpenRouter)
- [ ] Update documentation
- [ ] Deploy to staging
- [ ] Monitor for issues
- [ ] Document lessons learned

---

## Files to Create/Modify

### New Files:
- `backend/app/agent/llm_factory.py` - Provider factory
- `backend/app/agent/graph.py` - LangGraph agent definition
- `backend/app/core/llm_config.py` - LLM settings

### Modified Files:
- `backend/app/agent/tools.py` - Convert to `@tool` decorators
- `backend/app/api/agent.py` - Use LangGraph agent
- `backend/requirements.txt` - Add LangChain dependencies
- `frontend/lib/useAgentStream.ts` - Send conversation history

### Deleted Files:
- `backend/app/agent/planner.py` ❌ (477 lines)
- `backend/app/agent/dispatcher.py` ❌ (100 lines)
- `backend/app/agent/hooks.py` ❌ (80 lines)

---

## Post-Migration Benefits

### Immediate:
- ✅ Conversation history works
- ✅ update_task tool available
- ✅ Cleaner codebase
- ✅ Faster development

### Medium-term:
- ✅ Easy to switch models
- ✅ Better debugging with LangSmith
- ✅ Community support
- ✅ Less maintenance

### Long-term:
- ✅ Multi-agent workflows
- ✅ Human-in-the-loop approvals
- ✅ Complex reasoning chains
- ✅ Production-ready scaling

---

## Conclusion

**Recommendation: Migrate to LangChain + LangGraph**

We've reached the inflection point where maintaining custom code costs more than adopting a framework. The migration will:

1. **Solve current blockers** (conversation history, update_task)
2. **Reduce code by 82%** (1,118 → 200 lines)
3. **Enable model switching** (Ollama ↔ OpenRouter ↔ Claude)
4. **Future-proof** the system with battle-tested infrastructure

**Start fresh in new session with this plan as context.**

---

## References for New Session

**Key Files to Review:**
- `docs/agentic-assistant-plan.md` - Current implementation details
- `backend/app/agent/planner.py` - Custom planner to replace
- `backend/app/agent/tools.py` - Tools to convert to `@tool`
- `backend/tests/agent_test_cases.json` - Test scenarios to validate
- `backend/scripts/test_agent.sh` - Test runner

**LangChain Resources:**
- https://python.langchain.com/docs/integrations/llms/ollama
- https://python.langchain.com/docs/modules/agents/
- https://langchain-ai.github.io/langgraph/tutorials/introduction/
- https://docs.smith.langchain.com/ (observability)

**Commands to Run:**
```bash
# Activate venv
cd backend && source venv/bin/activate

# Install LangChain
pip install langchain langchain-ollama langgraph

# Test current system before migration
./backend/scripts/test_agent.sh -q "Create task for meeting"
```
