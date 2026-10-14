# Claude Intelligence Plugin — Gemini CLI Adapter

This file configures the Gemini CLI agent (`gemini` command) to use the intelligence system.
Reference this file in your `GEMINI.md` at project root, or copy its contents there.

## Session Initialisation

At the start of every Gemini CLI session, the agent should:

1. Read `context/overview.md` and `context/handoff.md` (first entry only).
2. Read `context/current-task.md` for the active task.
3. Read `context/constraints.md` for hard rules.
4. Check whether `context/session-snapshot.md` starts with `# Session Snapshot` — if so, read it for recovery context.

## Tool Usage Guidance

### Before any `edit` or `write` operation:
Check `context/revert-state.md` for a row matching today's date with status=in-progress.
If none exists, record one first:
```
Append to context/revert-state.md:
| YYYY-MM-DD | in-progress | <git-short-sha> | <brief task description> |
```

### After any `edit` or `write` operation:
Record that edits happened — note the changed files in your working memory.

### Before ending a session:
1. Update `context/handoff.md` with a new entry.
2. Run the test suite and confirm passing.
3. Update `context/current-task.md` with progress.

## Skill Equivalents

| Plugin skill | Gemini CLI equivalent |
|-------------|----------------------|
| `/safe-point` | Record a row in `context/revert-state.md` as above |
| `/handoff` | Prepend a new entry to `context/handoff.md` |
| `/verify` | Run `python -m pytest` (or equivalent) and report |
| `/catch-up` | Read all context docs and last 5 commits |
| `/execute` | Follow the execute-careful protocol: plan, verify constraints, implement, test |
| `/debug-systematically` | Form hypotheses first; test cheapest hypothesis first |

## Gemini-Specific Notes

- Use `google_search` for external lookups when documentation is needed.
- Prefer reading existing context docs over web searches for project-internal questions.
- When working with large files, read them in sections rather than all at once.

## Context Quality

After making changes, if you notice a context doc is outdated, update it immediately.
The context/ directory is the source of truth for the next session.
