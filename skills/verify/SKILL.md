# /verify

Run the verification suite and record the result so `check_handoff` knows whether the working tree is safe to hand off.

## When to use

- After completing any coding task before marking it done or ending the session.
- Before running `/handoff` — check_handoff will block if verification hasn't run since the last edit.
- Any time you want a confidence check on the current state.

## Steps

1. **Read the test strategy.** Read `context/test-strategy.md` to understand what the verification suite consists of for this project.

2. **Run the test suite.** Execute the project's tests with the appropriate command (e.g. `pytest`, `npm test`, `go test ./...`). Capture stdout and stderr.

3. **Run static analysis.** If the project uses a linter or type-checker, run it now. Record failures.

4. **Run the build.** If there is a compile or build step, run it and confirm it succeeds.

5. **Evaluate results.** Summarise: tests passed/failed, linting issues, build status.

6. **Record verification state.** Write the current edit hash to `.claude/.last_verified`:
   ```python
   import os, subprocess
   proj = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
   hash_path = os.path.join(proj, '.claude', '.last_edit_hash')
   verified_path = os.path.join(proj, '.claude', '.last_verified')
   if os.path.exists(hash_path):
       with open(hash_path) as f:
           h = f.read().strip()
       os.makedirs(os.path.dirname(verified_path), exist_ok=True)
       with open(verified_path, 'w') as f:
           f.write(h)
   ```

7. **Report.** Output a clear pass/fail summary. If any check failed, do not mark verification as passed — fix the issues first.

## Blocking Rule

If tests fail, do not record verification as passed. Fix the failures or explicitly note them as known-failing with justification in `context/known-problems.md` before recording.
