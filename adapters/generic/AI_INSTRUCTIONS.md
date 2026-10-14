# AI Agent Instructions — Intelligence System Entry Point

This file is the generic entry point for any AI agent working in this repository.
Copy it to your project root as `AI_INSTRUCTIONS.md`, or reference it from your agent's system prompt.

## What This Is

This project uses the Claude Intelligence Plugin: a portable engineering intelligence system that
provides persistent context, specialist agents, and verified task workflows across AI sessions.

## Starting Every Session

Read in this order (do not skip):

1. **`context/overview.md`** — understand what you are working on
2. **`context/handoff.md`** — first entry only: what was done last session
3. **`context/current-task.md`** — what is active and what is queued
4. **`context/constraints.md`** — what you must never do

If `context/session-snapshot.md` exists and begins with `# Session Snapshot`:
read it — it contains your recovery state from a mid-session interrupt.

## Before Editing Source Code

- Verify `context/revert-state.md` has a row for today with `status=in-progress`.
  If not, add one: `| YYYY-MM-DD | in-progress | <git-sha> | <task description> |`
- Verify the change does not violate anything in `context/constraints.md`.
- Verify you know which task this change belongs to.

## While Working

- Keep `context/current-task.md` updated as you complete sub-steps.
- If you discover a problem, note it in `context/known-problems.md`.
- If you make an architectural decision, note it in `context/decisions.md`.

## Ending Every Session

1. Run the test suite. Fix failures before stopping.
2. Update `context/handoff.md` with a new entry at the top.
3. Update `context/current-task.md` to reflect completed steps and what is next.

## Context Document Index

| Document | Purpose | Update when |
|----------|---------|------------|
| overview.md | Project purpose and tech stack | Project changes fundamentally |
| architecture.md | How components fit together | Structure changes |
| dependencies.md | External libraries and services | Dependencies added/removed |
| decisions.md | Why things are built this way | Architectural decision made |
| constraints.md | Hard rules | New constraint discovered |
| known-problems.md | Known bugs and fragile areas | Problem found or fixed |
| handoff.md | Inter-session continuity | Every session end |
| current-task.md | Active work | Multiple times per session |
| revert-state.md | Safe-point registry | Before editing source code |
| test-strategy.md | How testing works | Test approach changes |
| api-contracts.md | External interfaces | API changes |
| environment.md | Config and secrets | Env vars change |
| deployment.md | How to ship | Deploy process changes |
| security.md | Threat model and controls | Security posture changes |
| session-snapshot.md | Pre-compact state | Written by hooks automatically |

## Specialist Agents

When you need deep expertise, delegate to one of:

- **explorer** — discover the codebase structure
- **librarian** — retrieve specific knowledge from the database
- **context-auditor** — find stale or missing context docs
- **verifier** — run the verification suite
- **architecture-analyst** — analyse structural design
- **test-architect** — design and implement test coverage
- **regression-hunter** — diagnose and fix regressions
- **security-auditor** — audit for vulnerabilities
- **integration-auditor** — verify external integrations
- **context-curator** — keep context/ accurate and complete
