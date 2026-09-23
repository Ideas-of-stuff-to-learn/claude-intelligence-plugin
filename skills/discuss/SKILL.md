---
name: discuss
description: Enter plan/discussion mode for a proposed change. Propose approach, surface trade-offs, iterate with the user until explicit agreement — no code written until the user says go.
disable-model-invocation: true
---

**Trigger:** User says "discuss X", "plan X", or you hit a decision point that needs alignment before coding.

Steps — in this exact order:

1. **Understand the goal** — state in one sentence what the user wants to achieve and what constraints apply (from `context/constraints.md` and current task).

2. **Propose an approach** — lay out the concrete plan: which files change, what the data flow looks like, any migrations or config needed. Be specific enough that the user can spot wrong assumptions.

3. **Surface trade-offs** — name the one or two real risks or alternative approaches. Don't list everything; pick what matters.

4. **Switch to plan mode** — enter plan mode so the user can review and redirect before anything is written.

5. **Iterate** — respond to feedback in plan mode. Update the proposal. Repeat until the user says "go", "yes", "do it", or equivalent explicit approval.

6. **On approval** — exit plan mode, then proceed with execution (which will follow `/execute` or `/execute-careful` behaviour depending on what the user asks for, or default to asking before any irreversible action).

**Do NOT write any code, edit any file, or run any command before explicit approval.**
