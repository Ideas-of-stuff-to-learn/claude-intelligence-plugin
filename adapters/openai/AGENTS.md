# Claude Intelligence Plugin — OpenAI / Codex Adapter

This file is the entry point for OpenAI-based agents (ChatGPT, Codex, Assistants API).
Place or reference this file as your agent's system instructions.

## How to Load Context

At the start of every session, read these files in order:

1. `context/overview.md` — what this project is
2. `context/handoff.md` — what happened last session (first block only)
3. `context/current-task.md` — what is active right now
4. `context/constraints.md` — what you must never do

If `context/session-snapshot.md` exists and starts with `# Session Snapshot`, read it and treat it as your starting state.

## Equivalent Skill Commands

This adapter maps plugin skills to plain instructions. Use these patterns:

| Plugin skill | OpenAI equivalent |
|-------------|------------------|
| `/safe-point` | "Record a safe point: read `context/revert-state.md`, append a new row with today's date and status=in-progress. Note the current git ref." |
| `/handoff` | "Update `context/handoff.md` with a new entry at the top: what was done, files changed, and what is next." |
| `/verify` | "Run the test suite, check for errors, and if all passes write the current working-tree fingerprint to `.claude/.last_verified`." |
| `/catch-up` | "Read all 15 context docs and the last three git commits. Summarise current state." |
| `/execute` | "Plan first, then implement step by step, updating `context/current-task.md` as you go." |
| `/review-change` | "Diff the staged and unstaged changes. Check against constraints. Produce a structured review report." |

## Working Tree State

Because OpenAI agents do not have lifecycle hooks, you must simulate them manually:

- **Before editing source code:** check `context/revert-state.md` for a row with today's date and status=in-progress. If none, record one first.
- **After editing source code:** update `context/handoff.md`.
- **Before ending a session:** run verification and update `context/handoff.md`.

## Context Update Protocol

Whenever you change source code, you must also:
1. Update `context/current-task.md` to reflect progress.
2. Note any new constraints or decisions in `context/constraints.md` / `context/decisions.md`.
3. Record any new problems in `context/known-problems.md`.

## Limitations vs Claude Code

- No automatic session hooks — you must run the above manually.
- No SQLite knowledge base — search context docs with grep or read them directly.
- No `/build-intelligence` automation — maintain context docs by hand.
