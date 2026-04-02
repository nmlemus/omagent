# omagent — Oh My Agent

Generic domain-configurable agentic engine with:
- **Interactive REPL** — multi-turn CLI with history and streaming
- **One-shot mode** — `omagent run "your prompt"`
- **Server mode** — FastAPI + WebSocket for UI integration
- **Domain packs** — swap persona + tools via YAML config

## Quickstart

```bash
pip install -e ".[dev]"
cp .env.example .env
# edit .env with your API key

# Interactive mode
omagent chat

# One-shot
omagent run "analyze this CSV file at data.csv"

# Server mode
omagent serve
```

## Domain Packs

The engine ships with a `data_science` pack. Swap packs with:
```bash
omagent chat --pack marketing
```
