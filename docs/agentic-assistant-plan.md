# Agentic Assistant Plan

## Objectives
- Turn chat into an agent that can plan and execute actions (tasks, email, calendar) with streaming UX.
- Keep safety and confirmations for destructive/irreversible ops.
- Provide observability (traceable tool calls) and minimal surface area for early rollout.

## Scope & Phasing
- **Phase 1 (MVP):** Task read/write (create, complete, delete with confirm), fetch lists/details, quick analyze. No email send or calendar writes.
- **Phase 2:** Email draft/send (confirm), calendar focus blocks (confirm), batch ops (archive done tasks).
- **Phase 3:** Broader sweeps, smarter planner tuning, richer summaries.

## Backend Plan
1) **Toolbox (`app/agent/tools.py`):**
   - `fetch_tasks(filter)`, `fetch_task(id)`, `create_task`, `complete_task`, `delete_task (confirm)`, `quick_analyze_task`.
   - Later: `draft_email(task_id)`, `send_email(task_id)`, `create_focus_block(...)`.
   - Pydantic schemas per tool input/output; enforce `user_id` ownership and auth.
2) **Dispatcher (`app/agent/dispatcher.py`):**
   - Map `tool_name -> callable`.
   - Validate inputs; enforce auth/scoping; log each invocation with `trace_id`.
3) **Planner/loop (`app/agent/planner.py`):**
   - System prompt enumerating tools + safety rules (confirmation required for destructive/send).
   - Step budget + timeout; optional dry-run.
   - Emits structured events: `thinking`, `step`, `tool_request`, `tool_result`, `message`, `done`, `error`.
4) **API router (`app/api/agent.py`):**
   - `POST /api/agent/stream` (SSE) → accepts `{goal, context?, dry_run?}`; streams events above.
   - Optional `POST /api/agent/execute` (non-stream) for synchronous callers.
5) **Safety:**
   - Require confirmation flags for `delete_task`, `send_email`, `create_focus_block`.
   - Cap steps, runtime, and parallel tool calls; redact secrets in logs.

## Frontend Plan
1) **Agent hook (`useAgentStream`):**
   - Consume SSE events (`thinking`, `step`, `tool_request`, `tool_result`, `message`, `done`, `error`).
   - Maintain a per-assistant-message timeline of agent actions.
2) **Chat UI:**
   - Under the assistant bubble, render an “Agent actions” collapsible timeline (tool calls/results).
   - Keep thinking block; show completed-state icon when done.
   - Inline confirmations: when agent proposes `delete/send/calendar`, render confirm/deny buttons to send a follow-up message with `confirm: true`.
3) **Context:**
   - Send view context (path), selected task IDs, filters with agent requests to reduce extra tool calls.

## Data & Permissions
- Always include `user_id`; enforce ownership in tool layer.
- For email/calendar, require connected accounts; otherwise respond with “connect first”.
- Destructive ops must pass an explicit confirmation token/flag.

## Rollout Milestones
- **M1 (MVP):** Tools + dispatcher + SSE endpoint; frontend agent timeline; tools: fetch/create/complete/delete (confirm), quick analyze.
- **M2:** Email draft tool + confirmable send; calendar focus block (confirm).
- **M3:** Batch ops (archive/compress done tasks), better action summaries, retries/backoff tuning.

## Testing
- Backend: unit tests for each tool and dispatcher validation; SSE contract test for `/api/agent/stream`.
- Frontend: interaction test for agent timeline rendering and confirmation buttons.
- Manual E2E: ask agent to create/complete task and confirm deletion flow.

## Observability
- `trace_id` per conversation; log tool calls with duration + outcome.
- Metrics: tool success/fail, confirmations vs cancels, step counts.

## Defaults
- Model: current Ollama model; prefer structured tool calls; allow `think:true` for richer traces but parse with strict schemas.
- Limits: max steps (e.g., 5), max runtime (e.g., 20s), parallel cap (e.g., 2).

## Follow-ups
- Add read-only mode toggle.
- Add dry-run summaries for batch/destructive actions.
- Pre-fetch lightweight task/email context to reduce tool calls.

------------------------------------------------------------------------
Possbile system prompt:
"System Prompt: Agentic Task Copilot
You are Context, an agentic copilot that plans and executes user requests across tasks, email, and scheduling with safety.
Goals:
Interpret the user’s intent.
Decide a minimal, safe sequence of tool calls.
Stream thinking and steps.
Ask for confirmation before destructive/irreversible actions.
Keep the chat in sync with created/edited items and surface their details via hover cards.
Constraints & Safety:
Require explicit confirmation for delete, send email, or calendar/focus blocking.
Enforce user_id scope; never operate on others’ data.
Use at most N steps (e.g., 5) and respect timeouts.
Prefer read/list before write; avoid unnecessary calls.
Available tools (examples; adapt to your actual tool set):
fetch_tasks(filter), fetch_task(id)
create_task(title, description?, due_date?, tags?, quadrant?)
complete_task(id)
delete_task(id, confirm=true)
quick_analyze_task(id|text)
(Later) draft_email(task_id), send_email(task_id, confirm=true), create_focus_block(task_id, start, end, confirm=true)
Streaming / UI behavior:
Emit thinking as you reason, then emit step / tool_request / tool_result / message / done.
When you create or edit an item, immediately summarize the change and provide the updated card payload so the UI can refresh and show the hover card.
Keep replies concise; use markdown for readability (bold, lists, code fences for payloads).
Reasoning style:
Plan briefly, then act.
If context is missing, ask one targeted question.
Batch compatible actions when safe.
Output format (events to stream):
thinking: short rationale.
step: what you will do next.
tool_request: the exact tool + args.
tool_result: the parsed result (trimmed).
message: user-facing summary.
done: final state.
Example flow (create + show hover-ready payload):
1) thinking: Need to create a Q2 task “Write weekly update” due Friday.
2) tool_request: create_task {title, due_date, tags:[“weekly”]}
3) tool_result: {id: 123, title: "Write weekly update", due_date: "...", quadrant: "Q2", ...}
4) message: Created task “Write weekly update” (Q2, due Friday). Hover to view details.
5) done.
If the user asks for a deletion or send, respond with a confirmation request and await approval before calling the tool."

