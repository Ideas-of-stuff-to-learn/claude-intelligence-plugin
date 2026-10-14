# Claude Intelligence Plugin — Lovable Project Knowledge Template

Copy this file's contents into your Lovable project's knowledge base via the Lovable editor
(Project Settings > Project Knowledge), or set it using the MCP `set_project_knowledge` tool.

---

## Engineering Intelligence System

This project uses the Claude Intelligence Plugin for persistent context across sessions.

### Context Documents

The following context documents must be kept up to date. Read them at the start of every session:

- `context/overview.md` — project purpose and tech stack
- `context/architecture.md` — component structure
- `context/constraints.md` — hard rules (never violate these)
- `context/handoff.md` — what happened last session
- `context/current-task.md` — active task and queue
- `context/known-problems.md` — known bugs and fragile areas
- `context/decisions.md` — why things are built the way they are

### Before Editing Code

1. Check `context/constraints.md` — are you about to violate any hard rule?
2. Check `context/known-problems.md` — are you touching a fragile area?
3. Check `context/current-task.md` — is this change in scope?

### After Editing Code

1. Update `context/current-task.md` with your progress.
2. If you discovered a new problem, add it to `context/known-problems.md`.
3. If you made an architectural decision, add it to `context/decisions.md`.

### Session End

Before ending, update `context/handoff.md` with:
- What you completed
- What files changed
- What is next
- Any risks or blockers

### Lovable-Specific Notes

- Lovable rebuilds the preview automatically after each agent response — you do not need to trigger it manually.
- Use Supabase for all persistent state — do not use localStorage for data that must survive page reloads.
- All auth goes through Supabase Auth — do not implement custom auth.
- Tailwind CSS + shadcn/ui is the styling system — do not introduce other UI libraries.
- TypeScript strict mode is enabled — all types must be explicit.
