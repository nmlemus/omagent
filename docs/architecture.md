# Architecture

This document describes omagent's internal architecture for developers who want to understand, extend, or contribute to the project.

## Design Principles

1. **Generic core, specialized packs** -- the engine knows nothing about data science or Flutter; domain knowledge lives in packs
2. **Streaming everything** -- every operation produces events that flow through the system in real-time
3. **Tools as the interface** -- the LLM interacts with the world exclusively through tools; skills are loaded via a tool
4. **Full observability** -- every LLM call, tool execution, and decision is logged to a JSONL journal
5. **Pack-agnostic loop** -- the same AgentLoop runs regardless of domain

## System Overview

```
                                    omagent
 +------------------------------------------------------------------+
 |                                                                    |
 |   CLI / TUI              Server (FastAPI)                         |
 |   +--------+             +------------------+                     |
 |   | Click  |             | REST  SSE  WS    |                     |
 |   | Textual|             | /chat /stream /ws|                     |
 |   +---+----+             +--------+---------+                     |
 |       |                           |                               |
 |       +----------+  +------------+                                |
 |                  |  |                                              |
 |              +---v--v---+                                         |
 |              | AgentLoop |  <-- core engine                       |
 |              +-----+-----+                                        |
 |                    |                                               |
 |     +--------------+---------------+                              |
 |     |              |               |                              |
 | +---v----+   +-----v------+  +----v-------+                      |
 | |Provider |   |ToolRegistry|  |  Session   |                      |
 | |(LiteLLM)|   |            |  | (messages) |                      |
 | +---+-----+   +-----+------+  +----+-------+                      |
 |     |               |              |                              |
 |     |        +------+------+       |                              |
 |     |        |      |      |       |                              |
 |     |     Builtin Pack   MCP       |                              |
 |     |     Tools   Tools  Tools     |                              |
 |     |                              |                              |
 |  +--v-----------+   +---------+   +----------+                   |
 |  |PermissionPolicy|  |Workspace|   |SessionStore|                  |
 |  +--------------+   +---------+   +----------+                   |
 |                                                                    |
 |  Cross-cutting: Journal | Tracker | Memory | Planner | Skills     |
 +------------------------------------------------------------------+
```

## Core Components

### AgentLoop (`core/loop.py`)

The heart of the system. Implements the agentic tool loop pattern:

```
1. User message --> Session (add to history)
2. Session messages + system prompt + tool schemas --> LLM
3. Stream LLM response:
   - Text chunks --> yield TextDeltaEvent
   - Tool calls --> collect ToolCallEvents
4. For each tool call:
   a. Check permission (auto / prompt / deny)
   b. Execute tool via ToolRegistry
   c. Add result to Session
   d. yield ToolResultEvent
5. Loop to step 2 (LLM sees tool results, may call more tools)
6. No more tool calls --> yield DoneEvent, stop
```

**Key behaviors:**
- Maximum 20 iterations to prevent infinite loops
- Conversation summarization triggers automatically when message count is high
- Plans are detected from early LLM responses (first 2 iterations)
- Memory context is injected into the system prompt on session resume
- Token usage is tracked cumulatively per session

### Event System (`core/events.py`)

All communication between the loop and frontends happens through typed events:

| Event | When | Data |
|-------|------|------|
| `TextDeltaEvent` | LLM generates text | `content: str` |
| `ToolCallEvent` | LLM requests a tool | `id, name, input` |
| `ToolResultEvent` | Tool execution completes | `tool_use_id, tool_name, result, is_error` |
| `PermissionPromptEvent` | Tool needs user approval | `tool_name, input` |
| `PermissionDeniedEvent` | Tool was denied | `tool_name, reason` |
| `ErrorEvent` | Something went wrong | `message: str` |
| `DoneEvent` | Turn complete | (none) |
| `SubAgentStartEvent` | Sub-agent spawned | `agent_id, pack_name, task` |
| `SubAgentDoneEvent` | Sub-agent finished | `agent_id, pack_name, result` |

Every event has a `to_dict()` method for JSON serialization (SSE/WebSocket).

### Session (`core/session.py`)

Manages conversation history in OpenAI message format:

```python
session.add_user_message("analyze this data")
session.add_assistant_message("I'll help you...", tool_calls=[...])
session.add_tool_result(tool_call_id, {"output": "..."})
```

**Persistence:** SQLite via `SessionStore` with async operations (aiosqlite).

**Features:**
- Fork sessions (deep copy with new ID)
- Export to JSON or Markdown
- Import from JSON
- Track cumulative tokens and cost

### Tool System

#### Base Class (`tools/base.py`)

Every tool implements four things:

```python
class MyTool(Tool):
    @property
    def name(self) -> str: return "my_tool"

    @property
    def description(self) -> str: return "Does something useful"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "..."}
            },
            "required": ["param"]
        }

    async def execute(self, input: dict) -> dict:
        # Do work
        return {"output": "result"}
        # Or on error:
        return {"error": "what went wrong"}
```

