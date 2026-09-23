---
name: build-intelligence
description: Install or repair the intelligence system in any project. Handles three cases — empty project, partial/existing implementation, or a different context system. Manual-only.
disable-model-invocation: true
---

## Step 0 — Detect which case you are in

Before doing anything, check what exists:

```
A. EMPTY — no context/, no .ai/, no .claude/hooks/, no knowledge.db
B. PARTIAL — some of the above exist but are incomplete or missing entries
C. DIFFERENT SYSTEM — a context system exists but uses different conventions (e.g. just a CONTEXT.md file, a different DB, or a plain notes folder)
```

How to detect:
- `context/` exists AND has at least 5 .md files AND `.ai/knowledge.db` exists → likely B or already complete
- `context/` or equivalent exists but NO `.ai/knowledge.db` → C (different system)
- Neither exists → A

Announce which case you detected and what you will do before touching anything.

---

## Case A — Empty project (fresh install)

1. **Scaffold context docs** — create all of the following as empty skeletons with section headers only (do not fill content yet):
   `context/overview.md`, `context/architecture.md`, `context/dependencies.md`,
   `context/decisions.md`, `context/constraints.md`, `context/known-problems.md`,
   `context/failed-solutions.md`, `context/current-task.md`, `context/verification.md`,
   `context/handoff.md`, `context/realignment.md`, `context/gitContext.md`,
   `context/revert-state.md`, `context/savings-log.md`, `context/session-snapshot.md`

2. **Scaffold .ai/ scripts** — copy or create:
   - `.ai/rebuild_db.py` — full DB builder (use the version from the intelligence plugin)
   - `.ai/sync_context.py` — incremental sync script
   - `.ai/system-config.json` — `{"project": "<name>", "installed": "<date>"}`

3. **Wire hooks** — copy hook scripts from the plugin into `.claude/hooks/`:
   `session_start.py`, `safe_point_guard.py`, `context_sync.py`,
   `check_handoff.py`, `precompact_snapshot.py`, `task_complete_stats.py`

4. **Wire settings.json** — create or update `.claude/settings.json` with the full hook block (SessionStart, Stop, PreToolUse/Edit|Write, PostToolUse/Edit|Write, PreCompact) and permissions (allow context/tasks/.claude edits silently; deny Read on overview.html).

5. **Update .gitignore** — ensure `.claude/settings.local.json`, `.claude/**/*.local.*`, `.claude/.last_edit_hash`, `.claude/.last_verified`, `.claude/.current_task_id` are ignored.

6. **Ensure CLAUDE.md / AGENTS.md** — if neither exists, create `AGENTS.md` with the standard skeleton (project description placeholder, Persistent Knowledge System section, Enforcement Rules, Git Workflow, Progress Updates, Hard Constraints). Create `CLAUDE.md` as a single line: `@AGENTS.md`.

7. **Run `python .ai/rebuild_db.py`** — initialises knowledge.db.

8. **Spawn explorer subagents** — now that scaffolding is done, spawn one `explorer` subagent per major area to survey the codebase and fill in the context docs:
   - Overview + architecture
   - Dependencies + decisions
   - Constraints + known-problems
   After each returns, write its findings into the relevant `context/*.md` files.

9. **Run `python .ai/sync_context.py`** — syncs filled docs to DB.

10. **Confirm** — tell the user the system is live. List what was created.

---

## Case B — Partial implementation (gaps only)

1. **Audit what exists** — for each of the 15 context docs, each of the 2 .ai/ scripts, each of the 6 hook scripts, check whether it exists and whether it has real content (not just skeleton headers). Build a gap list.

2. **Audit settings.json** — check that all 5 hook events are wired (SessionStart, Stop, PreToolUse, PostToolUse, PreCompact). Note any missing.

3. **Audit .gitignore** — check the 5 ignore entries are present.

4. **Report the gaps** — show the user a list of what's missing or incomplete before changing anything.

5. **Fill gaps only** — create missing files, add missing hook wiring, fill missing .gitignore entries. Do NOT overwrite files that already have content.

6. **Run `python .ai/rebuild_db.py`** if any context doc was added or significantly changed; otherwise run `python .ai/sync_context.py`.

7. **Confirm** — tell the user what was added.

---

## Case C — Different context system (migration)

1. **Read what exists** — read the existing context files (whatever they are: a single CONTEXT.md, a notes/ folder, a different DB schema). Understand their structure.

2. **Map to the standard schema** — identify which content maps to which of the 15 standard context docs. Tell the user the mapping before doing anything.

3. **Confirm with user** — show the proposed mapping and ask for a go-ahead. Do NOT migrate without explicit approval.

4. **On approval: migrate** — for each mapping, extract the relevant content and write it into the appropriate `context/*.md` file. Preserve the original files (do not delete them — user can clean up later).

5. **Then follow Case A steps 2–10** — scaffold anything still missing, wire hooks, run rebuild.

6. **Flag what couldn't be mapped** — if any content in the original system has no obvious home in the standard schema, surface it to the user.

---

## All cases — final check

After completing the relevant case above:
- Run `python .ai/rebuild_db.py` if not already done.
- Confirm `.claude/settings.json` has all 5 hook events.
- Confirm `AGENTS.md` (or `CLAUDE.md`) contains the Enforcement Rules section.
- Tell the user to restart their Claude Code session so the SessionStart hook fires fresh.
