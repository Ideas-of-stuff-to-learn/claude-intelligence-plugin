---
name: ship-branch
description: Manual-only skill. Runs /task-done, creates an ai/<desc> branch, commits and pushes. Only invoke when user explicitly says "ship to branch".
disable-model-invocation: true
---

**Trigger:** User explicitly says "ship to branch". Never run this automatically.

Exact order:

1. **Run /task-done** — complete the mini-handoff first.

2. **Branch name** — derive from current task: `ai/<short-kebab-desc>` (e.g. `ai/auth-migration`). Confirm with user if not obvious.

3. **Create branch** — `git checkout -b ai/<desc>` (stash with `-u` first if uncommitted changes exist).

4. **Stage and review** — `git status`, then `git add` only relevant files. Review diff. Stop if secrets or unintended files are staged.

5. **Commit** — conventional commit message. End with:
   ```
   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   ```

6. **Push** — `git push -u origin ai/<desc>`

7. **Confirm** — report branch name, commit hash, and short summary to user. Offer to create a PR if they want one.

**Never** force-push. Never auto-merge.
