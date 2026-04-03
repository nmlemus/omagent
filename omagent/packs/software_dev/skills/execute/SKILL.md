---
name: execute
description: Implement tasks from the plan one at a time with progress tracking
allowed-tools: project_state read_file write_file list_dir bash
metadata:
  pack: software_dev
  version: "1.0"
  user-invocable: "true"
---

## Execute Phase — Implementation

You are entering the **Execute** phase. Your goal is to implement tasks from PLAN.md one at a time, updating progress as you go.

### Step 1: Load State

1. Use `project_state` with `operation: read, file: PLAN.md` to get the task list
2. Use `project_state` with `operation: read, file: STATE.md` to check current progress
3. Use `project_state` with `operation: read, file: CONTEXT.md` to review architecture decisions

### Step 2: Find Next Task

Identify the first task with status `pending` whose dependencies are all `completed`.

If no task is available:
- Check for blocked tasks (dependencies not met)
- Report the blocker to the user
- Suggest reordering if possible

### Step 3: Implement the Task

For each task:

1. **Announce**: "Starting Task N: [title]"
2. **Review**: Re-read the task's acceptance criteria and files list
3. **Implement**: Write the code, following decisions from CONTEXT.md
4. **Test**: If the task includes tests, write and run them
5. **Verify**: Check each acceptance criterion for this task

### Implementation Rules

- Follow existing code patterns in the project
- Use consistent naming conventions
- Write meaningful error messages
- Add comments only where the logic is non-obvious
- If a task reveals a gap in the plan, note it but complete the task as specified

### Step 4: Update Progress

After completing each task, update PLAN.md:
- Change the task's status from `pending` to `completed`
- Note any deviations or issues discovered

Update STATE.md:
- Increment tasks completed count
- Update last modified timestamp
- Note any blockers for the next task

### Step 5: Report

After each task:

```
## Task N: [title] — COMPLETED
- Files created/modified: [list]
- Tests: [pass/fail/none]
- Notes: [any issues or deviations]
- Next: Task M: [title]
```

### Step 6: Completion

When all tasks are complete:
- Update STATE.md phase to "execute (completed)"
- Summarize what was built
- Recommend running `/verify` to validate the work