#### Tool Registry (`core/registry.py`)

Central catalog of all available tools:

```python
registry = ToolRegistry()
registry.register(ReadFileTool())
registry.register_many([WriteFileTool(), BashTool()])

schemas = registry.get_schemas()    # For LLM tool_use parameter
result = await registry.execute("read_file", {"path": "/tmp/f.txt"})
```

#### Built-in Tools

Available in every pack:

| Tool | Purpose |
|------|---------|
| `read_file` | Read file content |
| `write_file` | Create/overwrite files |
| `list_dir` | List directory contents |
| `bash` | Execute shell commands (30s timeout) |
| `Skill` | Load skill instructions on-demand |
| `remember` | Store persistent facts |
| `summarize` | Compress conversation history |
| `delegate` | Spawn sub-agents |

### Domain Packs (`packs/`)

A pack is a directory with a `pack.yaml` that configures the agent:

```yaml
name: data_science
version: "1.0"
description: Data science assistant

system_prompt: |
  You are Meridian, a senior data scientist...

tools:
  - omagent.packs.data_science.tools.jupyter_execute:JupyterExecuteTool
  - omagent.packs.data_science.tools.dataset_profile:DatasetProfileTool

permissions:
  jupyter_execute: auto
  write_file: prompt
  bash: prompt

mcp_servers:
  - command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem"]
```

**Pack search order:**
1. `omagent/packs/` (built-in)
2. `./packs/` (project-local)
3. `~/.omagent/packs/` (user global)

The `DomainPackLoader` resolves tool classes from dotted paths (`module:ClassName`), instantiates them, and builds the `DomainPack` dataclass.

### Skill System (`core/skill_loader.py`)

