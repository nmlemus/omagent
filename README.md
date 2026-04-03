# omagent -- Oh My Agent

A generic, domain-configurable agentic engine that turns any LLM into a specialized AI assistant with tools, skills, and full observability.

```
User message --> LLM --> Tool calls --> Execute --> Results --> LLM --> ... --> Response
```

## Features

- **Interactive TUI** -- rich terminal UI with live streaming, tool cards, plan tracking, and session management
- **One-shot mode** -- `omagent run "your prompt"` for scripting and pipelines
- **Server mode** -- FastAPI + WebSocket + SSE for web UI integration
- **Domain packs** -- swap persona, tools, and skills via YAML config
- **Skill system** -- on-demand skill loading following the [Agent Skills](https://agentskills.io) spec
- **Full observability** -- JSONL event journal, activity tracking, session replay
- **Memory system** -- conversation summarization and persistent key-value memory
- **MCP support** -- connect external tools via [Model Context Protocol](https://modelcontextprotocol.io)
- **Multi-provider** -- any LLM supported by [LiteLLM](https://docs.litellm.ai) (Anthropic, OpenAI, Google, etc.)

## Quick Start

### 1. Install

```bash
git clone https://github.com/nmlemus/omagent.git
cd omagent
pip install -e ".[dev]"
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your API key:

```env
ANTHROPIC_API_KEY=sk-ant-...
# or
OPENAI_API_KEY=sk-...
```

### 3. Run

```bash
# Interactive TUI (default)
omagent chat

# Classic REPL (no TUI)
omagent chat --classic

# One-shot execution
omagent run "list all Python files in the current directory"

# With a specific domain pack
omagent chat --pack data_science

# Start the API server
omagent serve
```

## Domain Packs

Packs transform omagent into a specialized assistant. Each pack provides a persona, tools, skills, and permission policies.

| Pack | Persona | Tools | Use Case |
|------|---------|-------|----------|
| `default` | Atlas -- general assistant | read, write, list, bash | File ops, shell commands, general tasks |
| `data_science` | Meridian -- senior data scientist | jupyter, dataset_profile, sql_query, model_train | Data analysis, ML, visualization |
| `flutter_dev` | Velo -- Flutter engineer | flutter_cli, dart_analyze, pubspec_manager | Mobile app development |

Switch packs with:

```bash
omagent chat --pack data_science
omagent chat --pack flutter_dev
```

Or set the default:

```bash
export OMAGENT_PACK=data_science
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `omagent chat` | Interactive TUI session |
| `omagent chat --classic` | Classic REPL mode |
| `omagent run "prompt"` | One-shot execution |
| `omagent serve` | Start FastAPI server |
| `omagent config` | Show active configuration |
| `omagent activity [today]` | Daily activity report |
| `omagent replay [session_id\|last]` | Replay a session timeline |
| `omagent session list` | List recent sessions |
| `omagent session export ID` | Export session (JSON/Markdown) |
| `omagent workspace list` | List session workspaces |
| `omagent workspace open ID` | Browse workspace contents |

## TUI Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+N` | New session |
| `Ctrl+T` | Toggle sidebar |
| `Ctrl+E` | Toggle activity log |
| `Ctrl+Q` | Quit |
| `ESC` | Focus input |

## Configuration

All settings can be set via environment variables (prefix `OMAGENT_`) or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OMAGENT_MODEL` | `anthropic/claude-sonnet-4-6` | LLM model (LiteLLM format) |
| `OMAGENT_PACK` | `default` | Default domain pack |
| `OMAGENT_HOST` | `0.0.0.0` | Server bind host |
| `OMAGENT_PORT` | `8000` | Server bind port |
| `OMAGENT_MAX_ITERATIONS` | `20` | Max tool loop iterations |
| `OMAGENT_DEFAULT_PERMISSION` | `prompt` | Default tool permission |
| `OMAGENT_API_KEY` | (none) | Server auth token |
| `OMAGENT_LOG_LEVEL` | `INFO` | Logging verbosity |

## API Server

Start the server and integrate with any frontend:

```bash
omagent serve --port 8000
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send message, get complete response |
| `POST` | `/stream` | Send message, stream SSE events |
| `WS` | `/ws/chat` | WebSocket for real-time streaming |
| `GET` | `/sessions` | List sessions |
| `GET` | `/packs` | List available packs |
| `GET` | `/tools` | List available tools |
| `GET` | `/health` | Health check |

See [docs/api-reference.md](docs/api-reference.md) for complete API documentation.

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [Architecture](docs/architecture.md) | Developers | System design, data flow, component relationships |
| [Getting Started](docs/getting-started.md) | Users | Installation, first steps, tutorials |
| [CLI Reference](docs/cli-reference.md) | Users | Complete command reference |
| [API Reference](docs/api-reference.md) | Developers | REST/WebSocket API docs |
| [Domain Packs](docs/domain-packs.md) | Developers | Creating custom packs |
| [Tools Guide](docs/tools.md) | Developers | Building custom tools |
| [Skills Guide](docs/skills.md) | Developers | Creating and using skills |
| [Configuration](docs/configuration.md) | Users/Devs | All config options |

## Project Structure

```
omagent/
  cli/            # CLI + TUI (Click, Textual)
  core/           # Engine (loop, session, events, registry, permissions)
  tools/          # Tool system (base class + builtins)
  packs/          # Domain packs (YAML config + pack-specific tools/skills)
  providers/      # LLM providers (LiteLLM)
  server/         # FastAPI server (REST, SSE, WebSocket)
  mcp/            # Model Context Protocol client
tests/            # Test suite (pytest)
docs/             # Documentation
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check omagent/

# Run specific test
pytest tests/test_loop.py -v
```

## License

MIT
