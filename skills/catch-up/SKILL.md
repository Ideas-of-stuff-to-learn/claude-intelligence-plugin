---
name: catch-up
description: Assumes the intelligence system is already installed. Brings context docs fully up to date with the current codebase state — efficiently, without wasting the context window.
---

Use this when the intelligence system is in place but context docs may have drifted from the code (after a long session, after a merge, or at the start of a new session on an existing project).

**Do NOT use this for fresh installs — use `/build-intelligence` instead.**

## Steps

1. **Load minimal working memory** — query SQLite for the realignment record, read `context/handoff.md` (newest block only), read `context/current-task.md` (Active Task section only). Do not load anything else yet.

2. **Check staleness markers** — for each `context/*.md`, read only the first line to check for a `<!-- last-verified: <hash> YYYY-MM-DD -->` marker. Build a list of which docs are stale (marker missing, or hash doesn't match a recent commit).

3. **Spawn targeted explorer subagents** — for each stale doc (or area), spawn one `explorer` subagent scoped to that area only. Pass it: the current doc content, the area to survey, and the specific questions to answer. Do NOT spawn a full-repo survey — one focused subagent per stale doc.

4. **Write updates** — for each returned survey, update only the sections that changed. Preserve existing content that is still accurate. Do not rewrite whole docs.

5. **Re-stamp staleness markers** — add/update `<!-- last-verified: <hash> YYYY-MM-DD -->` at the top of each updated doc, where `<hash>` is the current `git rev-parse --short HEAD`.

6. **Sync DB** — run `python .ai/sync_context.py`.

7. **Report** — tell the user which docs were updated and what changed. If everything was already current, say so.

## Efficiency rules

- Never read a context doc fully if only the staleness marker needs checking — use `head -1` or read only the first line.
- Never spawn more than one subagent per doc — scope each one narrowly.
- Never run `rebuild_db.py` unless a file was added or removed from the context set; `sync_context.py` is enough for content updates.
- Stop after step 7 — do not proceed to code changes. This skill only updates context, not source.
