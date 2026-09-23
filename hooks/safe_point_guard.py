"""
PreToolUse hook (Edit|Write matcher) — safe_point_guard.py
Blocks source code edits until a safe-point has been recorded for today.
Fails open: any internal error exits 0 (warning only, never locks the owner out).
"""
import sys, json, os, re
from datetime import date

def main():
    try:
        payload = json.load(sys.stdin)
        tool_input = payload.get("tool_input", {})
        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")

        proj = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        rel = os.path.relpath(file_path, proj) if file_path else ""

        # Allow edits to context/, tasks/, .claude/ — only guard actual source code
        exempt_prefixes = ("context" + os.sep, "tasks" + os.sep, ".claude" + os.sep,
                           "context/", "tasks/", ".claude/")
        if not file_path or any(rel.startswith(p) for p in exempt_prefixes):
            sys.exit(0)

        # Check revert-state.md for an in-progress row dated today
        revert_path = os.path.join(proj, "context", "revert-state.md")
        today = date.today().isoformat()
        if os.path.exists(revert_path):
            with open(revert_path, encoding="utf-8") as f:
                content = f.read()
            if today in content and "in-progress" in content:
                sys.exit(0)

        # No safe-point found for today
        print("No safe-point recorded for today — run /safe-point first before editing source files.", file=sys.stderr)
        sys.exit(2)

    except Exception as e:
        print(f"[safe_point_guard] warning: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()