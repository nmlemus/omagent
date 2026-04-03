# Configuration

omagent uses [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) for configuration. All settings can be set via environment variables, `.env` file, or code.

## Environment Variables

All variables use the `OMAGENT_` prefix:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OMAGENT_MODEL` | string | `anthropic/claude-sonnet-4-6` | LLM model in LiteLLM format |
| `OMAGENT_PACK` | string | `default` | Default domain pack |
| `OMAGENT_HOST` | string | `0.0.0.0` | Server bind host |
| `OMAGENT_PORT` | int | `8000` | Server bind port |
| `OMAGENT_API_KEY` | string | (none) | Server auth token (disabled if unset) |
| `OMAGENT_DB_PATH` | path | `~/.omagent/sessions.db` | Session database path |
| `OMAGENT_MAX_ITERATIONS` | int | `20` | Max tool loop iterations per turn |
| `OMAGENT_DEFAULT_PERMISSION` | string | `prompt` | Default tool permission level |
| `OMAGENT_LOG_LEVEL` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `OMAGENT_LOG_FORMAT` | string | `text` | Log format: `text` or `json` |

## LLM API Keys

Set the API key for your LLM provider:

| Provider | Variable |
|----------|----------|
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Google | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| Azure OpenAI | `AZURE_API_KEY` + `AZURE_API_BASE` |
| AWS Bedrock | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |

See [LiteLLM docs](https://docs.litellm.ai/docs/providers) for all supported providers.

## .env File

Create a `.env` file in your project root:

```env
# LLM Provider
ANTHROPIC_API_KEY=sk-ant-api03-...

# Model selection (LiteLLM format)
OMAGENT_MODEL=anthropic/claude-sonnet-4-6

# Default pack
OMAGENT_PACK=data_science

# Server settings
OMAGENT_HOST=0.0.0.0
OMAGENT_PORT=8000
OMAGENT_API_KEY=my-secret-token

# Agent behavior
OMAGENT_MAX_ITERATIONS=20
OMAGENT_DEFAULT_PERMISSION=prompt

# Logging
OMAGENT_LOG_LEVEL=INFO
```

omagent loads `.env` from the current directory at startup.

## Model Selection

The model is specified in [LiteLLM format](https://docs.litellm.ai/docs/providers): `provider/model-name`.

### Examples

```env
# Anthropic
OMAGENT_MODEL=anthropic/claude-sonnet-4-6
OMAGENT_MODEL=anthropic/claude-opus-4-6
OMAGENT_MODEL=anthropic/claude-haiku-4-5-20251001

# OpenAI
OMAGENT_MODEL=openai/gpt-4o
OMAGENT_MODEL=openai/gpt-4o-mini

# Google
OMAGENT_MODEL=gemini/gemini-2.0-flash

# Azure
OMAGENT_MODEL=azure/my-deployment-name

# AWS Bedrock
OMAGENT_MODEL=bedrock/anthropic.claude-3-sonnet-20240229-v1:0
```

## Permission Levels

The `OMAGENT_DEFAULT_PERMISSION` setting controls the default behavior when a tool doesn't have a specific permission set:

| Level | Behavior |
|-------|----------|
| `auto` | Execute tools immediately without asking |
| `prompt` | Ask for user approval before executing |
| `deny` | Block all tool execution by default |

Pack-specific permissions override the default. For example, with `OMAGENT_DEFAULT_PERMISSION=prompt`:

```yaml
# pack.yaml
permissions:
  read_file: auto    # Override: don't ask for reads
  list_dir: auto     # Override: don't ask for listings
  bash: prompt       # Keep default: ask for shell commands
```

## Storage Paths

| Path | Purpose |
|------|---------|
| `~/.omagent/sessions.db` | SQLite database for sessions, activity, memory |
| `~/.omagent/workspaces/{session_id}/` | Per-session workspace (artifacts, logs, notebooks) |
| `~/.omagent/packs/` | User-global custom packs |
| `~/.omagent/skills/` | User-global skills |

## Viewing Configuration

Check your active configuration:

```bash
omagent config
```

This shows all settings with their resolved values (API keys are masked).

## Programmatic Access

```python
from omagent.core.config import get_config

config = get_config()
print(config.model)       # "anthropic/claude-sonnet-4-6"
print(config.max_iterations)  # 20
print(config.db_path)     # PosixPath("~/.omagent/sessions.db")
```

The `get_config()` function is cached -- it returns the same instance on repeated calls.
