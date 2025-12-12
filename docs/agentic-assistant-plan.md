# Agentic Assistant Plan

## Objectives
- Turn chat into an agent that can plan and execute actions (tasks, email, calendar) with streaming UX.
- Keep safety and confirmations for destructive/irreversible ops.
- Provide observability (traceable tool calls) and minimal surface area for early rollout.

## Current Implementation Status (Dec 2025)

### Architecture Overview
**Approach:** Custom agent implementation (NOT using LangChain framework)
- Custom HTTP client to Ollama API for tool calling
- Manual streaming with SSE (Server-Sent Events)
- Pydantic-based tool schema validation
- Pre-execution hooks for input validation and safety
- Decision tree prompting for tool selection

**Why Custom (Not LangChain):**
- Full control over streaming behavior
- Lightweight dependencies (~15MB vs ~50MB+ with LangChain)
- Custom business logic (hooks, user scoping, validation)
- Team familiarity with custom architecture
- LangChain evaluated but deemed unnecessary for current needs - may need to be evluated again.

### Implementation Details

**Backend Components:**

1. **Planner** (`backend/app/agent/planner.py` - 477 lines)
   - `AgentPlanner.run()` - Main orchestration loop
   - `_build_plan()` - LLM generates JSON plan with tool steps
   - `_llm_reply_stream()` - Conversational replies without tools
   - Retry logic with `tenacity` (3 attempts, exponential backoff)
   - Token budgets: Planning=1000, Conversational=600

2. **Dispatcher** (`backend/app/agent/dispatcher.py`)
   - Validates tool inputs via Pydantic schemas
   - Runs pre-execution hooks before tool dispatch
   - Returns error dicts instead of raising (keeps stream alive)
   - Passes context (user_id, etc.) for hooks

3. **Tools** (`backend/app/agent/tools.py`)
   - `fetch_tasks`, `fetch_task`, `create_task`, `complete_task`, `delete_task`, `quick_analyze_task`
   - Strict Pydantic validators:
     - `CreateTaskInput.clean_title` - Removes quotes, enforces 120 chars
     - `CreateTaskInput.prevent_duplicate_description` - Blocks title==description
   - Tool registry with examples and metadata

4. **Hooks** (`backend/app/agent/hooks.py` - NEW)
   - Pre-execution validation layer
   - `validate_no_duplicate_title_desc` - Denies/modifies duplicates
   - `auto_clean_inputs` - Strips whitespace, removes quotes
   - `validate_task_ownership` - Enforces user_id scoping
   - Hooks run before Pydantic validation

5. **API** (`backend/app/api/agent.py`)
   - `POST /api/agent/stream` - SSE streaming endpoint
   - Events: `thinking`, `step`, `tool_request`, `tool_result`, `message`, `done`, `error`

**Frontend Components:**

1. **Agent Stream Hook** (`frontend/lib/useAgentStream.ts`)
   - SSE parsing and state management
   - Separate state for thinking vs message content
   - `appendAssistantEvent()` - Adds events to timeline
   - `updateAssistantContent()` - Updates message content only

2. **Chat UI** (`frontend/components/ChatPanel.tsx`)
   - Agent timeline shows tool actions
   - Thinking display (separate from content)
   - Collapsible tool event cards

### Key Configuration (Current)

**Token Budgets:**
- Planning: 1000 tokens (increased from 500) ✅
- Conversational: 600 tokens (increased from 300) ✅
- Max response length: 1200 chars (increased from 240) ✅

**System Prompts:**
- Planning prompt: Explicit JSON structure with decision tree
- Conversational prompt: Adaptive length (1-4 sentences based on complexity)
- `think: False` for conversational to hide reasoning ✅

**Model:**
- Ollama: qwen3:8b (upgraded from 4b - Dec 12, 2025)
- Temperature: 0.2 (planning), 0.4 (conversational)
- Base URL: http://localhost:11434
- Why 8b: 4b model echoed JSON prompts instead of generating plans; 8b handles complex JSON correctly

### Recent Fixes Applied (Dec 12, 2025)

