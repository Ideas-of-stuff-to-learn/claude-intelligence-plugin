#!/usr/bin/env python3 -I
"""
intelligence_cli.py — Portable intelligence engine CLI.
Usage:
  python .ai/intelligence_cli.py status
  python .ai/intelligence_cli.py search <term>
  python .ai/intelligence_cli.py deps <file>
  python .ai/intelligence_cli.py rebuild
  python .ai/intelligence_cli.py sync
  python .ai/intelligence_cli.py health
  python .ai/intelligence_cli.py init
  python .ai/intelligence_cli.py events
  python .ai/intelligence_cli.py budget <task_description>
  python .ai/intelligence_cli.py dashboard
  python .ai/intelligence_cli.py log-event <type> <component> <status>
"""
import sys, os, sqlite3, json, subprocess
from pathlib import Path
from datetime import datetime


def get_proj():
    return Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))


def get_db(proj):
    return proj / '.ai' / 'knowledge.db'


def cmd_status(proj):
    db = get_db(proj)
    if not db.exists():
        print("ERROR: knowledge.db not found. Run: python .ai/rebuild_db.py")
        sys.exit(1)
    conn = sqlite3.connect(str(db))
    files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    ctx = conn.execute("SELECT COUNT(*) FROM files WHERE is_context_doc=1").fetchone()[0]
    stale = conn.execute("SELECT COUNT(*) FROM context_freshness WHERE is_stale=1").fetchone()[0]
    ver = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
    rebuilt = conn.execute("SELECT value FROM project_config WHERE key='last_full_rebuild'").fetchone()
    conn.close()
    print(f"Schema version:   {ver[0] if ver else 'unknown'}")
    print(f"Files indexed:    {files}")
    print(f"Context docs:     {ctx}")
    print(f"Stale docs:       {stale}")
    print(f"Last rebuild:     {rebuilt[0] if rebuilt else 'unknown'}")


def cmd_search(proj, term):
    db = get_db(proj)
    if not db.exists():
        print("ERROR: knowledge.db not found")
        sys.exit(1)
    conn = sqlite3.connect(str(db))
    rows = conn.execute("""
        SELECT path, description FROM files
        WHERE path LIKE ? OR description LIKE ? OR tags LIKE ?
        ORDER BY is_context_doc DESC, path
        LIMIT 20
    """, (f'%{term}%', f'%{term}%', f'%{term}%')).fetchall()
    conn.close()
    if not rows:
        print(f"No results for '{term}'")
        return
    for path, desc in rows:
        print(f"  {path}")
        if desc:
            print(f"    {desc[:80]}")


def cmd_deps(proj, file_path):
    db = get_db(proj)
    if not db.exists():
        print("ERROR: knowledge.db not found")
        sys.exit(1)
    conn = sqlite3.connect(str(db))
    rows = conn.execute("""
        SELECT source, relationship, target, evidence FROM dependencies
        WHERE source LIKE ? OR target LIKE ?
        LIMIT 30
    """, (f'%{file_path}%', f'%{file_path}%')).fetchall()
    conn.close()
    if not rows:
        print(f"No dependency records for '{file_path}'")
        return
    for src, rel, tgt, ev in rows:
        print(f"  {src} --[{rel}]--> {tgt}")
        if ev:
            print(f"    evidence: {ev[:60]}")