Skills are LLM-readable instruction files (`SKILL.md`) following the [Agent Skills](https://agentskills.io) spec.

**Discovery flow:**
1. Pack skills directory (`{pack_dir}/skills/`)
2. Project-local (`{cwd}/.omagent/skills/`)
3. User global (`~/.omagent/skills/`, `~/.claude/skills/`)
4. Walk-up from cwd ancestors (`.omagent/skills/` at each level)

**Loading pattern (Skill-as-Tool):**

Skills are NOT injected into the system prompt. Instead, the LLM sees an `<available_skills>` XML summary and calls the `Skill` tool to load full instructions when needed:

```
System prompt contains:
  <available_skills>
    <skill name="eda">Exploratory data analysis workflow</skill>
    <skill name="modeling">ML model training workflow</skill>
  </available_skills>

LLM decides it needs EDA instructions:
  --> Skill({ skill: "eda" })
  <-- { skill: "eda", prompt: "## EDA Workflow\n1. Profile the dataset..." }
```

This pattern (from claw-code-parity) keeps the system prompt small and lets context window management work naturally.

**Validation:** Uses the `skills-ref` library for spec-compliant parsing and validation.

### Permission System (`core/permissions.py`)

Three-level permission model:

| Level | Behavior |
|-------|----------|
| `auto` | Execute immediately, no user prompt |
| `prompt` | Yield `PermissionPromptEvent`, wait for approval |
| `deny` | Block execution, yield `PermissionDeniedEvent` |

**Priority order:**
1. Pack-level overrides (from `pack.yaml` permissions)
2. Tool defaults (e.g., `read_file` defaults to `auto`)
3. System default (`OMAGENT_DEFAULT_PERMISSION`)

### Provider (`providers/litellm_provider.py`)

Wraps LiteLLM for multi-provider LLM access:

```python
provider = LiteLLMProvider()  # Uses OMAGENT_MODEL

async for event in provider.stream(messages, tools, system):
    # Yields TextDeltaEvent, ToolCallEvent, ErrorEvent, DoneEvent
```

**Features:**
- Streaming with `stream=True`
- Token usage tracking via `stream_options={"include_usage": True}`
- Tool call accumulation from delta chunks
- Builds properly formatted assistant messages with `tool_calls` array

### Workspace (`core/workspace.py`)

Per-session file management at `~/.omagent/workspaces/{session_id}/`:

```
{session_id}/
  artifacts/    # Charts, CSVs, reports, models
  notebooks/    # Auto-generated Jupyter notebooks
  logs/         # events.jsonl + run.log
  code/         # Generated code snippets
```

The workspace path is injected into the system prompt so the LLM knows where to save files:

```
Save all generated files to: ~/.omagent/workspaces/abc123/artifacts/
```

Tools that support workspaces get the workspace injected automatically.

### Event Journal (`core/journal.py`)

Dual-format logging for full observability:

1. **events.jsonl** -- structured, machine-readable
2. **run.log** -- human-readable narrative

Event types logged:
- `session_start`, `session_end`
- `user_message`
- `llm_request`, `llm_response` (with token counts and latency)
- `tool_call`, `tool_result` (with duration)
- `plan_created`
- `memory_summary`
- `error`

Use `omagent replay last` to visualize a session's event journal as a rich timeline.

### Memory (`core/memory.py`)

Two systems:

1. **ConversationSummarizer** -- compresses old messages when the conversation gets long
   - Uses Claude Haiku for fast, cheap summarization
   - Keeps last N messages verbatim, summarizes the rest
   - Injects summary as a system message on session resume

2. **MemoryStore** -- persistent key-value facts per session
   - SQLite-backed
   - LLM uses the `remember` tool to store facts
   - Facts are injected into the system prompt on resume

### Planner (`core/planner.py`)

Detects and tracks multi-step plans from LLM responses:

- Plans are parsed from `<plan>` XML tags in early LLM responses
- Each step has a status: `pending` -> `in_progress` -> `completed` / `failed`
- Steps are automatically advanced when tool calls complete
- Plans are stored in SQLite via `PlanStore`
- The TUI sidebar shows plan progress in real-time

### Activity Tracker (`core/tracker.py`)

Temporal event logging for analytics:

- Logs LLM calls, tool executions, milestones
- SQLite-backed with timestamp indices
- Generates daily activity reports
- Timeline queries for session replay

### Orchestrator (`core/orchestrator.py`)

Multi-agent coordination:

- Main agent can spawn sub-agents via the `delegate` tool
- Each sub-agent gets its own session, pack, and tool set
- Sub-agents run with auto-approve permissions (supervised by parent)
- Results flow back as `SubAgentDoneEvent`

## Data Flow

### Interactive Session

```
User types message
    |
    v
TUI InputArea --> OmagentApp.handle_submit()
    |
    v
AgentLoop.run(message) --> async generator
    |
    +-- Summarizer: compress if needed
    |
    +-- Provider.stream() --> LLM API
    |       |
    |       +-- TextDeltaEvent --> TUI ChatView (streaming text)
    |       +-- ToolCallEvent --> collected
    |
    +-- For each tool call:
    |       |
    |       +-- PermissionPolicy.check()
    |       |       |
    |       |       +-- auto: execute immediately
    |       |       +-- prompt: PermissionPromptEvent --> user decides
    |       |       +-- deny: PermissionDeniedEvent
    |       |
    |       +-- ToolRegistry.execute(name, input)
    |       +-- ToolResultEvent --> TUI ToolCard
    |       +-- Result --> Session history
    |       +-- Journal.log_tool_result()
    |       +-- Tracker.log_tool_call()
    |
    +-- No more tool calls --> DoneEvent
    |
    v
Session saved to SQLite
```

### Server SSE Flow

```
POST /stream { message, session_id, pack }
    |
    v
loop_factory(pack, session_id) --> AgentLoop
    |
    v
AgentLoop.run(message) --> async generator
    |
    v
event_generator():
    for event in loop.run():
        yield f"event: {type}\ndata: {json}\n\n"
    |
    v
StreamingResponse(media_type="text/event-stream")
```

## Extension Points

### Creating a New Tool

1. Create `omagent/packs/{pack}/tools/my_tool.py`
2. Subclass `Tool` with name, description, input_schema, execute
3. Add the dotted path to `pack.yaml` under `tools:`

### Creating a New Pack

1. Create `omagent/packs/{name}/pack.yaml`
2. Define system_prompt, tools, permissions
3. Optionally add `tools/` and `skills/` directories

### Creating a New Skill

1. Create `{pack}/skills/{name}/SKILL.md`
2. Add YAML frontmatter with `name`, `description`
3. Write instructions in Markdown body

### Adding a New Event Type

1. Add dataclass to `core/events.py`
2. Add to `AgentEvent` union type
3. Add `to_dict()` for serialization
4. Handle in TUI (`app.py`) and server (`routes.py`)

## Shared Persistence Layer

All persistent state flows through a single SQLite database at `~/.omagent/sessions.db`:

```
~/.omagent/sessions.db
  |
  +-- sessions        Session objects + message history (SessionStore)
  +-- memories         Key-value facts per session (MemoryStore)
  +-- plans            Agent plans per session (PlanStore)
  +-- activity         Tracker events, timeline, daily reports (ActivityTracker)
```

All stores share the same database path, configurable via `OMAGENT_DB_PATH`. The workspace filesystem (`~/.omagent/workspaces/`) is separate and stores binary artifacts, notebooks, and event journals (JSONL).

## Dependencies

| Package | Purpose |
|---------|---------|
| `litellm` | Multi-provider LLM API |
| `click` | CLI framework |
| `textual` | Terminal UI |
| `rich` | Terminal formatting |
| `fastapi` | API server |
| `uvicorn` | ASGI server |
| `pydantic-settings` | Configuration |
| `aiosqlite` | Async SQLite |
| `skills-ref` | Agent Skills spec parser |
| `pyyaml` | YAML parsing |
| `pandas` | Data manipulation (data_science pack) |
| `matplotlib` | Visualization (data_science pack) |