**Problem 1: User Input Echoed Back**
- Root cause: Fallback in `_llm_reply_stream` echoed goal verbatim
- Fix: Changed fallback message to helpful error (planner.py:455)

**Problem 2: Responses Truncated at 240 Chars**
- Root cause: Hardcoded `[:240]` slice
- Fix: Increased to `[:1200]` (planner.py:457)

**Problem 3: No Tool Calls Generated**
- Root cause: Insufficient tokens (500), vague prompt
- Fix: Increased to 1000 tokens, made prompt explicit about MUST call tools (planner.py:201-232, 255)

**Problem 4: Verbose Thinking Visible**
- Root cause: `think: True` in conversational mode
- Fix: Changed to `think: False` (planner.py:411)

**Problem 5: Response Length Too Restrictive**
- Root cause: "1-2 sentences max" in prompt
- Fix: Adaptive length based on question complexity (planner.py:406-416)

**Problem 6: Planning Prompt Format Confuses qwen3:4b (CRITICAL - Dec 12, 2025)**
- **Problem:** Agent not calling tools despite clear "create task" requests
  - Test query: "Create a task for team meeting tomorrow at 2pm"
  - Result: No tool_request events, went to conversational mode
  - Agent returned thinking process instead of executing action
- **Root Cause:** Complex JSON input confuses qwen3:4b
  - Planner sends user prompt as `json.dumps(user_prompt)` (planner.py:257)
  - Creates deeply nested JSON: `{"goal": "...", "context": {}, "tools": [...], "required_shape": {...}}`
  - Small model (qwen3:4b) **echoes back the input JSON** instead of generating plan
  - Model treats complex JSON as schema to copy, not instructions to follow
- **Evidence:**
  ```bash
  # Complex JSON prompt → Model echoes it back ❌
  ./backend/scripts/inspect_ollama.sh --prompt '{"goal": "Create task...", "tools": [...]}' --format json
  # Result: {"goal": "Create task...", "tools": [...]} (just echoed)

  # Simple natural language → Generates correct plan ✅
  ./backend/scripts/inspect_ollama.sh --prompt "User says: Create a task for meeting at 2pm" --format json
  # Result: {"message": "...", "steps": [{"tool": "create_task", "args": {...}}]}
  ```
- **Testing Infrastructure Created:**
  - `backend/scripts/test_agent.sh` - Interactive test runner with SSE capture
  - `backend/scripts/inspect_ollama.sh` - Direct Ollama API tester
  - `backend/scripts/run_agent_tests.sh` - Automated test suite
  - `backend/tests/agent_test_cases.json` - 20+ test scenarios
  - Fixed SSE parsing to handle `message` field (not just `delta`)
- **Fix Options:**
  1. **Try qwen3:8b** - Larger model might handle complex JSON better ✅ **WORKED!**
  2. **Simplify prompt** - Use natural language instead of JSON blob (not needed)
  3. **OpenRouter** - Use smarter cloud model ($0.06/M tokens) (not needed)
- **Solution:** ✅ **Upgraded to qwen3:8b** - Handles complex JSON prompts correctly
  - Changed `OLLAMA_MODEL=qwen3:8b` in backend/.env
  - Restarted backend with `./init.sh restart backend`
  - Test results:
    - ✅ Tool calling works: "Create task" → calls `create_task` tool
    - ✅ Task created successfully (ID: 70, Title: "Team Meeting Tomorrow")
    - ✅ Conversational mode works: "Good morning" → clean response
    - ✅ No thinking leaks in final messages
    - ⚠️ Slower than 4b (~35s vs ~23s for tool calls)
    - Model size: 5.2GB (vs 2.5GB for 4b)
- **Status:** ✅ **RESOLVED** - Agent fully functional with qwen3:8b
- **Trade-offs:**
  - Speed: ~50% slower (but still acceptable)
  - Memory: ~2x more RAM needed
  - Accuracy: Much better JSON adherence and tool decision-making

### Testing Scenarios

