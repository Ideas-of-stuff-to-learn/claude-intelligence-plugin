---
name: handoff
description: Full end-of-session ritual — update revert-state, current-task, handoff, backlog, sync SQLite, savings log, commit and push. Run before ending any session where code or context changed.
disable-model-invocation: true
---

You are running the `/handoff` skill. Run these steps **in this exact order**. Do not skip or reorder.

## Step 1 — revert-state.md

Find the row with `in-progress` status added today. Update its status to `complete`.
If there is no in-progress row, note that no safe-point was recorded this session (this is a warning, not a blocker).

## Step 2 — current-task.md

- Move the active task description to a "Recently Completed" section
- Clear the Active Task section
- Note any open work or follow-up tasks in a "Next Steps" section

## Step 3 — handoff.md

Prepend a new block at the top of the file:

```markdown
## What Was Just Done — YYYY-MM-DD

**Commit:** `<hash>`
**Files changed:** <list each file with one-line description of change>
**Open work:** <anything not completed>
**Notes:** <anything the next session needs to know>

---
```

Keep all existing blocks below. Do not delete anything.

## Step 4 — tasks/backlog.md

- Mark any completed tasks with `[x]` or strikethrough
- Add a progress log row with today's date, status, and a brief note

## Step 5 — Sync SQLite

Run: `python .ai/sync_context.py`

## Step 6 — savings-log.md

Append one line:
```
YYYY-MM-DD | task: <what was done> | SQLite queries: <N> | context docs loaded: <N> | full repo scan avoided: yes/no | notes
```

Estimate SQLite queries and context docs loaded during this session.

## Step 7 — Commit and push

Stage all modified context and backlog files. Do not stage source code that is not yet ready to ship.

```
git add context/ tasks/
git commit -m "chore: session handoff YYYY-MM-DD — <brief description>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push origin main
```

Report: "Handoff complete — session state saved and pushed."
