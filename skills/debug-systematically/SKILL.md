# /debug-systematically

Diagnose a bug using a structured, evidence-driven approach. No guessing.

## When to use

- When tests fail and the cause is not immediately obvious.
- When a system is behaving unexpectedly in production or staging.
- When you have tried one fix and it didn't work — stop and use this skill.

## Steps

1. **State the symptom precisely.** Write down exactly what is observed vs what is expected. Include error messages verbatim, not paraphrased.

2. **Read the context.** Read `context/known-problems.md` — is this already documented? Read `context/handoff.md` — did recent changes touch this area?

3. **Form hypotheses.** List 3–5 possible causes, ordered by likelihood. Do not start fixing until you have hypotheses.

4. **Test hypotheses cheaply first.** For each hypothesis, identify the cheapest way to confirm or rule it out:
   - Add a log statement and run the failing path
   - Check a config value
   - Read the relevant code carefully
   - Run a targeted test

5. **Narrow the search space.** Use binary search on the call stack: is the bug in the caller or callee? Is the input wrong or the processing wrong?

6. **Find the root cause.** Keep narrowing until you can point to a specific line and explain WHY it is wrong — not just that it produces the wrong output.

7. **Verify the fix.** Before committing: does the original failing test now pass? Does the rest of the suite still pass?

8. **Add a regression test.** Write a test that fails before the fix and passes after. Commit the test alongside the fix.

9. **Document.** Update `context/known-problems.md` if this was a known issue. Add a note in `context/handoff.md` about what was found.

## Anti-Patterns to Avoid

- Do not apply a fix based on a guess and then check if it worked.
- Do not change multiple things at once — change one thing, verify, then change the next.
- Do not dismiss a hypothesis without testing it.
- Do not read a stacktrace and immediately start changing code — read the full trace first.
