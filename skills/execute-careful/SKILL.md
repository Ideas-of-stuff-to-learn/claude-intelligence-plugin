---
name: execute-careful
description: Execute with zero auto-permissions — pause and ask the user before every file edit, shell command, and context update. Use when the task is high-risk, touches production config, or the user wants full visibility.
disable-model-invocation: true
---

**Trigger:** User says "execute carefully", "execute-careful", "ask me everything", or explicitly invokes `/execute-careful`.

**Permission level:** Ask before EVERY action, including:
- Each individual file edit or write (state the file, what will change, and why)
- Every shell command (state the command and its effect before running)
- Context doc updates
- Git staging and commits
- Any directory creation or file deletion

**How to ask:** One clear sentence describing the action and its effect. Wait for "yes", "go", "ok", or equivalent before proceeding. If the user says "stop" or "no", abandon that step and ask what to do instead.

**Batching:** You may propose a group of related low-risk actions together ("I'll edit these 3 files to add the route — ok?") but still wait for approval before touching any of them. Never group an irreversible action with reversible ones.

**Execution behaviour:**
- Give rolling status updates after each approved chunk (see Enforcement Rules in AGENTS.md)
- Run `/task-done` when the full task is complete — ask first
- Run `/verifier` if source code was changed — ask first
- Emit the task-complete stats block on completion

**Use this mode for:** production config changes, DB migrations, anything touching auth or billing, or when the user is learning a new area of the codebase and wants to understand each step.
