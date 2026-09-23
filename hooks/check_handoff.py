"""
Stop hook — check_handoff.py
Blocks session end if:
  1. Source files changed this session but handoff.md was not updated
  2. Source files were edited but /verifier has not been run since the last edit
Fails open on all internal errors.
"""
import sys, json, os, subprocess

def main():
    try:
        payload = json.load(sys.stdin)

        # Required: always allow stop when stop_hook_active is true (avoids infinite loop)
        if payload.get("stop_hook_active"):
            sys.exit(0)

        proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

        # Check if any source files changed this session
        last_edit_path = os.path.join(proj, ".claude", ".last_edit_hash")
        if not os.path.exists(last_edit_path):
            sys.exit(0)  # No edits recorded this session

        # Check git status for uncommitted changes or recent commits
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=proj
        )
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=proj
        )
        changed_files = (result.stdout + staged.stdout).strip().splitlines()

        # Filter to source files only (not context/, tasks/, .claude/)
        source_changed = [
            f for f in changed_files
            if not f.startswith("context/") and
               not f.startswith("tasks/") and
               not f.startswith(".claude/")
        ]

        if not source_changed:
            sys.exit(0)

        # Check if handoff.md was updated this session
        handoff_path = os.path.join(proj, "context", "handoff.md")
        handoff_in_git = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", "context/handoff.md"],
            capture_output=True, text=True, cwd=proj
        )
        handoff_staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--", "context/handoff.md"],
            capture_output=True, text=True, cwd=proj
        )
        handoff_updated = bool(
            handoff_in_git.stdout.strip() or handoff_staged.stdout.strip()
        )

        if not handoff_updated:
            print(
                "Source files changed but context/handoff.md was not updated.\n"
                "Run /handoff before ending this session.",
                file=sys.stderr
            )
            sys.exit(2)

        # Check if verifier has been run since last edit
        last_edit_hash = open(last_edit_path).read().strip()
        verified_path = os.path.join(proj, ".claude", ".last_verified")
        if os.path.exists(verified_path):
            last_verified = open(verified_path).read().strip()
            if last_verified != last_edit_hash:
                print(
                    "Source files were edited but /verifier has not been run since the last edit.\n"
                    "Run /verifier and confirm it passes before ending this session.",
                    file=sys.stderr
                )
                sys.exit(2)

        sys.exit(0)

    except Exception as e:
        print(f"[check_handoff] warning: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
