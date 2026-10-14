# /recover-session

Reconstruct context after a compact event, token limit, or session restart. Resume work without losing state.

## When to use

- At the start of a session when `context/session-snapshot.md` contains a pre-compact snapshot.
- When you realise mid-session that important context was lost.
- When `session_start.py` reports a snapshot is available.

## Steps

1. **Read the snapshot.** Read `context/session-snapshot.md` fully.

2. **Read the handoff.** Read `context/handoff.md` — the most recent entry tells you what was last completed.

3. **Read the active task.** Read `context/current-task.md` to understand what was in progress.

4. **Check the knowledge base.** Run:
   ```
   python .ai/intelligence_cli.py status
   ```
   If stale, run `python .ai/rebuild_db.py` to rebuild.

5. **Inspect the working tree.** Run `git status` and `git diff` to see what state the files are in. This is ground truth — prefer it over snapshot text.

6. **Identify the next action.** Based on the snapshot, handoff, and working tree, determine:
   - What was just completed (don't redo it)
   - What was in progress (may need to be re-examined)
   - What is the single next step

7. **Report your understanding.** Before taking any action, state:
   - What you believe the current state is
   - What you are about to do next
   - Any uncertainty or gaps in your understanding

8. **Resume.** Take the single next step from the task plan.

## After Recovery

- Do not re-read all context docs from scratch — trust the snapshot + handoff.
- If something in the snapshot conflicts with the working tree, trust the working tree.
- Update `context/session-snapshot.md` to mark it as consumed once you are oriented.
