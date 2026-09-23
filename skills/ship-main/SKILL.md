---
name: ship-main
description: Manual-only skill. Runs /task-done, then commits and pushes to main. Only invoke when user explicitly says "ship" or "ship to main".
disable-model-invocation: true
---

**Trigger:** User explicitly says "ship" or "ship to main". Never run this automatically.

Exact order:

1. **Run /task-done** — complete the mini-handoff first (safe-point, context updates, DB sync).

2. **Stage and review** — `git status`, then `git add` only the relevant files (never `git add -A` blindly). Review the diff. If any secrets or unintended files are staged, stop and tell the user.

3. **Commit** — write a conventional commit message summarising what was done. End with:
   ```
   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   ```

4. **Rebase** — `git pull --rebase origin main` (stash with `-u` first if there are unstaged changes).

5. **Push** — `git push origin main`

6. **Confirm** — report the commit hash and short summary to the user.

**Never** force-push, never skip the rebase step, never push without the user having said "ship".
