"""
PreCompact hook — precompact_snapshot.py
Before context window summarisation, writes a full session snapshot to:
  - context/session-snapshot.md  (overwritten — always the latest)
  - prepends a summary block to context/handoff.md
Then syncs SQLite.
Fails open on all errors.
"""
import sys, json, os, subprocess
from datetime import datetime

def get_git_head(proj):
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, cwd=proj)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"

def get_touched_files(proj):
    try:
        r = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                           capture_output=True, text=True, cwd=proj)
        s = subprocess.run(["git", "diff", "--cached", "--name-only"],
                           capture_output=True, text=True, cwd=proj)
        files = list(set((r.stdout + s.stdout).strip().splitlines()))
        return files if files else ["(none — no uncommitted changes)"]
    except Exception:
        return ["(git unavailable)"]

def read_active_task(proj):
    try:
        path = os.path.join(proj, "context", "current-task.md")
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        in_section = False
        result = []
        for line in lines:
            if line.strip() == "## Active Task":
                in_section = True
                continue
            if in_section:
                if line.startswith("## ") and line.strip() != "## Active Task":
                    break
                result.append(line)
        return "".join(result).strip() or "(no active task)"
    except Exception:
        return "(current-task.md unavailable)"

def main():
    try:
        proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        head = get_git_head(proj)
        touched = get_touched_files(proj)
        active_task = read_active_task(proj)

        snapshot = f"""# Session Snapshot — {now}

**Git HEAD:** `{head}`
**Triggered by:** PreCompact (context window about to be summarised)

## Active Task
{active_task}

## Files Touched This Session
{chr(10).join(f'- {f}' for f in touched)}

## Context
This snapshot was auto-written before context summarisation.
If you are reading this in a new session or after a compact, treat this as
the highest-priority recovery document — it captures the exact mid-session state.

Load order after a compact:
1. This file (session-snapshot.md)
2. context/handoff.md (newest block)
3. context/current-task.md
4. context/realignment.md
5. Target context docs for the active task area

## Open Work
(Populated manually via /task-done or /handoff — check handoff.md for details)
"""

        # Overwrite session-snapshot.md
        snap_path = os.path.join(proj, "context", "session-snapshot.md")
        with open(snap_path, "w", encoding="utf-8") as f:
            f.write(snapshot)

        # Prepend summary block to handoff.md
        handoff_path = os.path.join(proj, "context", "handoff.md")
        block = f"""## Pre-Compact Snapshot — {now}

**Git HEAD:** `{head}`
**Files touched:** {', '.join(touched[:5])}{'...' if len(touched) > 5 else ''}
**Active task:** {active_task[:100]}

*(Auto-written by PreCompact hook — full snapshot in context/session-snapshot.md)*

---

"""
        if os.path.exists(handoff_path):
            with open(handoff_path, encoding="utf-8") as f:
                existing = f.read()
            with open(handoff_path, "w", encoding="utf-8") as f:
                f.write(block + existing)
        else:
            with open(handoff_path, "w", encoding="utf-8") as f:
                f.write(block)

        # Sync SQLite
        sync_script = os.path.join(proj, ".ai", "sync_context.py")
        if os.path.exists(sync_script):
            subprocess.run([sys.executable, sync_script], cwd=proj, capture_output=True)

    except Exception as e:
        print(f"[precompact_snapshot] warning: {e}", file=sys.stderr)

    sys.exit(0)

if __name__ == "__main__":
    main()