def cmd_health(proj):
    issues = []
    ctx_dir = proj / 'context'
    ai_dir = proj / '.ai'

    if not ctx_dir.exists():
        issues.append("MISSING: context/ directory")
    else:
        expected = ['overview.md', 'architecture.md', 'dependencies.md', 'decisions.md',
                    'constraints.md', 'known-problems.md', 'handoff.md', 'current-task.md']
        for doc in expected:
            if not (ctx_dir / doc).exists():
                issues.append(f"MISSING: context/{doc}")

    if not (ai_dir / 'knowledge.db').exists():
        issues.append("MISSING: .ai/knowledge.db (run rebuild)")
    if not (ai_dir / 'rebuild_db.py').exists():
        issues.append("MISSING: .ai/rebuild_db.py")
    if not (ai_dir / 'sync_context.py').exists():
        issues.append("MISSING: .ai/sync_context.py")

    settings = proj / '.claude' / 'settings.json'
    if settings.exists():
        try:
            cfg = json.loads(settings.read_text())
            hooks = cfg.get('hooks', {})
            for ev in ['SessionStart', 'Stop', 'PreToolUse', 'PostToolUse', 'PreCompact']:
                if ev not in hooks:
                    issues.append(f"MISSING hook: {ev} in .claude/settings.json")
        except Exception:
            issues.append("INVALID: .claude/settings.json (parse error)")
    else:
        issues.append("MISSING: .claude/settings.json")

    if issues:
        print("Intelligence system health: ISSUES FOUND")
        for i in issues:
            print(f"  WARNING: {i}")
    else:
        print("Intelligence system health: OK")


def cmd_events(proj):
    try:
        sys.path.insert(0, str(proj / '.ai'))
        from event_logger import query_events
        events = query_events(project_dir=str(proj), limit=20)
        if not events:
            print("No events recorded yet.")
            return
        for e in events:
            ts = e.get('timestamp', '')[:19]
            print(f"  {ts}  {e.get('event_type','?'):<30} [{e.get('component','?')}] {e.get('status','')}")
    except Exception as exc:
        print(f"Events unavailable: {exc}")


def cmd_budget(proj, task_description):
    try:
        sys.path.insert(0, str(proj / '.ai'))
        from budget_manager import preflight_estimate
        est = preflight_estimate(task_description, project_dir=str(proj))
        print(f"Budget estimate for: {task_description[:80]}")
        print(f"  Tool calls:   {est.estimated_tool_calls}")
        print(f"  Agent calls:  {est.estimated_agent_calls}")
        print(f"  Index ops:    {est.estimated_index_ops}")
        print(f"  Confidence:   {est.confidence}")
        print(f"  Notes:        {est.notes}")
    except Exception as exc:
        print(f"Budget estimate unavailable: {exc}")


def cmd_dashboard(proj):
    print("Starting dashboard at http://localhost:7654")
    print(f"Run: python {proj / '.ai' / 'dashboard_server.py'}")


def cmd_log_event(proj, event_type, component, status):
    try:
        sys.path.insert(0, str(proj / '.ai'))
        from event_logger import log_event
        eid = log_event(event_type, component, status, project_dir=str(proj))
        if eid:
            print(f"Event logged: {eid}")
        else:
            print("Failed to log event (DB may be missing — run rebuild first)")
    except Exception as exc:
        print(f"Event logging failed: {exc}")


def main():
    proj = get_proj()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    cmd = args[0]
    if cmd == 'status':
        cmd_status(proj)
    elif cmd == 'search' and len(args) > 1:
        cmd_search(proj, args[1])
    elif cmd == 'deps' and len(args) > 1:
        cmd_deps(proj, args[1])
    elif cmd == 'rebuild':
        rb = proj / '.ai' / 'rebuild_db.py'
        if rb.exists():
            os.execv(sys.executable, [sys.executable, '-I', str(rb), str(proj)])
        else:
            print("ERROR: rebuild_db.py not found")
    elif cmd == 'sync':
        sc = proj / '.ai' / 'sync_context.py'
        if sc.exists():
            os.execv(sys.executable, [sys.executable, '-I', str(sc), str(proj)])
        else:
            print("ERROR: sync_context.py not found")
    elif cmd == 'health':
        cmd_health(proj)
    elif cmd == 'events':
        cmd_events(proj)
    elif cmd == 'budget' and len(args) > 1:
        cmd_budget(proj, ' '.join(args[1:]))
    elif cmd == 'dashboard':
        cmd_dashboard(proj)
    elif cmd == 'log-event' and len(args) >= 4:
        cmd_log_event(proj, args[1], args[2], args[3])
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
