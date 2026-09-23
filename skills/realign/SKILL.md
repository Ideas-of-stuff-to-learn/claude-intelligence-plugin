---
name: realign
description: Reconstruct working memory at session start or after confusion — queries SQLite, reads handoff + current-task, outputs a 5-10 line summary of what is active and what not to break.
---

You are running the `/realign` skill. Execute in order.

## Step 1 — Query realignment record

```sql
SELECT * FROM realignment WHERE id = 1;
```

This gives you the pointers to the foundational context docs.

## Step 2 — Read handoff (newest block only)

Read `context/handoff.md`. Extract only the first `## What Was Just Done` block (stop at the second `---` separator). Do not read the entire file.

## Step 3 — Read current task (active section only)

Read `context/current-task.md`. Extract the Active Task and Status sections only.

## Step 4 — Targeted SQLite query

If the user's message or the active task mentions a specific area (auth, categorization, charts, etc.), query:
```sql
SELECT title, description FROM constraints WHERE severity = 'hard';
SELECT path, description FROM files WHERE tags LIKE '%<area>%' LIMIT 10;
```

## Step 5 — Output working-memory summary

Write a 5–10 line summary covering:
- **Active task:** what is in progress
- **Last change:** what was done most recently (from handoff)
- **Key constraints:** what must not be broken for this area
- **Open questions:** anything flagged as unresolved
- **Next step:** what to do first in this session

Keep it tight — this is a working-memory anchor, not a report.