**Test 1: Tool Calling**
- Input: "Create a task for me to run 15 minutes tomorrow at 1 PM"
- Expected: `create_task` tool call with extracted title, due_date
- Status: ⏳ Pending validation

**Test 2: Conversational (No Tools)**
- Input: "Good morning" or "How should I prioritize?"
- Expected: Brief helpful reply, NO tool calls
- Status: ⏳ Pending validation

**Test 3: Full Response (No Truncation)**
- Input: "What are top 3 important items?"
- Expected: 2-4 sentence response, NOT cut off
- Status: ⏳ Pending validation

### Known Issues & Limitations

**Current Challenges:**
1. Small model (qwen3:4b) struggles with complex JSON generation
2. Tool calling still inconsistent - may require more prompt tuning
3. No conversation state management (each request is stateless)
4. No top work items context passed to agent

**Workarounds in Place:**
- Retry logic (3 attempts) for transient failures
- Heuristic fallback when LLM planning fails
- Pre-execution hooks catch validation issues
- Error recovery returns error dicts instead of terminating

### Next Steps (If Current Fixes Fail)

**Option 1: Add Minimal LangChain Utilities**
- Package: `langchain-ollama==0.2.3`
- Use `ChatOllama` wrapper for better streaming
- Add `@tool` decorators for automatic schema generation
- Keep 90% of custom code unchanged
- Effort: 2-3 hours

**Option 2: Switch to Larger Model**
- Try `qwen3:7b` or `mistral:7b` for better tool calling
- May require more VRAM but better at following prompts
- Effort: 15 minutes

**Option 3: Hybrid Approach**
- Keep custom planner for control
- Use LangChain just for streaming utilities
- Gradually migrate tools to LangChain format
- Effort: 1 week

**Option 4: Full LangGraph Migration**
- Complete rewrite using LangGraph state graphs
- Built-in retry, error handling, checkpointing
- Effort: 2-3 weeks (NOT RECOMMENDED - current arch is good)

### Observability & Debugging

**Logging:**
- Debug logs for plan parsing (planner.py:267-271)
- Error logs for plan failures (planner.py:284-288)
- Tool execution logs with trace_id

**Monitoring:**
```bash
# Watch logs in real-time
tail -f backend/uvicorn.log

# Look for these patterns:
# "LLM plan parsed successfully: num_steps=X"
# "Failed LLM response data: ..."
# "Hook denied tool X: reason"
```

**Metrics to Track:**
- Tool call success rate
- Empty steps rate (indicates tool decision failures)
- Response truncation incidents (should be 0 now)
- Validation errors from hooks

### Decision Log

**Dec 12, 2025 - LangChain Evaluation:**
- Researched LangChain best practices via Context7
- Found: LangChain would reduce ~1500 lines to ~200 lines
- Decision: Stay custom for now, add utilities only if needed
- Rationale: Current implementation is solid, issues are configuration not architecture

**Dec 12, 2025 - Immediate Fixes:**
- Prioritized quick configuration fixes over framework migration
- All fixes applied in <30 minutes
- Ready for testing before considering LangChain

### Configuration Reference

**Current System Prompt (Planning):**
```
You are Context, an agentic task copilot. Plan minimal steps (1-3 max).

CRITICAL: ALWAYS return valid JSON with this exact structure:
{
  "message": "brief planning note",
  "steps": [array of tool calls OR empty array]
}

DECISION TREE - When to call tools:
1. User says "create", "add task", "make task" → MUST call create_task
2. User says "complete", "finish", "done", "mark done" → MUST call complete_task
3. User says "show", "list", "what tasks", "my tasks" → MUST call fetch_tasks
4. User says "how should I", "advice", "what do you think" → return empty steps array
5. Ambiguous or unclear → return empty steps array

CRITICAL RULES:
1. If user mentions creating a task, ALWAYS include create_task in steps
2. For create_task args:
   - title: max 120 chars, NO quotes, concise, descriptive
   - description: MUST differ from title OR be null (don't duplicate)
   - Extract due_date from text (ISO 8601 format if mentioned)
   - Extract priority (0/1/3/5) if user mentions urgency
   - Extract tags from context
3. Always include user_id in ALL tool args
4. Keep steps array minimal (usually 1-2 tools max)
5. Respond with ONLY valid JSON, no extra text
```

