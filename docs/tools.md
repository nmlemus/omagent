# Tools Guide

Tools are how the agent interacts with the world. This guide covers using built-in tools and creating custom ones.

## How Tools Work

1. The LLM receives tool schemas (name, description, input_schema) in every request
2. When the LLM wants to take an action, it generates a `tool_use` response with a tool name and input
3. The AgentLoop checks permissions, executes the tool, and returns the result
4. The LLM sees the result and decides what to do next

## Built-in Tools

These are available in every pack:

### read_file

Read the contents of a file.

```json
{
  "name": "read_file",
  "input": { "path": "/path/to/file.py" }
}
```

**Returns:** `{ "output": "file contents..." }`
**Permission:** `auto`

### write_file

Create or overwrite a file.

```json
{
  "name": "write_file",
  "input": {
    "path": "/path/to/file.py",
    "content": "print('hello')"
  }
}
```

**Returns:** `{ "output": "Written to /path/to/file.py" }`
**Permission:** `prompt`

### list_dir

List the contents of a directory.

```json
{
  "name": "list_dir",
  "input": { "path": "/path/to/directory" }
}
```

**Returns:** `{ "output": "file1.py\nfile2.py\nsubdir/" }`
**Permission:** `auto`

### bash

Execute a shell command with a 30-second timeout.

```json
{
  "name": "bash",
  "input": { "command": "git status" }
}
```

**Returns:** `{ "output": "On branch main\n..." }` or `{ "error": "command failed", "output": "stderr..." }`
**Permission:** `prompt`

### Skill

Load skill instructions on-demand. See [Skills Guide](skills.md).

```json
{
  "name": "Skill",
  "input": { "skill": "eda", "args": "focus on correlations" }
}
```

**Returns:** `{ "skill": "eda", "path": "...", "description": "...", "prompt": "full SKILL.md content" }`
**Permission:** `auto`

### remember

Store a persistent fact in the session memory.

```json
{
  "name": "remember",
  "input": {
    "key": "data_source",
    "value": "PostgreSQL database at db.example.com"
  }
}
```

**Returns:** `{ "output": "Remembered: data_source" }`
**Permission:** `auto`

### summarize

Compress the conversation history to free context window space.

```json
{
  "name": "summarize",
  "input": { "max_messages": 10 }
}
```

**Returns:** `{ "output": "Summarized 45 messages into context" }`
**Permission:** `auto`

### delegate

Spawn a sub-agent with a different pack to handle a subtask.

```json
{
  "name": "delegate",
  "input": {
    "pack": "data_science",
    "task": "Profile the dataset at /tmp/data.csv",
    "context": "We need to understand the data quality"
  }
}
```

**Returns:** `{ "output": "Sub-agent result..." }`
**Permission:** `prompt`

## Creating a Custom Tool

### Step 1: Implement the Tool Class

Create a Python file with a class that extends `Tool`:

```python
# omagent/packs/my_pack/tools/weather.py
from omagent.tools.base import Tool
from typing import Any
import httpx


class WeatherTool(Tool):
    """Get current weather for a location."""

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "Get the current weather for a city. Returns temperature, conditions, and humidity."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name (e.g., 'San Francisco')"
                },
                "units": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature units",
                    "default": "celsius"
                }
            },
            "required": ["city"]
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        city = input["city"]
        units = input.get("units", "celsius")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.weather.example.com/current",
                    params={"city": city, "units": units}
                )
                response.raise_for_status()
                data = response.json()

            return {
                "output": (
                    f"Weather in {city}: {data['temp']}°"
                    f"{'C' if units == 'celsius' else 'F'}, "
                    f"{data['conditions']}, "
                    f"Humidity: {data['humidity']}%"
                )
            }
        except httpx.HTTPError as e:
            return {"error": f"Failed to get weather: {e}"}
```

### Step 2: Register in pack.yaml

```yaml
tools:
  - omagent.packs.my_pack.tools.weather:WeatherTool
```

### Step 3: Set Permissions

```yaml
permissions:
  get_weather: auto  # Safe to auto-execute (read-only API call)
```

## Tool Design Guidelines

### Naming

- Use `snake_case` for tool names
- Be descriptive: `dataset_profile` not `profile`
- Use verb_noun pattern: `read_file`, `train_model`

### Description

Write descriptions for the LLM, not for humans:

```python
# Good: tells the LLM when and how to use it
"Profile a CSV or Excel file. Returns column types, null counts, "
"unique values, and basic statistics. Use this before analysis."

# Bad: too vague
"Analyze data"
```

### Input Schema

- Use JSON Schema with clear descriptions
- Mark required fields
- Provide enums for constrained choices
- Set sensible defaults

```python
{
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "Absolute path to the CSV or Excel file"
        },
        "max_rows": {
            "type": "integer",
            "description": "Maximum rows to sample for profiling",
            "default": 10000
        }
    },
    "required": ["path"]
}
```

### Return Values

Always return a dict:

```python
# Success
return {"output": "result text or data"}

# Error
return {"error": "what went wrong"}

# Rich output (tool result is shown to the LLM as JSON)
return {
    "output": "Profile complete",
    "columns": 12,
    "rows": 50000,
    "null_percentage": 3.2
}
```

### Workspace Integration

If your tool generates files, support workspace injection:

```python
class MyTool(Tool):
    def __init__(self):
        self._workspace = None  # Injected by AgentLoop

    async def execute(self, input: dict) -> dict:
        if self._workspace:
            output_path = self._workspace.artifacts_dir / "output.csv"
        else:
            output_path = Path("/tmp/output.csv")

        # Save to workspace
        save_result(output_path)
        return {"output": f"Saved to {output_path}"}
```

The AgentLoop automatically injects the workspace into tools that have a `_workspace` attribute.

## Tool Registry

The `ToolRegistry` manages all tools:

```python
from omagent.core.registry import ToolRegistry

registry = ToolRegistry()

# Register tools
registry.register(MyTool())
registry.register_many([Tool1(), Tool2()])

# Query
registry.names()                    # ["my_tool", "tool1", "tool2"]
registry.get("my_tool")             # MyTool instance
registry.get_schemas()              # List of tool schemas for LLM

# Execute
result = await registry.execute("my_tool", {"param": "value"})
```

## Permission Model

Each tool has a permission level that controls whether user approval is needed:

| Level | Behavior | Use For |
|-------|----------|---------|
| `auto` | Execute immediately | Read-only operations, safe queries |
| `prompt` | Ask user before executing | File writes, shell commands, API mutations |
| `deny` | Block execution | Dangerous or disallowed operations |

Permissions are resolved in priority order:
1. Pack-level override (from `pack.yaml`)
2. Tool default
3. System default (`OMAGENT_DEFAULT_PERMISSION`)
