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
  python .ai/intelligence_cli.py install [project_dir]
  python .ai/intelligence_cli.py setup-alias
"""
import sys
import os
import sqlite3
import json
import hashlib
import shutil
import subprocess
from pathlib import Path


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
        from budget_manager import preflight_estimate, read_session_usage, estimate_cost
        est = preflight_estimate(task_description, project_dir=str(proj))
        print(f"Budget estimate for: {task_description[:80]}")
        print(f"  Tool calls:   ~{est.estimated_tool_calls}")
        print(f"  Agent calls:  ~{est.estimated_agent_calls}")
        print(f"  Index ops:    ~{est.estimated_index_ops}")
        print(f"  Confidence:   {est.confidence}")
        print()

        # Real token usage from Claude Code JSONL transcripts
        usage = read_session_usage()
        if usage.get('turns'):
            cost = estimate_cost(usage)
            print("Actual usage this session (from ~/.claude/projects/):")
            print(f"  Input tokens:        {usage['input_tokens']:,}")
            print(f"  Output tokens:       {usage['output_tokens']:,}")
            print(f"  Cache read:          {usage['cache_read_input_tokens']:,}")
            print(f"  Cache write:         {usage['cache_creation_input_tokens']:,}")
            if usage.get('thinking_tokens'):
                print(f"  Thinking tokens:     {usage['thinking_tokens']:,}")
            print(f"  Turns:               {usage['turns']}")
            print(f"  Est. cost (list $):  ${cost['total']:.4f}  "
                  f"(in ${cost['input']:.4f} / out ${cost['output']:.4f} / "
                  f"cache_r ${cost['cache_read']:.4f} / cache_w ${cost['cache_write']:.4f})")
            print("  (List prices — actual cost may differ on Max/Team plans)")
        else:
            print("  No Claude Code session data found in ~/.claude/projects/")
    except Exception as exc:
        print(f"Budget unavailable: {exc}")


def cmd_dashboard(proj):
    print("Starting dashboard at http://localhost:7654")
    print(f"Run: python {proj / '.ai' / 'dashboard_server.py'}")


# ---------------------------------------------------------------------------
# version_check
# ---------------------------------------------------------------------------

HOOK_FILES = [
    'session_start.py',
    'safe_point_guard.py',
    'context_sync.py',
    'check_handoff.py',
    'precompact_snapshot.py',
    'task_complete_stats.py',
]

AI_FILES = [
    '.ai/rebuild_db.py',
    '.ai/sync_context.py',
    '.ai/intelligence_cli.py',
    '.ai/event_logger.py',
    '.ai/budget_manager.py',
    '.ai/analyze_repo.py',
    '.ai/registry.py',
    '.ai/git_history.py',
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version_check(project_dir: str, plugin_dir: str) -> list:
    """Check installed hook/ai files vs canonical versions in plugin_dir.

    Returns list of dicts: {file, status ('current'|'outdated'|'missing'), action}
    """
    project_dir = Path(project_dir)
    plugin_dir = Path(plugin_dir)
    results = []

    # Check hook files
    hooks_src = plugin_dir / 'hooks'
    hooks_dst = project_dir / '.claude' / 'hooks'
    for fname in HOOK_FILES:
        canonical = hooks_src / fname
        installed = hooks_dst / fname
        if not canonical.exists():
            continue
        if not installed.exists():
            results.append({'file': f'.claude/hooks/{fname}', 'status': 'missing', 'action': 'copy'})
        elif _sha256(canonical) != _sha256(installed):
            results.append({'file': f'.claude/hooks/{fname}', 'status': 'outdated', 'action': 'update'})
        else:
            results.append({'file': f'.claude/hooks/{fname}', 'status': 'current', 'action': 'none'})

    # Check .ai/ files
    for rel in AI_FILES:
        # canonical lives directly at plugin_dir/<rel>
        canonical = plugin_dir / rel
        installed = project_dir / rel
        if not canonical.exists():
            continue
        if not installed.exists():
            results.append({'file': rel, 'status': 'missing', 'action': 'copy'})
        elif _sha256(canonical) != _sha256(installed):
            results.append({'file': rel, 'status': 'outdated', 'action': 'update'})
        else:
            results.append({'file': rel, 'status': 'current', 'action': 'none'})

    return results


# ---------------------------------------------------------------------------
# install command
# ---------------------------------------------------------------------------

def find_repo_root(start: str) -> str:
    """Walk up from start until we find a .git directory. Returns start if not found."""
    current = Path(start).resolve()
    for directory in [current, *current.parents]:
        if (directory / '.git').exists():
            if directory != current:
                print(f"[ci] Not at repo root — using: {directory}")
            return str(directory)
    print(f"[ci] Warning: no .git found above {start}, using as-is")
    return start


def cmd_install(project_dir: str) -> None:
    """Install or upgrade the intelligence system in a repo."""
    project_dir = Path(project_dir)
    # plugin_dir is the parent of the .ai/ directory containing this script
    plugin_dir = Path(__file__).resolve().parent.parent

    print(f"Installing claude-intel in: {project_dir}")

    checks = version_check(str(project_dir), str(plugin_dir))

    patched_hooks = 0
    added_ai = 0
    for item in checks:
        if item['status'] in ('outdated', 'missing'):
            src_rel = item['file']
            dst = project_dir / src_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            # Hook files: canonical source is plugin_dir/hooks/<fname>
            # AI files: canonical source is plugin_dir/<rel>
            if '.claude/hooks/' in src_rel:
                fname = Path(src_rel).name
                src = plugin_dir / 'hooks' / fname
            else:
                src = plugin_dir / src_rel
            if not src.exists():
                continue
            shutil.copy2(str(src), str(dst))
            if '.claude/hooks/' in src_rel:
                patched_hooks += 1
            else:
                added_ai += 1

    if patched_hooks:
        print(f"✓ Patched/added {patched_hooks} hook file(s)")
    if added_ai:
        print(f"✓ Patched/added {added_ai} .ai file(s)")

    # Copy context templates only if context/ dir already exists
    ctx_dst = project_dir / 'context'
    ctx_src = plugin_dir / 'templates' / 'context'
    if ctx_dst.exists() and ctx_src.exists():
        added_ctx = 0
        for tmpl in ctx_src.glob('*.md'):
            dest = ctx_dst / tmpl.name
            if not dest.exists():
                shutil.copy2(str(tmpl), str(dest))
                added_ctx += 1
        if added_ctx:
            print(f"✓ Added {added_ctx} missing context templates")

    # Rebuild DB
    rebuild_script = project_dir / '.ai' / 'rebuild_db.py'
    file_count = 0
    if rebuild_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, '-I', str(rebuild_script), str(project_dir)],
                capture_output=True, text=True, timeout=120
            )
            # Try to parse file count from output
            for line in (result.stdout + result.stderr).splitlines():
                if 'file' in line.lower():
                    import re
                    m = re.search(r'(\d+)\s+file', line)
                    if m:
                        file_count = int(m.group(1))
                        break
            print(f"✓ Index rebuilt ({file_count} files)")
        except Exception as exc:
            print(f"  (rebuild skipped: {exc})")
    else:
        print("  (rebuild_db.py not found, skipping index rebuild)")

    # Run analyze_repo
    analyze_script = project_dir / '.ai' / 'analyze_repo.py'
    if analyze_script.exists():
        try:
            subprocess.run(
                [sys.executable, '-I', str(analyze_script), str(project_dir)],
                capture_output=True, text=True, timeout=120
            )
            print("✓ Analysis complete (semantic, structural, exact)")
        except Exception as exc:
            print(f"  (analysis skipped: {exc})")
    else:
        print("  (analyze_repo.py not found, skipping analysis)")

    # Register project
    reg_script = project_dir / '.ai' / 'registry.py'
    if reg_script.exists():
        try:
            sys.path.insert(0, str(project_dir / '.ai'))
            import importlib.util
            spec = importlib.util.spec_from_file_location('registry', str(reg_script))
            reg_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(reg_mod)
            if hasattr(reg_mod, 'register_project'):
                reg_mod.register_project(str(project_dir))
            print("✓ Registered in global registry")
        except Exception as exc:
            print(f"  (registry skipped: {exc})")

    print("")
    print("Done. Run: ci status")


# ---------------------------------------------------------------------------
# setup-alias command
# ---------------------------------------------------------------------------

def find_local_git_repos(max_depth: int = 5) -> list:
    """Scan for git repos efficiently.

    Uses 'find' (C, parallel I/O) on Unix/Mac; falls back to os.scandir()
    with in-place dir pruning (avoids extra stat calls vs Path.iterdir).
    """
    home = Path.home()
    found_paths = _scan_for_git_dirs(home, max_depth)

    raw = []
    for path in sorted(found_paths, key=lambda p: Path(p).name.lower()):
        remote = _get_remote_url(path)
        raw.append({
            'path': path,
            'name': Path(path).name,
            'has_plugin': (Path(path) / '.ai').exists(),
            'remote': remote,
        })
    return raw


def _scan_for_git_dirs(root: Path, max_depth: int) -> set:
    """Return set of repo root paths. Tries 'find' first, falls back to scandir."""
    import subprocess as _sp

    # --- fast path: let the OS do it with find (Unix/Mac/WSL/Git Bash) ---
    try:
        result = _sp.run(
            ['find', str(root), '-maxdepth', str(max_depth),
             '-name', '.git', '-type', 'd', '-prune'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            repos = set()
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.endswith('/.git'):
                    repos.add(line[:-5])   # strip /.git
            if repos:
                return repos
    except (FileNotFoundError, Exception):
        pass  # 'find' not available (Windows CMD) — fall through

    # --- fallback: os.scandir with pruning, no extra stat() calls ---
    return _scandir_walk(str(root), max_depth)


def _scandir_walk(root: str, max_depth: int) -> set:
    """Efficient scandir-based walker. Prunes .git, hidden, and irrelevant dirs."""
    _SKIP = frozenset({
        'node_modules', '__pycache__', '.venv', 'venv', 'env',
        'dist', 'build', 'target', '.cache', 'vendor',
    })
    found = set()
    # Stack entries: (path_str, depth_remaining)
    stack = [(root, max_depth)]
    while stack:
        current, depth = stack.pop()
        if depth == 0:
            continue
        try:
            with os.scandir(current) as it:
                subdirs = []
                has_git = False
                for entry in it:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    if entry.name == '.git':
                        has_git = True
                    elif not entry.name.startswith('.') and entry.name not in _SKIP:
                        subdirs.append(entry.path)
                if has_git:
                    found.add(current)
                    # Don't descend into a repo's subdirs
                else:
                    stack.extend((p, depth - 1) for p in subdirs)
        except PermissionError:
            pass
    return found


def _get_remote_url(path: str) -> str:
    """Return the origin remote URL, or '' if none."""
    try:
        import subprocess as _sp
        r = _sp.run(
            ['git', '-C', path, 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, timeout=3
        )
        return r.stdout.strip() if r.returncode == 0 else ''
    except Exception:
        return ''


def _normalize_remote(url: str) -> str:
    """Normalize git remote URL so SSH and HTTPS variants of the same repo group together.

    git@github.com:user/repo.git  ->  github.com/user/repo
    https://github.com/user/repo  ->  github.com/user/repo
    """
    if not url:
        return url
    u = url.strip().rstrip('/')
    if u.endswith('.git'):
        u = u[:-4]
    # SSH: git@host:path  ->  host/path
    if u.startswith('git@'):
        u = u[4:].replace(':', '/', 1)
    # HTTPS: strip scheme
    for scheme in ('https://', 'http://'):
        if u.startswith(scheme):
            u = u[len(scheme):]
            break
    return u.lower()


def print_repo_list_and_pick(repos: list) -> None:
    """Print repos grouped by (normalized) remote URL.

    Column layout — ASCII only, works in CMD / PowerShell / bash / zsh:

      Single copy:
        "  NN)  BBBB  Name"
        "              remote: <url>"
        "              <path>"

      Multi-copy group (name in same column as single-copy name):
        "              Name  (N local copies)"
        "              remote: <url>"
        "  NN)  BBBB  <path1>"
        "  NN)  BBBB  <path2>"

      Local-only:
        "  NN)  BBBB  Name"
        "              <path>"

    Column offsets (0-based):
      0-1   : leading spaces
      2-3   : right-justified pick number (2 wide)
      4     : )
      5-6   : two spaces
      7-10  : badge ([ci] or 4 spaces)
      11-12 : two spaces
      13+   : name / path content
    """
    from collections import OrderedDict

    # Group by *normalized* remote so SSH and HTTPS of the same repo merge
    by_norm: dict = OrderedDict()
    local_only = []
    for r in repos:
        if r['remote']:
            norm = _normalize_remote(r['remote'])
            by_norm.setdefault(norm, []).append(r)
        else:
            local_only.append(r)

    all_paths: list = []   # indexed by pick-number (0-based)

    # Fixed column widths
    _NUM_W = 2              # digits in pick number
    _BADGE_W = 4            # len('[ci]')
    # Total prefix before content:  "  NN)  BBBB  " = 2+2+1+2+4+2 = 13
    _CONT = ' ' * 13        # continuation indent for remote/path lines

    def _badge(r: dict) -> str:
        return '[ci]' if r.get('has_plugin') else '    '

    def _entry(n: int, badge: str, content: str) -> str:
        return f"  {n:>{_NUM_W}})  {badge}  {content}"

    def _group_hdr(name: str, count: int) -> str:
        # No pick number — content starts at column 13 (same as _entry)
        return f"{_CONT}{name}  ({count} local copies)"

    # ── Connected to a remote ──────────────────────────────────────────────
    if by_norm:
        print("  Connected to a remote:\n")
        for _norm, group in by_norm.items():
            canonical_url = group[0]['remote']
            name = group[0]['name']

            if len(group) == 1:
                r = group[0]
                n = len(all_paths) + 1
                all_paths.append(r['path'])
                print(_entry(n, _badge(r), name))
                print(f"{_CONT}remote: {canonical_url}")
                print(f"{_CONT}{r['path']}")
            else:
                # Multi-copy: header (no pick number), then one line per copy
                print(_group_hdr(name, len(group)))
                print(f"{_CONT}remote: {canonical_url}")
                for r in group:
                    n = len(all_paths) + 1
                    all_paths.append(r['path'])
                    print(_entry(n, _badge(r), r['path']))
            print()

    # ── Local only ────────────────────────────────────────────────────────
    if local_only:
        print("  Local only (no remote):\n")
        for r in local_only:
            n = len(all_paths) + 1
            all_paths.append(r['path'])
            print(_entry(n, _badge(r), r['name']))
            print(f"{_CONT}{r['path']}")
        print()

    print("  [ci] = claude intelligence plugin installed\n")

    if not sys.stdin.isatty():
        return

    try:
        choice = input("Enter number to print cd command (or Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not choice:
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(all_paths):
            print(f"\n  cd \"{all_paths[idx]}\"")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")


def cmd_repos() -> None:
    """Scan for local git repos, grouped by remote presence."""
    print("Scanning for git repos...\n")
    repos = find_local_git_repos()

    if not repos:
        print("No git repos found in common locations under your home directory.")
        return

    n = len(repos)
    print(f"Found {n} git repo(s):\n")
    print_repo_list_and_pick(repos)


def is_in_repo(proj: Path) -> bool:
    """Return True if proj is inside a git repo with the plugin installed."""
    current = proj.resolve()
    for directory in [current, *current.parents]:
        if (directory / '.git').exists():
            return True
    return False


REPO_REQUIRED_CMDS = {
    'status', 'search', 'deps', 'rebuild', 'sync',
    'health', 'events', 'budget', 'dashboard', 'log-event',
}


def not_in_repo_prompt(proj: Path) -> None:
    """Warn the user they're not in a repo, scan for local git repos and offer navigation."""
    print(f"[ci] Not inside a git repo (checked from: {proj})")
    print()
    print("Scanning for git repos...\n")
    repos = find_local_git_repos()

    if not repos:
        print("No git repos found. Navigate to a repo and run 'ci install'.")
        sys.exit(1)

    print(f"Found {len(repos)} git repo(s):\n")
    print_repo_list_and_pick(repos)
    sys.exit(1)  # noqa: E501 — always exit after prompt; user must cd manually