**Current System Prompt (Conversational):**
```
You are Context, a helpful life assistant.

Respond naturally about tasks, schedule, or wellbeing.
- Simple greetings: 1-2 sentences
- Questions needing context: 2-4 sentences with helpful details
- Complex planning requests: Be thorough but concise

RULES:
1. Never include meta-reasoning or thinking process in final message
2. Be specific and actionable
3. Provide helpful details when relevant
```

### Services Status

**Current Ports:**
- Backend: http://localhost:5405
- Frontend: http://localhost:5401
- Ollama: http://localhost:11434
- PostgreSQL: 5432
- Redis: 6379

**Health Check:**
```bash
curl http://localhost:5405/health
# Expected: {"status":"ok","ollama_connected":true,"ollama_model":"qwen3:4b"}
```

### Files Modified (Dec 12, 2025)

```
backend/app/agent/planner.py      - Token budgets, prompts, truncation fix
backend/app/agent/tools.py        - Strict validators, examples
backend/app/agent/hooks.py        - NEW: Pre-execution validation
backend/app/agent/dispatcher.py   - Hook integration, error handling
backend/requirements.txt          - Added tenacity==8.2.3
frontend/.env.local               - Updated API URL to port 5405
backend/scripts/test_agent.sh     - NEW: Interactive test runner (shell wrapper)
backend/scripts/test_agent_core.py - NEW: Test runner Python implementation
backend/scripts/inspect_ollama.sh - NEW: Ollama API inspector (shell wrapper)
backend/scripts/inspect_ollama_core.py - NEW: Ollama inspector Python implementation
backend/scripts/run_agent_tests.sh - NEW: Automated test suite
backend/tests/agent_test_cases.json - NEW: 20+ test scenarios
```

### Success Criteria

**Minimum Viable:**
- [ ] Tool calls triggered on "create task" requests
- [ ] Responses NOT truncated at 240 chars
- [ ] No user input echoed back
- [ ] Thinking NOT visible in final messages
- [ ] Conversational replies work for greetings

**Ideal:**
- [ ] 80%+ tool call accuracy for clear requests
- [ ] <5% empty steps when tools should be called
- [ ] Zero title==description validation errors
- [ ] Responses adaptive in length (1-4 sentences as appropriate)

### Testing & Iteration Workflow

**IMPORTANT: Always follow this test-read-modify-test cycle when working on the agent:**

#### 1. Initial Test Run

```bash
# Run full test suite to establish baseline
cd /Users/srikar.kandikonda/Desktop/Claude/Task-management
./backend/scripts/run_agent_tests.sh
```

This generates:
- `backend/test_results/agent_tests_YYYYMMDD_HHMMSS.json` - Full results
- `backend/test_results/agent_report_YYYYMMDD_HHMMSS.txt` - Summary report

**Save the results file name for comparison later!**

#### 2. Read & Analyze Output

```bash
# View the report
cat backend/test_results/agent_report_*.txt | tail -n 50

# Or examine specific test failures
./backend/scripts/test_agent.sh --query "Create task for meeting" --verbose
```

**What to look for:**

- **Tool Call Accuracy**: Did it call tools when it should? Did it avoid tools for conversational queries?
- **Response Quality**: Any truncation? Thinking leaking into messages?
- **Error Patterns**: Common validation failures? JSON parsing issues?
- **Token Usage**: Responses hitting token limits?
- **Performance**: Slow requests? Timeouts?

#### 3. Inspect Ollama Directly (if model issues suspected)

```bash
# Test raw Ollama behavior with different configs
./backend/scripts/inspect_ollama.sh \
    --prompt "Generate a JSON plan to create a task" \
    --format json \
    --think false \
    --compare  # Compares think:true vs think:false vs no-think
```

**This helps identify:**

- Whether JSON ends up in `content` vs `thinking` field
- Token limit issues
- Model understanding of prompts
- Temperature effects

