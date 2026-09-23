"""
SessionStart hook — session_start.py
Prints context into the AI session (injected as system context by Claude Code).
Also auto-rebuilds knowledge.db if stale or missing.
Fails open: any internal error prints a warning and exits 0.
"""
import sys, os, subprocess
from datetime import datetime

def read_section(path, heading):
    """Read lines from a heading until the next same-level heading or end of file."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        in_section = False
        result = []
        level = heading.count("#")
        for line in lines:
            if line.strip() == heading.strip():
                in_section = True
                result.append(line)
                continue
            if in_section:
                stripped = line.lstrip("#")
                curr_level = len(line) - len(stripped)
                if line.startswith("#") and curr_level <= level and line.strip() != heading.strip():
                    break
                result.append(line)
        return "".join(result).strip()
    except Exception:
        return ""

def newest_handoff_block(path):
    """Return just the first 'What Was Just Done' block from handoff.md."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Find first block between --- separators
        blocks = content.split("\n---\n")
        if blocks:
            return blocks[0].strip()
        return content[:1000]
    except Exception:
        return ""

def main():
    try:
        proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        print("=" * 60)
        print("SESSION START — Intelligence System")
        print("=" * 60)

        # Print newest handoff block
        handoff_path = os.path.join(proj, "context", "handoff.md")
        handoff = newest_handoff_block(handoff_path)
        if handoff:
            print("\n## Last Session Handoff\n")
            print(handoff[:1500])  # cap at 1500 chars to avoid flooding context
        else:
            print("\n[handoff.md not found or empty]")

        # Print active task
        task_path = os.path.join(proj, "context", "current-task.md")
        active = read_section(task_path, "## Active Task")
        if active:
            print("\n## Active Task\n")
            print(active[:500])
        else:
            print("\n[current-task.md: no active task found]")

        # Check session snapshot
        snapshot_path = os.path.join(proj, "context", "session-snapshot.md")
        if os.path.exists(snapshot_path):
            with open(snapshot_path, encoding="utf-8") as f:
                snap = f.read().strip()
            if snap and not snap.startswith("# Session Snapshot"):
                print("\n## Session Snapshot (pre-compact)\n")
                print(snap[:800])

        # Auto-rebuild knowledge.db if stale or missing
        db_path = os.path.join(proj, ".ai", "knowledge.db")
        rebuild_script = os.path.join(proj, ".ai", "rebuild_db.py")
        needs_rebuild = not os.path.exists(db_path)
        if not needs_rebuild and os.path.exists(db_path):
            db_mtime = os.path.getmtime(db_path)
            ctx_dir = os.path.join(proj, "context")
            if os.path.exists(ctx_dir):
                for f in os.listdir(ctx_dir):
                    if f.endswith(".md"):
                        fpath = os.path.join(ctx_dir, f)
                        if os.path.getmtime(fpath) > db_mtime:
                            needs_rebuild = True
                            break

        if needs_rebuild and os.path.exists(rebuild_script):
            print("\n[Rebuilding knowledge.db — context docs newer than index...]")
            result = subprocess.run(
                [sys.executable, rebuild_script],
                capture_output=True, text=True, cwd=proj
            )
            if result.returncode == 0:
                print("[knowledge.db rebuilt successfully]")
            else:
                print(f"[rebuild_db warning: {result.stderr[:200]}]")

        print("\n" + "=" * 60)
        print("Reminders: /safe-point before touching code | /verifier before marking complete | /handoff before ending session")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"[session_start] warning: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
