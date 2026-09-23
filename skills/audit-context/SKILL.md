---
name: audit-context
description: Check context/*.md for drift against the source code — spawns the context-auditor subagent, presents findings, applies agreed fixes, and re-stamps staleness markers.
---

You are running the `/audit-context` skill.

## Step 1 — Spawn context-auditor

Delegate to the `context-auditor` subagent with this task:

> Compare every claim in `context/*.md` against the current source code and `git log` output.
> For each document, note the staleness marker (`<!-- last-verified: <hash> YYYY-MM-DD -->`) at the top.
> Check `git log <hash>..HEAD -- <relevant files>` to see what changed since that marker.
> Report: outdated statements, missing information, and wrong statements.
> Include the source evidence for each finding (file + line or commit hash).
> Do NOT edit any file.

## Step 2 — Present findings

Show the subagent's drift report to the user. Group by document. For each finding:
- Document name
- Claim that is outdated/wrong/missing
- Evidence (current source or git log)

## Step 3 — Apply agreed fixes

For each finding the user agrees to fix:
- Edit the relevant `context/*.md` file
- Make only the specific correction; do not rewrite sections unnecessarily

## Step 4 — Re-stamp staleness markers

For each document that was updated, add or update the staleness marker at the very top of the file:

```markdown
<!-- last-verified: <current git HEAD hash> YYYY-MM-DD -->
```

Run `git rev-parse HEAD` to get the current hash.

## Step 5 — Sync SQLite

Run: `python .ai/sync_context.py`

Report: "Context audit complete — <N> documents updated."