def cmd_setup_alias(plugin_dir: str) -> None:
    """Detect shell and add plugin_dir to PATH in the appropriate rc file."""
    plugin_dir = Path(plugin_dir)
    home = Path.home()
    shell_env = os.environ.get('SHELL', '')
    shell_name = Path(shell_env).name if shell_env else ''

    fish_config = home / '.config' / 'fish' / 'config.fish'
    nu_config = home / '.config' / 'nushell' / 'config.nu'

    if shell_name == 'zsh' or (home / '.zshrc').exists():
        rc_file = home / '.zshrc'
        path_line = f'export PATH="{plugin_dir}:$PATH"'
    elif shell_name == 'bash' or (home / '.bashrc').exists():
        rc_file = home / '.bashrc'
        path_line = f'export PATH="{plugin_dir}:$PATH"'
    elif shell_name == 'fish' or fish_config.exists():
        rc_file = fish_config
        path_line = f'set -gx PATH {plugin_dir} $PATH'
    elif shell_name in ('nu', 'nushell') or nu_config.exists():
        rc_file = nu_config
        path_line = f'$env.PATH = ($env.PATH | prepend {plugin_dir})'
    elif shell_name in ('tcsh', 'csh'):
        rc_file = home / '.tcshrc' if (home / '.tcshrc').exists() else home / '.cshrc'
        path_line = f'setenv PATH "{plugin_dir}:$PATH"'
    elif shell_name in ('dash', 'sh'):
        rc_file = home / '.profile'
        path_line = f'export PATH="{plugin_dir}:$PATH"'
    else:
        print("Could not detect shell rc file.")
        print("Add this line to your shell config manually:")
        print(f'  export PATH="{plugin_dir}:$PATH"')
        return

    rc_file.parent.mkdir(parents=True, exist_ok=True)
    existing = rc_file.read_text() if rc_file.exists() else ''
    if str(plugin_dir) in existing or '.claude-intel' in existing:
        print(f"✓ PATH already set in {rc_file} (skipping)")
    else:
        with open(rc_file, 'a') as f:
            f.write(f'\n# Claude Intelligence CLI\n{path_line}\n')
        print(f"✓ Added to PATH in {rc_file}")

    print("")
    print("Restart your terminal, then run:")
    print("  ci install")


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
        args = ['help']
    cmd = args[0]

    # Guard: commands that need a repo context check we're actually in one
    if cmd in REPO_REQUIRED_CMDS and not is_in_repo(proj):
        not_in_repo_prompt(proj)
        return

    if cmd == 'status':
        project_dir = args[1] if len(args) > 1 else str(proj)
        cmd_status(Path(project_dir))
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
        project_dir = args[1] if len(args) > 1 else str(proj)
        cmd_health(Path(project_dir))
    elif cmd == 'events':
        project_dir = args[1] if len(args) > 1 else str(proj)
        cmd_events(Path(project_dir))
    elif cmd == 'budget' and len(args) > 1:
        cmd_budget(proj, ' '.join(args[1:]))
    elif cmd == 'dashboard':
        project_dir = args[1] if len(args) > 1 else str(proj)
        cmd_dashboard(Path(project_dir))
    elif cmd == 'log-event' and len(args) >= 4:
        cmd_log_event(proj, args[1], args[2], args[3])
    elif cmd == 'install':
        project_dir = args[1] if len(args) > 1 else str(proj)
        project_dir = find_repo_root(project_dir)
        cmd_install(project_dir)
    elif cmd == 'setup-alias':
        plugin_dir = str(Path(__file__).resolve().parent.parent)
        cmd_setup_alias(plugin_dir)
    elif cmd in ('repos', 'projects'):
        cmd_repos()
    elif cmd in ('help', '--help', '-h'):
        print("""ci — Claude Intelligence Plugin

USAGE
  ci <command> [args]

COMMANDS
  install          Install or upgrade plugin in current repo (walks up to repo root)
  status           Show index health and stats
  health           Check all components
  search <term>    Full-text search the knowledge index
  events           Show recent telemetry events
  budget <desc>    Estimate resource budget for a task
  dashboard        Start web dashboard at http://localhost:7654
  rebuild          Rebuild the SQLite index
  sync             Sync context markdown files into index
  repos            List all registered repos (navigate to one)
  setup-alias      Add ci to PATH for your shell
  log-event <type> <component> <status>
  help             Show this message
""")
    else:
        print(f"Unknown command: {cmd}\nRun 'ci help' to see all commands.")
        sys.exit(1)


if __name__ == '__main__':
    main()