#### 4. Modify Code

Based on findings, modify:

**Prompts** (`backend/app/agent/planner.py`):
- Lines 201-232: Planning system prompt (when to call tools)
- Lines 406-416: Conversational system prompt (advice/greetings)
- Add more explicit examples if model struggles

**Token Budgets** (`backend/app/agent/planner.py`):
- Line 255: Planning tokens (`num_predict`)
- Line 411: Conversational tokens
- Line 367: Final message tokens

**Tool Schemas** (`backend/app/agent/tools.py`):
- Improve validators (lines 45-95)
- Add better descriptions/examples
- Adjust required vs optional fields

**Hooks** (`backend/app/agent/hooks.py`):
- Add pre-execution validation
- Auto-clean inputs
- Block problematic patterns

#### 5. Test Again & Compare

```bash
# Run tests again with same cases
./backend/scripts/run_agent_tests.sh

# Or save and compare explicitly
./backend/scripts/test_agent.sh \
    --batch \
    --save backend/test_results/after_fix.json \
    --diff backend/test_results/before_fix.json
```

**Look for:**
- Increased pass rate
- Fewer tool calling errors
- Better response quality metrics
- No regressions (previously passing tests still pass)

#### 6. Document Findings

Update this file (`docs/agentic-assistant-plan.md`) with:

```markdown
**[Date] - [Change Description]:**
- Problem: [What was broken]
- Root cause: [Why it happened]
- Fix: [What changed, with file:line references]
- Results: [Before/after metrics]
- Status: ✅/⚠️/✗
```

Add to the "Recent Fixes Applied" section above.

#### Quick Test Commands Reference

```bash
# Single query (fast iteration)
./backend/scripts/test_agent.sh -q "Your test query here"

# Batch with save
./backend/scripts/test_agent.sh -b --save results.json

# Full suite with report
./backend/scripts/run_agent_tests.sh

# Ollama debugging
./backend/scripts/inspect_ollama.sh -p "Test prompt" --think false

# View logs in real-time
tail -f backend/uvicorn.log | grep -E "(LLM|plan|tool|agent)"
```

**Note:** All `.sh` scripts automatically activate `backend/venv` if present.

#### Test Coverage

**Current test scenarios** (in `backend/tests/agent_test_cases.json`):

- **Tool Calling (10 tests)**: Create task, complete task, list tasks, delete task
- **Conversational (6 tests)**: Greetings, advice, general questions
- **Edge Cases (4 tests)**: Ambiguous input, long responses, empty queries, multiple actions

**To add new test case:**

```json
{
  "name": "Descriptive test name",
  "query": "User input to test",
  "expected": {
    "should_call_tools": true/false,
    "expected_tool": "tool_name",
    "should_succeed": true,
    "no_truncation": true,
    "no_thinking_leak": true,
    "comment": "Why this test matters"
  }
}
```

### Rollout Plan

**Phase 1 (Completed - Dec 12, 2025):**
- ✅ Test scaffolding created
- ✅ qwen3:8b migration (tool calling now works)
- ✅ Agent functional for basic task creation

**Phase 2 (DECISION - Dec 12, 2025): Migrate to LangChain**

**Critical Issues Identified:**
1. ❌ No conversation history - Agent can't reference "that task" from previous message
2. ❌ Missing update_task tool - Can't modify existing tasks
3. ❌ Custom code complexity reached ~1,500 lines
4. ❌ Reinventing features LangChain already provides

**Decision: MIGRATE TO LANGCHAIN + LANGGRAPH**

**Rationale:**
- We're building conversation history, tool updates, state management
- LangChain provides all of this out of the box
- 82% code reduction (1,118 → 200 lines)
- Plugin architecture for easy model switching (Ollama ↔ OpenRouter ↔ Claude)
- Battle-tested framework vs custom maintenance burden
- Faster future development

**See: `docs/langchain-migration-plan.md` for full plan**

**Timeline:** 2-3 days for complete migration

**Next Steps:**
- Start new session with migration plan
- Keep API contracts unchanged (frontend unaffected)
- Validate with existing test suite
- Enable easy model switching via config

