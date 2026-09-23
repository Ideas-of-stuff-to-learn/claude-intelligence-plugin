"""
PostToolUse hook (Edit|Write matcher) — context_sync.py
- If edited file is under context/, runs sync_context.py
- If edited file is a .py file and ruff is available, runs ruff check --fix
- Records current HEAD hash to .claude/.last_edit_hash
Fails open on all internal errors.
"""
import sys, json, os, subprocess, shutil

def main():
    try:
        payload = json.load(sys.stdin)
        tool_input = payload.get("tool_input", {})
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")

        proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        rel = os.path.relpath(file_path, proj) if file_path else ""

        # Sync SQLite if a context doc was edited
        context_prefixes = ("context" + os.sep, "context/")
        if any(rel.startswith(p) for p in context_prefixes):
            sync_script = os.path.join(proj, ".ai", "sync_context.py")
            if os.path.exists(sync_script):
                subprocess.run([sys.executable, sync_script], cwd=proj,
                               capture_output=True)

        # Run ruff on Python files if available
        if file_path and file_path.endswith(".py") and shutil.which("ruff"):
            subprocess.run(["ruff", "check", "--fix", "--quiet", file_path],
                           capture_output=True)

        # Record that an edit happened this session
        last_edit_path = os.path.join(proj, ".claude", ".last_edit_hash")
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=proj
            )
            if result.returncode == 0:
                with open(last_edit_path, "w") as f:
                    f.write(result.stdout.strip())
        except Exception:
            pass

    except Exception as e:
        print(f"[context_sync] warning: {e}", file=sys.stderr)

    sys.exit(0)

if __name__ == "__main__":
    main()
