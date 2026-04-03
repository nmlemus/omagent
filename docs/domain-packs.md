# Domain Packs

Domain packs transform omagent into a specialized assistant by providing a persona, tools, skills, and permission policies. This guide covers using built-in packs and creating your own.

## How Packs Work

A pack is a directory containing a `pack.yaml` configuration file and optional `tools/` and `skills/` subdirectories:

```
my_pack/
  pack.yaml          # Required: persona, tools, permissions
  tools/             # Optional: pack-specific tool implementations
    my_tool.py
  skills/            # Optional: SKILL.md instruction files
    my-skill/
      SKILL.md
```

When you start omagent with `--pack my_pack`, the engine:
1. Finds the pack directory across search paths
2. Loads `pack.yaml` and applies the system prompt
3. Imports and registers all declared tools
4. Discovers skills from the `skills/` directory
5. Applies permission overrides

## Pack Search Paths

omagent searches for packs in this order (first match wins):

1. `omagent/packs/` -- built-in packs (ships with omagent)
2. `./packs/` -- project-local packs (in your current directory)
3. `~/.omagent/packs/` -- user-global packs

## Built-in Packs

### default (Atlas)

General-purpose assistant for file operations and shell commands.

```bash
omagent chat  # uses default pack
```

**Tools:** read_file, write_file, list_dir, bash
**Permissions:** auto for reads, prompt for writes and bash

### data_science (Meridian)

Senior data scientist with a structured methodology.

```bash
omagent chat --pack data_science
```

**Tools:** jupyter_execute, dataset_profile, sql_query, model_train, jupyter_reset
**Skills:** data-analysis, cleaning, eda, modeling, chart-visualization, consulting-analysis
**Permissions:** auto for analysis tools, prompt for modifications

### flutter_dev (Velo)

Senior Flutter engineer with architecture-first approach.

```bash
omagent chat --pack flutter_dev
```

**Tools:** flutter_cli, dart_analyze, pubspec_manager
**Skills:** firebase-setup, responsive-ui, state-management
**Permissions:** prompt for CLI and pubspec (high-impact), auto for analysis

## Creating a Custom Pack

### Step 1: Create the Directory

```bash
mkdir -p ~/.omagent/packs/my_pack/tools
mkdir -p ~/.omagent/packs/my_pack/skills
```

### Step 2: Write pack.yaml

```yaml
name: my_pack
version: "1.0"
description: My custom domain pack

system_prompt: |
  You are a specialized assistant for [your domain].

  ## Core Capabilities
  - Capability 1
  - Capability 2

  ## Workflow
  1. Understand the request
  2. Use available tools
  3. Present results clearly

  ## Important
  - When the user provides a plan using <plan> tags, track and execute each step.
  - Save all generated artifacts to the workspace directory.

tools:
  # Built-in tools are always available (read_file, write_file, list_dir, bash)
  # Add your custom tools here:
  - omagent.packs.my_pack.tools.my_tool:MyTool

permissions:
  # Override default permissions for specific tools
  my_tool: auto        # Execute without asking
  write_file: prompt   # Ask before writing
  bash: prompt          # Ask before running commands

# Optional: MCP server connections
mcp_servers:
  - command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem"]
    env:
      ALLOWED_DIRS: "/path/to/allowed"
```

### Step 3: Create Custom Tools (Optional)

Create `tools/my_tool.py`:

```python
from omagent.tools.base import Tool
from typing import Any


class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Does something specific to my domain"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The query to process"
                },
                "format": {
                    "type": "string",
                    "enum": ["json", "text", "csv"],
                    "description": "Output format"
                }
            },
            "required": ["query"]
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        query = input["query"]
        fmt = input.get("format", "text")

        try:
            result = do_something(query, fmt)
            return {"output": result}
        except Exception as e:
            return {"error": str(e)}
```

Make sure the module path in `pack.yaml` matches:

```yaml
tools:
  - omagent.packs.my_pack.tools.my_tool:MyTool
```

### Step 4: Add Skills (Optional)

Create `skills/my-skill/SKILL.md`:

```markdown
---
name: my-skill
description: Step-by-step workflow for a specific task
allowed-tools: my_tool read_file write_file
metadata:
  pack: my_pack
  user-invocable: "true"
---

## My Skill Workflow

### Step 1: Analyze
- Use `my_tool` to gather information
- Check the input format

### Step 2: Process
- Apply transformations
- Validate results

### Step 3: Output
- Save results to workspace
- Present summary to user
```

### Step 5: Test Your Pack

```bash
# Verify it loads
omagent chat --pack my_pack

# Check config
omagent config
```

## pack.yaml Reference

```yaml
# Required
name: string              # Pack identifier (matches directory name)

# Optional
version: string           # Semantic version (default: "0.1.0")
description: string       # Human-readable description

system_prompt: string     # System prompt for the LLM
                          # This defines the agent's persona and behavior

tools: list[string]       # Tool class paths in "module:ClassName" format
                          # e.g., "omagent.packs.my_pack.tools.foo:FooTool"

permissions:              # Per-tool permission overrides
  tool_name: auto|prompt|deny

mcp_servers:              # MCP server connections
  - command: string       # Command to run
    args: list[string]    # Command arguments
    env:                  # Environment variables
      KEY: value
```

## System Prompt Tips

The system prompt defines how the agent behaves. Some patterns that work well:

1. **Give the agent a name and role** -- "You are Meridian, a senior data scientist"
2. **Define a methodology** -- step-by-step workflow the agent should follow
3. **Set boundaries** -- what the agent should and shouldn't do
4. **Include plan support** -- "When the user provides a plan using `<plan>` tags, track each step"
5. **Reference the workspace** -- omagent automatically appends workspace save paths

## MCP Integration

Packs can connect to [MCP servers](https://modelcontextprotocol.io) to access external tools:

```yaml
mcp_servers:
  - command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem"]
    env:
      ALLOWED_DIRS: "/home/user/data"

  - command: python
    args: ["-m", "my_mcp_server"]
```

MCP tools are automatically discovered and registered in the tool registry alongside native tools.
