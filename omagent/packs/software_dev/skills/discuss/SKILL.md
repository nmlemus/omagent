---
name: discuss
description: Requirements elicitation — ask targeted questions to clarify what needs to be built
allowed-tools: project_state read_file list_dir
metadata:
  pack: software_dev
  version: "1.0"
  user-invocable: "true"
---

## Discuss Phase — Requirements Elicitation

You are entering the **Discuss** phase. Your goal is to turn a vague idea into clear, testable requirements before any code is written.

### Step 1: Initialize State

Use `project_state` with `operation: init, phase: discuss` to create the `.planning/` directory if it doesn't exist.

### Step 2: Understand the Request

Ask the user targeted questions to clarify:
- **What** are we building? (specific features, not vague descriptions)
- **Why** does it need to exist? (problem being solved)
- **Who** will use it? (users, systems, APIs)
- **What are the boundaries?** (what is NOT in scope)
- **How do we know it's done?** (acceptance criteria)

Ask ONE question at a time. Wait for the answer before asking the next.

### Step 3: Check for Brownfield Context

If the project has existing code:
- Use `list_dir` and `read_file` to understand the codebase
- Ask how the new work fits with existing architecture
- Identify what can be reused vs. what needs to change

### Step 4: Capture Decisions

After each significant answer, update `.planning/CONTEXT.md` with:
- The requirement or decision
- The rationale (why this choice)
- Any constraints identified

Use `project_state` with `operation: write, file: CONTEXT.md` to save.

### Step 5: Define Acceptance Criteria

Before ending the discussion, ensure every requirement has at least one testable acceptance criterion:
- "Given X, when Y, then Z"
- Measurable and verifiable
- No ambiguous terms ("fast", "good", "easy")

### Step 6: Summarize and Confirm

Present a structured summary to the user:

```
## Requirements Summary
1. [Requirement 1] — AC: [criterion]
2. [Requirement 2] — AC: [criterion]

## Constraints
- [constraint 1]

## Non-Goals
- [explicitly excluded]
```

Ask the user to confirm before moving to `/plan`.

### Step 7: Update State

Update `.planning/STATE.md` to reflect:
- Phase: discuss (completed)
- Requirements count
- Ready for planning: yes/no
