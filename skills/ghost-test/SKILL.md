---
name: ghost-test
description: Structured dry-run before any code change — enumerate every affected file, call site, sentinel, constraint, and side effect, then give a PROCEED or REVISE verdict.
---

You are running the `/ghost-test` skill. Do NOT edit any file during this skill. This is analysis only.

For the planned change described by the user (or inferred from context), produce a structured report:

## 1. Files to be modified

List every source file that will change. For each: what changes and why.

## 2. Call sites and consumers

For every function, symbol, or interface being changed: list every file that calls or imports it. Confirm each consumer is compatible with the change or will also be updated.

## 3. Sentinel sync check

Are any sentinel constants involved (e.g. `NEEDS_MANUAL_REVIEW`, `NOT_YET_CATEGORISED`)? These are defined in multiple files and must stay in sync. If yes, list all files that define or import the sentinel and confirm all will be updated.

## 4. Constraint check

Query:
```sql
SELECT title, description FROM constraints WHERE severity = 'hard';
```

For each hard constraint: does the planned change violate it? State explicitly YES or NO for each.

## 5. Side effects

List any:
- Database schema changes (new columns, tables, migrations needed)
- New environment variables required
- Config file changes
- Files that must be updated in lock-step (e.g. duplicate color palettes, duplicate sentinel files)

## 6. Verdict

**PROCEED** — if all checks pass and no inconsistencies found.

**REVISE** — if any check fails. State exactly what must be corrected before proceeding. Re-run `/ghost-test` after corrections.

Do not touch any file until the verdict is PROCEED.
