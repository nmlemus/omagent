# Getting Started

This guide walks you through installing omagent, running your first session, and exploring its key features.

## Prerequisites

- Python 3.11 or later
- An API key from Anthropic, OpenAI, or another LLM provider supported by [LiteLLM](https://docs.litellm.ai)

## Installation

### From Source

```bash
git clone https://github.com/nmlemus/omagent.git
cd omagent
pip install -e ".[dev]"
```

### Environment Setup

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required: at least one LLM API key
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional: use a different model
# OMAGENT_MODEL=openai/gpt-4o

# Optional: default domain pack
# OMAGENT_PACK=data_science
```

### Verify Installation

```bash
omagent config
```

This shows your active configuration, confirming the CLI is installed correctly.

## Your First Session

### Interactive TUI

Start a chat session with the default pack:

```bash
omagent chat
```

You'll see the omagent TUI with:
- A splash screen showing recent sessions
- A message input area at the bottom
- A status bar with token and cost tracking

Type a message and press Enter:

```
> List all Python files in the current directory and summarize what each one does
```

The agent will:
1. Call the `list_dir` tool to see the directory
2. Call `read_file` on each Python file
3. Stream a summary as it reads

### One-Shot Mode

For scripting or quick tasks:

```bash
omagent run "what is the current git branch and last 3 commits"
```

### Classic REPL

If you prefer a simple terminal without the TUI:

```bash
omagent chat --classic
```

## Working with Domain Packs

### Data Science Pack

Start a data science session:

```bash
omagent chat --pack data_science
```

You'll get Meridian, a senior data scientist persona with access to:
- **Jupyter kernel** -- persistent Python execution
- **Dataset profiling** -- analyze CSV/Excel files
- **SQL queries** -- DuckDB analytics
- **Model training** -- ML with cross-validation

Example prompts:

```
> Profile the dataset at /path/to/sales.csv
> Show me the distribution of revenue by region
> Train a random forest model to predict churn
```

### Flutter Dev Pack

Start a Flutter development session:

```bash
omagent chat --pack flutter_dev
```

You'll get Velo, a Flutter engineer with access to:
- **Flutter CLI** -- build, run, test
- **Dart analyzer** -- linting and type checks
- **Pubspec manager** -- dependency management

Example prompts:

```
> Create a new Flutter widget for a responsive login form
> Add firebase_auth to the project dependencies
> Analyze the lib/ directory for lint issues
```

## TUI Features

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+N` | Start a new session |
| `Ctrl+T` | Toggle the sidebar |
| `Ctrl+E` | Toggle the activity log |
| `Ctrl+Q` | Quit |
| `ESC` | Focus the input area |

### Slash Commands

Type these in the input area:

| Command | Action |
|---------|--------|
| `/skills` | List all available skills |
| `/skills list` | Detailed skill listing |
| `/help` | Show help information |
| `/{skill_name}` | Invoke a skill directly (e.g., `/eda`) |

### Sidebar

Toggle with `Ctrl+T`. Shows:
- Session ID and pack name
- Current plan with step progress
- Available tools
- System prompt preview

### Activity Log

Toggle with `Ctrl+E`. Shows real-time events:
- LLM requests and responses
- Tool calls with timing
- Errors and warnings

## Skills

Skills are on-demand instruction sets that the agent loads when needed. They follow the [Agent Skills](https://agentskills.io) specification.

### How Skills Work

1. Available skills are listed in the system prompt as an XML summary
2. When the agent needs skill instructions, it calls the `Skill` tool
3. Full instructions are loaded into the conversation (not the system prompt)
4. This keeps the context window manageable

### Using Skills

You can invoke skills directly:

```
> /eda
```

Or the agent discovers and uses them automatically based on your request:

```
> I need to clean this messy dataset with lots of missing values
```

The agent sees the `cleaning` skill in its available skills and calls `Skill({ skill: "cleaning" })` to load the data cleaning workflow.

### Available Skills

**Data Science Pack:**
- `data-analysis` -- DuckDB-based CSV/Excel analysis
- `cleaning` -- Data quality and imputation
- `eda` -- Exploratory data analysis
- `modeling` -- ML model training
- `chart-visualization` -- Reference for 20+ chart types
- `consulting-analysis` -- High-level analysis patterns

**Flutter Pack:**
- `firebase-setup` -- Firebase + FlutterFire configuration
- `responsive-ui` -- Adaptive UI patterns
- `state-management` -- Riverpod/Bloc/Provider patterns

## Sessions and Workspaces

### Sessions

Every conversation is stored as a session with full message history:

```bash
# List recent sessions
omagent session list

# Export a session
omagent session export abc123def --format markdown -o session.md
omagent session export abc123def --format json -o session.json
```

### Workspaces

Each session gets a dedicated workspace at `~/.omagent/workspaces/{session_id}/`:

```
{session_id}/
  artifacts/    # Charts, CSVs, reports
  notebooks/    # Auto-generated Jupyter notebooks
  logs/         # Event journal (events.jsonl + run.log)
  code/         # Generated code
```

Browse workspaces:

```bash
# List all workspaces
omagent workspace list

# Show workspace contents
omagent workspace open abc123
```

### Session Replay

Visualize what the agent did in a past session:

```bash
# Replay the most recent session
omagent replay last

# Replay a specific session
omagent replay abc123def
```

This shows a rich timeline of events: LLM calls, tool executions, plans created, and errors.

## Activity Reports

Track what the agent has been doing:

```bash
# Today's activity
omagent activity today

# Yesterday's activity
omagent activity yesterday

# Specific date
omagent activity 2026-04-01
```

Reports show LLM call counts, tool usage, session summaries, and cost estimates.

## Server Mode

Start the API server for web UI integration:

```bash
omagent serve --port 8000
```

### Quick Test

```bash
# Health check
curl http://localhost:8000/health

# Send a message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, what can you do?"}'

# Stream a response (SSE)
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "List files in the current directory"}'
```

### WebSocket

Connect via WebSocket for real-time streaming:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/chat");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case "text_delta":
      process.stdout.write(data.content);
      break;
    case "tool_call":
      console.log(`Tool: ${data.tool_call.name}`);
      break;
    case "done":
      console.log("\n--- Done ---");
      break;
  }
};

ws.onopen = () => {
  ws.send(JSON.stringify({
    message: "What time is it?",
    pack: "default"
  }));
};
```

## Next Steps

- [CLI Reference](cli-reference.md) -- complete command documentation
- [Domain Packs](domain-packs.md) -- create your own packs
- [Tools Guide](tools.md) -- build custom tools
- [Skills Guide](skills.md) -- create skills
- [Architecture](architecture.md) -- understand the internals
