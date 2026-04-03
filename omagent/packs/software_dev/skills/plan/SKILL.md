---
name: plan
description: Break requirements into executable tasks with dependencies and acceptance criteria
allowed-tools: project_state read_file write_file list_dir
metadata:
  pack: software_dev
  version: "1.0"
  user-invocable: "true"
---

## Plan Phase — Task Breakdown

You are entering the **Plan** phase. Your goal is to transform requirements from CONTEXT.md into an executable task breakdown.

### Step 1: Read Context

Use `project_state` with `operation: read, file: CONTEXT.md` to load all requirements, decisions, and constraints from the discuss phase.

### Step 2: Analyze Scope

Before creating tasks:
- Count the requirements and acceptance criteria
- Identify shared dependencies (e.g., data models used by multiple features)
- Determine the implementation order (what must exist before what)

### Step 3: Create Task Breakdown

For each task, define:

```markdown
### Task N: [Title]
- **Description**: What to implement
- **Files**: Files to create or modify
- **Depends on**: Task numbers this depends on (or "none")
- **Acceptance criteria**: How to verify this task is complete
- **Estimated complexity**: simple | moderate | complex
- **Status**: pending
```

### Task Ordering Rules

1. Data models and schemas come first
2. Core logic before UI or API layers
3. Tests alongside implementation (not after)
4. Configuration and integration last
5. No task should take more than ~30 minutes of work

### Step 4: Self-Review Checklist

Before finalizing, verify:
- [ ] Every requirement from CONTEXT.md is covered by at least one task
- [ ] Every task has testable acceptance criteria
- [ ] Dependencies form a DAG (no circular dependencies)
- [ ] No task is too large (split if > 30 min estimated)
- [ ] File paths are specific and accurate
- [ ] The first task can start immediately (no unresolved dependencies)

### Step 5: Write Plan

Use `project_state` with `operation: write, file: PLAN.md` to save the complete plan.

Format:

```markdown
# Project Plan

## Goal
[One sentence from CONTEXT.md]

## Tasks

### Task 1: [Title]
...

### Task 2: [Title]
...

## Dependency Graph
Task 1 → Task 3
Task 2 → Task 3
Task 3 → Task 4

## Totals
- Simple: N tasks
- Moderate: N tasks
- Complex: N tasks
- Total: N tasks
```

### Step 6: Update State

Update `.planning/STATE.md`:
- Phase: plan (completed)
- Tasks total: N
- Ready for execution: yes

### Step 7: Present to User

Show the plan summary and ask for confirmation before moving to `/execute`.
