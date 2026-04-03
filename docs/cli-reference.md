# CLI Reference

Complete reference for all `omagent` commands.

## Global Options

omagent uses Click for CLI parsing. Environment variables can substitute for most options (prefix `OMAGENT_`).

## Commands

### `omagent chat`

Start an interactive multi-turn chat session.

```bash
omagent chat [OPTIONS]
```

| Option | Type | Default | Env Var | Description |
|--------|------|---------|---------|-------------|
| `--pack` | string | `default` | `OMAGENT_PACK` | Domain pack name |
| `--session` | string | (new) | -- | Resume a session by ID |
| `--classic` | flag | false | -- | Use classic REPL instead of TUI |

**Examples:**

```bash
# Default TUI
omagent chat

# Data science pack
omagent chat --pack data_science

# Resume a previous session
omagent chat --session abc123def456

# Classic REPL (no TUI)
omagent chat --classic
```

**TUI mode** launches a Textual-based terminal UI with:
- Streaming message display with tool cards
- Sidebar with session info and plan tracking (Ctrl+T)
- Activity log viewer (Ctrl+E)
- Status bar with token/cost metrics

**Classic mode** launches a prompt_toolkit REPL with:
- Command history (arrow keys)
- Basic streaming output
- Type `exit` or `quit` to end

---

### `omagent run`

Run a single prompt and print the response.

```bash
omagent run PROMPT [OPTIONS]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `PROMPT` | Yes | The prompt to send to the agent |

| Option | Type | Default | Env Var | Description |
|--------|------|---------|---------|-------------|
| `--pack` | string | `default` | `OMAGENT_PACK` | Domain pack name |

**Examples:**

```bash
# Simple prompt
omagent run "what is 2+2"

# With a specific pack
omagent run "profile the dataset at data.csv" --pack data_science

# Pipe output
omagent run "generate a Python hello world script" > hello.py
```

---

### `omagent serve`

Start the FastAPI server for API/WebSocket access.

```bash
omagent serve [OPTIONS]
```

| Option | Type | Default | Env Var | Description |
|--------|------|---------|---------|-------------|
| `--host` | string | `0.0.0.0` | `OMAGENT_HOST` | Bind host |
| `--port` | int | `8000` | `OMAGENT_PORT` | Bind port |
| `--pack` | string | `default` | `OMAGENT_PACK` | Default domain pack |

**Examples:**

```bash
# Default settings
omagent serve

# Custom port with data science pack
omagent serve --port 3000 --pack data_science

# Bind to localhost only
omagent serve --host 127.0.0.1
```

---

### `omagent config`

Show the active configuration as a table.

```bash
omagent config
```

Displays all settings with their current values. API keys are masked.

---

### `omagent activity`

Show a daily activity report.

```bash
omagent activity [WHEN]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `WHEN` | `today` | Date to report: `today`, `yesterday`, or `YYYY-MM-DD` |

**Examples:**

```bash
omagent activity
omagent activity yesterday
omagent activity 2026-04-01
```

---

### `omagent replay`

Replay a session as a rich timeline visualization.

```bash
omagent replay [SESSION_ID]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `SESSION_ID` | `last` | Full or partial session ID, or `last` for most recent |

Shows a chronological timeline of events: LLM calls, tool executions, plan steps, and errors with timing information.

**Examples:**

```bash
# Most recent session
omagent replay last

# Specific session (partial ID works)
omagent replay abc123
```

---

### `omagent session list`

List recent sessions.

```bash
omagent session list
```

Shows a table with session ID (truncated), pack name, and last update time.

---

### `omagent session export`

Export a session to JSON or Markdown.

```bash
omagent session export SESSION_ID [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format` | choice | `json` | Output format: `json` or `markdown` |
| `-o, --output` | path | (stdout) | Output file path |

**Examples:**

```bash
# Export as JSON to stdout
omagent session export abc123def

# Export as Markdown to file
omagent session export abc123def --format markdown -o session.md
```

---

### `omagent workspace list`

List all session workspaces.

```bash
omagent workspace list
```

Shows a table with session ID, artifact count, notebook presence, and disk size.

---

### `omagent workspace open`

Show the contents of a session workspace as a tree.

```bash
omagent workspace open SESSION_ID
```

| Argument | Required | Description |
|----------|----------|-------------|
| `SESSION_ID` | Yes | Full or partial session ID |

**Example output:**

```
abc123def456...
  artifacts/
    chart.png (45231 bytes)
    cleaned_data.csv (12048 bytes)
  notebooks/
    session.ipynb (8901 bytes)
  logs/
    events.jsonl (23456 bytes)
    run.log (5678 bytes)
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments (Click) |
