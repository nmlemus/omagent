---
name: verify
description: Goal-backward verification of implemented work against acceptance criteria
allowed-tools: project_state read_file list_dir bash
metadata:
  pack: software_dev
  version: "1.0"
  user-invocable: "true"
---

## Verify Phase — Goal-Backward Verification

You are entering the **Verify** phase. Your goal is to check every acceptance criterion from the plan and produce an honest assessment.

### Step 1: Load Artifacts

1. Use `project_state` with `operation: read, file: PLAN.md` — get all tasks and acceptance criteria
2. Use `project_state` with `operation: read, file: CONTEXT.md` — get original requirements
3. Use `project_state` with `operation: read, file: STATE.md` — confirm execution is complete

### Step 2: Run Tests

If tests exist:
- Use `bash` to run the test suite
- Capture pass/fail output
- Note any failures with details

### Step 3: Verify Each Criterion

For every acceptance criterion in PLAN.md:

1. **Read the criterion** — what should be true?
2. **Check the evidence** — read the relevant files, run the relevant command
3. **Verdict** — PASS, FAIL, or PARTIAL with explanation

Format per criterion:

```
### Criterion: [description]
- **Evidence**: [what you checked — file path, command output, etc.]
- **Result**: PASS | FAIL | PARTIAL
- **Notes**: [details if not PASS]
```

### Step 4: Check Requirements Coverage

For each requirement from CONTEXT.md:
- Is there at least one task that addresses it?
- Is there at least one passing criterion for it?
- Note any requirements with no test coverage

### Step 5: Write Review

Use `project_state` with `operation: write, file: REVIEW.md`:

```markdown
# Verification Review

## Date
[current date]

## Overall Result
PASS | FAIL | PARTIAL ([N/M] criteria passing)

## Criteria Results

### Criterion 1: [description]
- Evidence: [what was checked]
- Result: PASS
...

## Test Results
[test output summary]

## Requirements Coverage
- [N/M] requirements fully verified
- Gaps: [list any uncovered requirements]

## Issues Found
1. [issue description and severity]

## Recommendations
- [any fixes or improvements needed]

## Summary
[honest one-paragraph assessment]
```

### Step 6: Update State

Update STATE.md:
- Phase: verify (completed)
- Overall result: PASS/FAIL/PARTIAL
- If FAIL: list the specific failures so they can be addressed

### Verification Principles

- Be honest. A false PASS is worse than a real FAIL.
- Check evidence, not assumptions. Read the actual file, run the actual command.
- Partial credit is fine. Report what works and what doesn't.
- If a criterion is ambiguous, note the ambiguity rather than guessing.
