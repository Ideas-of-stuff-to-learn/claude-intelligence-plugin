---
name: safe-point
description: Record a revert anchor before touching code — runs git rev-parse HEAD and appends a row to context/revert-state.md.
---

You are running the `/safe-point` skill.

## Step 1 — Get current commit hash

Run: `git rev-parse HEAD`

Capture the full 40-character hash.

## Step 2 — Get task description

If the user provided a task description in the invocation, use it. Otherwise use the active task from `context/current-task.md` (read the Active Task line only).

## Step 3 — Append to revert-state.md

Read `context/revert-state.md` and append one row to the table:

```
| YYYY-MM-DD | task: <description> | <hash> | in-progress |
```

Use today's date. Do not modify any existing rows.

## Step 4 — Sync SQLite

Run: `python .ai/sync_context.py`

## Step 5 — Confirm

Report: "Safe-point recorded: `<first 8 chars of hash>` — safe to proceed."
