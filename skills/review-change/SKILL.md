# /review-change

Review a set of file changes for correctness, side-effects, and alignment with project constraints before they are committed.

## When to use

- Before committing or merging any non-trivial change.
- When another agent or human asks you to review a diff.
- After `/execute` or `/execute-careful` to verify the result before handing off.

## Steps

1. **Identify the diff.** Run `git diff` (unstaged) and `git diff --cached` (staged) to see all pending changes. If reviewing a specific file, read it directly.

2. **Read the constraints.** Read `context/constraints.md` to know what must not change.

3. **Check each changed file for:**
   - Correctness: does the change do what it claims?
   - Regressions: does it touch anything that other code depends on?
   - Constraint violations: does it break any hard rules?
   - Missing tests: are there new code paths without test coverage?
   - Documentation gaps: should `context/` be updated?

4. **Check for common mistakes:**
   - TODO/FIXME left in production code
   - Debug statements or temporary logging
   - Hardcoded values that should be config
   - Missing error handling
   - Inconsistent naming with the rest of the codebase

5. **Produce a review report:**

```
## Change Review — YYYY-MM-DD

### Files Changed
[List]

### Issues Found
| Severity | File | Line | Issue |
|----------|------|------|-------|
| high     |      |      |       |
| medium   |      |      |       |
| low      |      |      |       |

### Constraint Violations
[Any hard rules broken]

### Missing Tests
[Uncovered new code paths]

### Verdict
[ ] Approve — safe to commit
[ ] Approve with minor fixes — list them
[ ] Block — must fix before committing
```

## Rules

- Be specific: cite file and line for every finding.
- Distinguish between blocking issues and suggestions.
- If the change is clearly correct and low-risk, say so — reviews are not just for finding problems.
