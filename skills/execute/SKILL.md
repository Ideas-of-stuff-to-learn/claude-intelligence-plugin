---
name: execute
description: Execute an agreed plan with full auto-permissions. Proceeds through file edits, shell commands, and context updates without stopping to ask — except for pushes and irreversible destructive actions.
disable-model-invocation: true
---

**Trigger:** User says "execute", "go", "do it", or explicitly invokes `/execute` after a `/discuss` session or after describing a task.

**Permission level:** Auto-approve all of the following without asking:
- File edits and writes (source code, context docs, config)
- Creating directories and new files
- Running read-only shell commands (git status, git log, python scripts, builds)
- Running `python .ai/sync_context.py` and `python .ai/rebuild_db.py`
- Staging files with `git add`
- Creating commits

**Still require explicit user confirmation:**
- Any `git push` (requires "ship" from user)
- Dropping or truncating database tables
- Deleting files not created in this session
- Any command that modifies system settings outside the project directory
- Any action flagged as irreversible by context/constraints.md

**Execution behaviour:**
- Give rolling status updates after each chunk (see Enforcement Rules in AGENTS.md)
- Run `/task-done` when the full task is complete
- Run `/verifier` if source code was changed before declaring done
- Stop and surface blockers immediately rather than skipping around them

**On completion:** emit the task-complete stats block (files changed, % impact, one-line opinion) via `python .ai/hooks/task_complete_stats.py` or inline if the script is unavailable.
