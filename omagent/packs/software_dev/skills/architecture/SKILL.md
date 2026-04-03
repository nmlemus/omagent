---
name: architecture
description: System design decisions — tech stack, components, interfaces, and ADRs
allowed-tools: project_state read_file write_file list_dir bash
metadata:
  pack: software_dev
  version: "1.0"
  user-invocable: "true"
---

## Architecture Phase — System Design

Use this skill when a project needs architectural decisions before detailed planning. This sits between `/discuss` and `/plan` for complex projects.

### When to Use

- New project with multiple components
- Significant technology choices to make
- Integration with external systems
- Performance or scalability requirements
- Team needs alignment on structure before coding

### Step 1: Load Requirements

Use `project_state` with `operation: read, file: CONTEXT.md` to understand what needs to be built.

### Step 2: Analyze the Problem

Before proposing solutions:
- Identify the key components (what are the nouns?)
- Identify the interactions (what are the verbs?)
- List the quality attributes that matter (performance, security, maintainability)
- Check for existing code patterns if brownfield

### Step 3: Tech Stack Decision

For each technology choice, document:

```markdown
## ADR-N: [Decision Title]

### Status
Accepted

### Context
[Why this decision is needed]

### Options Considered
1. [Option A] — pros: ..., cons: ...
2. [Option B] — pros: ..., cons: ...

### Decision
[Which option and why]

### Consequences
- [What this enables]
- [What trade-offs we accept]
```

### Step 4: Component Diagram

Create an ASCII component diagram:

```
+-------------------+     +------------------+
|   Component A     |---->|   Component B    |
|   (responsibility)|     |   (responsibility)|
+-------------------+     +------------------+
         |                         |
         v                         v
+-------------------+     +------------------+
|   Component C     |     |   Data Store     |
+-------------------+     +------------------+
```

### Step 5: Key Interfaces

Define the interfaces between components:
- Function signatures or API endpoints
- Data models and schemas
- Error handling patterns
- Configuration requirements

### Step 6: Save Architecture

Append architecture decisions to CONTEXT.md using `project_state` with `operation: write`:

```markdown
## Architecture Decisions

### Components
[component list with responsibilities]

### Tech Stack
[chosen technologies with rationale]

### ADRs
[architecture decision records]

### Diagram
[ASCII component diagram]

### Key Interfaces
[interface definitions]
```

### Step 7: Update State

Update STATE.md to note architecture phase is complete. The project is ready for `/plan`.
