# /intelligence-health

Check the health of the intelligence system and fix any issues found.

## When to use

- At the start of a session when something feels off.
- After a project restructure that may have moved files.
- When hooks are not firing as expected.
- Periodically as a maintenance check.

## Steps

1. **Run the health check.**
   ```
   python .ai/intelligence_cli.py health
   ```

2. **Interpret results.** For each reported issue:

   | Issue | Fix |
   |-------|-----|
   | MISSING: context/[doc] | Copy template: `cp templates/context/[doc] context/[doc]` then populate |
   | MISSING: .ai/knowledge.db | Run `python .ai/rebuild_db.py` |
   | MISSING: .ai/rebuild_db.py | Copy from plugin: hooks and .ai/ scripts missing |
   | MISSING hook: [event] | Update `.claude/settings.json` — copy from `templates/settings.json` |
   | INVALID: .claude/settings.json | Fix JSON syntax errors |

3. **Rebuild knowledge base if stale.**
   ```
   python .ai/rebuild_db.py
   python .ai/intelligence_cli.py status
   ```

4. **Verify hooks are wired.** Check `.claude/settings.json` contains entries for:
   - `SessionStart`
   - `Stop`
   - `PreToolUse` (with `Edit|Write` matcher)
   - `PostToolUse` (with `Edit|Write` matcher)
   - `PreCompact`

5. **Test a hook manually.**
   ```
   echo '{}' | python .claude/hooks/session_start.py
   ```
   Should print the session start banner without errors.

6. **Report.** State what was fixed and what (if anything) still needs attention.

## Maintenance Schedule

Run `/intelligence-health` at the start of any session where:
- More than a week has passed since last use
- The project had significant structural changes
- Hooks produced unexpected output or errors