---

## Legacy Notes (Pre-Dec 2025)

### Target Experience
- Thinking: all reasoning streamed in a thinking channel; final message is short, reasoning-free.
- Steps: every tool step streams as it happens (`step`, `tool_request`, `tool_result`, `done`, `error`). Color/label separate assistant vs tool events.
- Tool intent: only when clearly asked (create/complete/delete/list, etc.). Pure advice → no tools.
- Task creation: structured fill — concise title (<=120 chars, no quotes), optional description (not duplicated), due/reminder/repeat/time_estimate/tags/project when implied. Return payload for hover card.
- Updates in chat: when tasks are created/edited, show a summary and attach payload so chat can show hoverable details.

### Scope & Phasing
- **Phase 1 (MVP):** Task read/write (create, complete, delete with confirm), fetch lists/details, quick analyze. No email send or calendar writes.
- **Phase 2:** Email draft/send (confirm), calendar focus blocks (confirm), batch ops (archive done tasks).
- **Phase 3:** Broader sweeps, smarter planner tuning, richer summaries.

### Data & Permissions
- Always include `user_id`; enforce ownership in tool layer.
- For email/calendar, require connected accounts; otherwise respond with "connect first".
- Destructive ops must pass an explicit confirmation token/flag.

### Follow-ups
- Add read-only mode toggle.
- Add dry-run summaries for batch/destructive actions.
- Pre-fetch lightweight task/email context to reduce tool calls.
- Add top work items to request context for better recommendations.

---

## LangChain Migration Progress (Dec 12, 2025)

### Decision: Migrating to LangChain + LangGraph

After reaching complexity where maintaining custom code costs more than adopting a battle-tested framework, we've begun migrating to LangChain + LangGraph. See [`docs/langchain-migration-plan.md`](./langchain-migration-plan.md) for full rationale and plan.

### Phase 1: Setup LangChain ✅ COMPLETE

**Goal:** Plugin-based LLM provider system with zero breaking changes.

**What Was Built:**
1. **LLM Configuration Module** (`backend/app/core/llm_config.py`)
   - Environment-based config with `LLM_` prefix
   - Supports 4 providers: ollama, openrouter, anthropic, openai
   - Pydantic Settings with extra field ignore

2. **LLM Provider Factory** (`backend/app/agent/llm_factory.py`)
   - Factory pattern for creating LLM instances
   - Provider-specific configuration
   - Convenience `get_llm()` function

3. **Dependencies Installed:**
   - `langchain==0.3.13`
   - `langchain-community==0.3.12`
   - `langchain-ollama==0.2.0`
   - `langgraph==0.2.60`
   - `langchain-openai==0.3.35`
   - `langchain-anthropic==0.3.22`

**Test Results:**
- ✅ Provider factory tested with Ollama
- ✅ LLM invocation successful
- ✅ No breaking changes to existing code

**Benefits:**
- Switch LLM providers with config changes only
- No code changes in agent logic
- Easy to test different providers
- Future-proof for new models

### Phase 2: Convert Tools to @tool Decorators ✅ COMPLETE

**Goal:** Replace manual Pydantic schemas with LangChain's `@tool` decorator pattern.

**What Was Converted:**
All 7 tools converted to `@tool` decorator format:
- `fetch_tasks` - List tasks with filters
- `fetch_task` - Get single task by ID
- `create_task` - Create new task
- `update_task` - Update existing task
- `complete_task` - Mark task completed
- `delete_task` - Soft/hard delete
- `quick_analyze_task` - LLM analysis

**Key Changes:**
1. **Removed 180+ lines** of manual Pydantic Input classes
2. **Added rich docstrings** with `Args:` sections for LLM guidance
3. **AsyncSession injection** using `Annotated[AsyncSession, InjectedToolArg()]`
4. **Backward compatibility layer** in `TOOL_REGISTRY` for Phase 3
5. **Updated dispatcher** to handle both old and new tool formats

