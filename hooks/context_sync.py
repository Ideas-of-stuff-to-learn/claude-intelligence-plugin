"""
PostToolUse hook (Edit|Write matcher) — context_sync.py
- If edited file is under context/, runs sync_context.py
- If edited file is a .py file and ruff is available, runs ruff check --fix
- Records current HEAD hash to .claude/.last_edit_hash
Fails open on all internal errors.
"""
import sys
import json
import os
import subprocess
import shutil

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

        # Record working-tree state fingerprint (not commit hash — that misses uncommitted edits)
        last_edit_path = os.path.join(proj, ".claude", ".last_edit_hash")
        try:
            import hashlib
            result_unstaged = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True, text=True, cwd=proj
            )
            result_staged = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True, text=True, cwd=proj
            )
            result_untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True, text=True, cwd=proj
            )
            files = sorted(set(
                result_unstaged.stdout.splitlines() +
                result_staged.stdout.splitlines() +
                result_untracked.stdout.splitlines()
            ))
            h = hashlib.sha256()
            for f in files:
                fpath = os.path.join(proj, f)
                h.update(f.encode())
                if os.path.exists(fpath):
                    h.update(str(os.path.getmtime(fpath)).encode())
            os.makedirs(os.path.dirname(last_edit_path), exist_ok=True)
            with open(last_edit_path, "w") as out:
                out.write(h.hexdigest())
        except Exception:
            pass

        # Log hook.fired event (fail open)
        try:
            import importlib.util
            import pathlib
            _spec = importlib.util.spec_from_file_location(
                "event_logger",
                pathlib.Path(proj) / ".ai" / "event_logger.py"
            )
            if _spec and _spec.loader:
                _mod = importlib.util.module_from_spec(_spec)
                _spec.loader.exec_module(_mod)
                _mod.log_event(
                    "hook.fired", "context_sync", "active",
                    metadata={"file_path": file_path, "rel": rel},
                    project_dir=proj,
                )
        except Exception:
            pass

    except Exception as e:
        print(f"[context_sync] warning: {e}", file=sys.stderr)

    sys.exit(0)

if __name__ == "__main__":
    main()