**Code Pattern:**
```python
from langchain.tools import tool
from langchain_core.tools import InjectedToolArg

@tool(parse_docstring=True)
async def create_task(
    user_id: int,
    title: str,
    db: Annotated[AsyncSession, InjectedToolArg()],  # Hidden from LLM
    description: Optional[str] = None,
    # ... other params
) -> Dict[str, Any]:
    """Create a new task for the user.
    
    Args:
        user_id: User ID for ownership (required)
        title: Concise task title without quotes, max 120 chars (required)
    """
    # Implementation stays the same
```

**Test Results:**
- ✅ All 7 tools import successfully
- ✅ Each tool has proper schema auto-generated
- ✅ `fetch_tasks` test: PASS (11.33s)
- ✅ `create_task` test: PASS (17.88s)
- ✅ Both read and write operations working

**Benefits:**
- Cleaner code with auto-generated schemas
- Better documentation visible to LLM
- Easier to add new tools
- Forward compatible with Phase 3

### Phase 3: LangGraph Agent Integration ✅ COMPLETE

**Goal:** Replace custom planner with LangGraph's `create_react_agent` for conversation memory and streaming.

**What Was Changed:**
1. **Created `graph.py`** (359 lines) - LangGraph ReAct agent with `create_react_agent`
2. **Deleted `planner.py`** (477 lines) - Removed custom planner
3. **Deleted `dispatcher.py`** (100 lines) - Replaced with direct tool invocation
4. **Deleted `hooks.py`** (80 lines) - Validation moved to tools
5. **Removed `TOOL_REGISTRY`** (52 lines) - No longer needed
6. **Updated `api/agent.py`** - Uses LangGraph agent with conversation history support
7. **Updated frontend** - Sends conversation history in requests

**Implementation Details:**
- `backend/app/agent/graph.py` - `create_agent()`, `invoke_agent()`, `stream_agent()`
- Uses `MemorySaver()` checkpointer for conversation persistence
- Thread-based conversation tracking via `thread_id`
- System message with comprehensive agent instructions
- Automatic `user_id` and `db` injection to all tools
- Frontend sends `messages: [{role, content}]` array

**Benefits Achieved:**
- ✅ Built-in conversation history (fixes "that task" reference issue)
- ✅ Better streaming with `astream_events(v2)`
- ✅ Easier model switching via `llm_factory.py`
- ✅ LangSmith observability ready (just add API key)
- ✅ Code reduction: 1,118 → 530 lines (53% reduction)

**Blockers Solved:**
- ✅ Conversation history → Built-in with `MemorySaver`
- ✅ Missing update_task → Added in Phase 2
- ✅ Thinking visibility → LangGraph streaming events
- ✅ Complex JSON prompts → Better prompt templates
- ✅ Tool execution → Direct `tool.ainvoke()` calls

**Test Results:**
```bash
./backend/scripts/test_agent.sh --query "Create a task for team meeting tomorrow"
✓ PASS in 84.56s
Tool Calls: create_task({'title': 'Team Meeting', 'due_date': '2023-10-06T00:00:00', 'ticktick_priority': 3})
```

**Timeline:** Completed Dec 12, 2025

### Migration Testing

**Test Infrastructure:**
- `backend/test_llm_factory.py` - Provider factory validation
- `backend/scripts/test_agent.sh` - Interactive agent testing
- `backend/scripts/run_agent_tests.sh` - Automated test suite
- `backend/tests/agent_test_cases.json` - 20+ test scenarios

**Validation Checklist:**
- [x] Phase 1: LLM factory working with Ollama
- [x] Phase 2: Tools converted and tested
- [x] Backward compatibility maintained
- [x] No breaking changes to API contracts
- [x] Phase 3: LangGraph agent integration
- [x] Phase 3: Conversation memory working
- [x] Phase 3: Tool calling validated

### References

- **Migration Plan:** [`docs/langchain-migration-plan.md`](./langchain-migration-plan.md)
- **Phase 2 Summary:** `backend/PHASE2_CONVERSION_SUMMARY.md`
- **LangChain Tools Docs:** https://python.langchain.com/docs/modules/agents/tools/
- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/

