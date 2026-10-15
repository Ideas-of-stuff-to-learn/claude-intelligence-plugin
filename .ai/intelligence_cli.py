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


def cmd_dashboard(proj, port: int = 7654):
    server_script = proj / '.ai' / 'dashboard_server.py'
    if not server_script.exists():
        # Try plugin's own dashboard_server
        server_script = Path(__file__).resolve().parent / 'dashboard_server.py'
    if not server_script.exists():
        print("ERROR: dashboard_server.py not found. Run: ci install")
        sys.exit(1)
    print(f"Starting Intelligence Dashboard at http://localhost:{port}")
    print("Press Ctrl+C to stop.\n")
    try:
        os.execv(sys.executable, [sys.executable, '-I', str(server_script),
                                   str(proj), '--port', str(port)])
    except KeyboardInterrupt:
        pass


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

    # Copy context templates — create context/ if it doesn't exist yet
    ctx_dst = project_dir / 'context'
    ctx_src = plugin_dir / 'templates' / 'context'
    if ctx_src.exists():
        ctx_dst.mkdir(exist_ok=True)
    if ctx_dst.exists() and ctx_src.exists():
        added_ctx = 0
        for tmpl in ctx_src.glob('*.md'):
            dest = ctx_dst / tmpl.name
            if not dest.exists():
                shutil.copy2(str(tmpl), str(dest))
                added_ctx += 1
        if added_ctx:
            print(f"✓ Added {added_ctx} missing context templates")

    # Write .claude/settings.json if missing — required for hooks to fire in Claude Code
    settings_path = project_dir / '.claude' / 'settings.json'
    if not settings_path.exists():
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        hook_entries: dict = {}
        hook_map = {
            'SessionStart': ['session_start.py'],
            'PreToolUse':   ['safe_point_guard.py', 'context_sync.py'],
            'PostToolUse':  ['context_sync.py'],
            'Stop':         ['check_handoff.py', 'task_complete_stats.py'],
            'PreCompact':   ['precompact_snapshot.py'],
        }
        for ev, scripts in hook_map.items():
            hooks_for_ev = [
                {'type': 'command', 'command': f'python3 .claude/hooks/{h}'}
                for h in scripts
                if (project_dir / '.claude' / 'hooks' / h).exists()
            ]
            if hooks_for_ev:
                hook_entries[ev] = hooks_for_ev
        settings_path.write_text(json.dumps({'hooks': hook_entries}, indent=2))
        print("✓ Created .claude/settings.json (hooks wired)")

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

      Multi-copy group — group gets a number, copies get letters:
        "  NN)  BBBB  Name  (N local copies)"
        "              remote: <url>"
        "        a)  <path1>"
        "        b)  <path2>"

      Picking a group number shows the a/b/c sub-menu.

    Column offsets (0-based):
      0-1   : leading spaces
      2-3   : right-justified pick number (2 wide)
      4     : )
      5-6   : two spaces
      7-10  : badge ([ci] or 4 spaces)
      11-12 : two spaces
      13+   : name content
    Sub-entry (indented, tight):
      0-7   : eight spaces
      8     : letter
      9     : )
      10-11 : two spaces
      12+   : path
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

    # Each top-level entry is either a str (single path) or list[str] (multi-copy)
    all_entries: list = []

    _NUM_W = 2   # width of top-level number column
    # "  NN)  " = 2+2+1+2 = 7 chars before name — tight, no badge column
    _CONT = ' ' * 7  # continuation indent for remote/path lines

    def _ci(has: bool) -> str:
        return '  [ci]' if has else ''

    def _entry(n: int, name: str, has_ci: bool = False) -> str:
        return f"  {n:>{_NUM_W}})  {name}{_ci(has_ci)}"

    def _sub(letter: str, path: str) -> str:
        # Indented under the group: 8 spaces so it's clearly nested
        return f"        {letter})  {path}"

    # ── Connected to a remote ──────────────────────────────────────────────
    if by_norm:
        print("  Connected to a remote:\n")
        for _norm, group in by_norm.items():
            canonical_url = group[0]['remote']
            name = group[0]['name']
            n = len(all_entries) + 1

            if len(group) == 1:
                r = group[0]
                all_entries.append(r['path'])
                print(_entry(n, name, r.get('has_plugin', False)))
                print(f"{_CONT}remote: {canonical_url}")
                print(f"{_CONT}{r['path']}")
            else:
                paths = [r['path'] for r in group]
                all_entries.append(paths)
                any_ci = any(r.get('has_plugin') for r in group)
                print(_entry(n, f"{name}  ({len(group)} local copies)", any_ci))
                print(f"{_CONT}remote: {canonical_url}")
                for i, r in enumerate(group):
                    print(_sub(chr(ord('a') + i), r['path']))
            print()

    # ── Local only ────────────────────────────────────────────────────────
    if local_only:
        print("  Local only (no remote):\n")
        for r in local_only:
            n = len(all_entries) + 1
            all_entries.append(r['path'])
            print(_entry(n, r['name'], r.get('has_plugin', False)))
            print(f"{_CONT}{r['path']}")
        print()

    print("  [ci] = claude intelligence plugin installed\n")

    if not sys.stdin.isatty():
        return

    # ── Interactive picker ────────────────────────────────────────────────
    try:
        choice = input("Enter number (or Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if not choice:
        return

    try:
        idx = int(choice) - 1
    except ValueError:
        print("Invalid input.")
        return

    if not 0 <= idx < len(all_entries):
        print("Invalid selection.")
        return

    entry = all_entries[idx]

    if isinstance(entry, str):
        print(f"\n  cd \"{entry}\"")
    else:
        # Multi-copy: show a/b/c sub-menu
        print()
        for i, path in enumerate(entry):
            print(f"  {chr(ord('a') + i)})  {path}")
        print()
        try:
            sub = input("Enter letter (or Enter to skip): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not sub:
            return
        si = ord(sub[0]) - ord('a')
        if len(sub) == 1 and 0 <= si < len(entry):
            print(f"\n  cd \"{entry[si]}\"")
        else:
            print("Invalid selection.")


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


def cmd_export_context(proj, to_file: bool = False) -> None:
    """Generate a compact context snapshot for pasting into a cloud LLM."""
    ctx = proj / 'context'
    lines = ['=== CI CONTEXT SNAPSHOT ===']
    lines.append(f"Project: {proj.name}")

    import datetime as _dt
    lines.append(f"Exported: {_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    # Stack from overview.md
    overview = ctx / 'overview.md'
    if overview.exists():
        text = overview.read_text()
        # Grab first 8 non-empty lines
        snippet = '\n'.join(
            line for line in text.splitlines() if line.strip()
        )[:600]
        lines.append(f"\n--- overview.md (excerpt) ---\n{snippet}\n")

    # Current task
    ct = ctx / 'current-task.md'
    if ct.exists():
        text = ct.read_text()
        snippet = '\n'.join(line for line in text.splitlines() if line.strip())[:400]
        lines.append(f"--- current-task.md ---\n{snippet}\n")

    # Last handoff entry
    hf = ctx / 'handoff.md'
    if hf.exists():
        text = hf.read_text()
        # Take the first entry (up to 400 chars)
        lines.append(f"--- handoff.md (latest entry) ---\n{text[:400].strip()}\n")

    # Constraints
    cn = ctx / 'constraints.md'
    if cn.exists():
        text = cn.read_text()
        lines.append(f"--- constraints.md (excerpt) ---\n{text[:300].strip()}\n")

    # Known problems
    kp = ctx / 'known-problems.md'
    if kp.exists():
        text = kp.read_text()
        lines.append(f"--- known-problems.md (excerpt) ---\n{text[:300].strip()}\n")

    lines.append('=== END CI CONTEXT SNAPSHOT ===')
    output = '\n'.join(lines)

    if to_file:
        out_path = proj / '.ai' / 'cloud-context.txt'
        out_path.write_text(output)
        print(f"Context snapshot written to: {out_path}")
    else:
        print(output)


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
        port = 7654
        project_dir = str(proj)
        for a in args[1:]:
            if a.startswith('--port='):
                port = int(a.split('=', 1)[1])
            elif a.isdigit():
                port = int(a)
            else:
                project_dir = a
        cmd_dashboard(Path(project_dir), port)
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
    elif cmd == 'export-context':
        to_file = '--file' in args
        cmd_export_context(proj, to_file)
    elif cmd == 'pentest':
        pentest_script = Path(__file__).resolve().parent / 'pentest_runner.py'
        if not pentest_script.exists():
            print("ERROR: pentest_runner.py not found. Run: ci install")
            sys.exit(1)
        os.execv(sys.executable, [sys.executable, '-I', str(pentest_script)] + args[1:])
    elif cmd == 'test':
        cmd_surgical_test(proj, args[1:])
    elif cmd == 'snapshots':
        cmd_snapshots(proj, args[1:])
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
  pentest <type> <target>  Sandboxed security scan (web|source|cli|docker|report)
  test             Surgical test runner — only tests affected by recent changes
  test --all       Run full test suite
  snapshots        List compaction snapshots; pass platform name to show that one
  setup-alias      Add ci to PATH for your shell
  log-event <type> <component> <status>
  help             Show this message
""")
    else:
        print(f"Unknown command: {cmd}\nRun 'ci help' to see all commands.")
        sys.exit(1)


def _build_gist_content(proj: Path) -> str:
    """Build one self-contained document: system prompt + context snapshot.
    Pasting the Gist URL into any LLM loads both instructions and project state.
    """
    plugin_dir = Path(__file__).resolve().parent.parent
    prompt_path = plugin_dir / 'adapters' / 'cloud-llm' / 'SYSTEM_PROMPT_UNIVERSAL.md'
    system_prompt = ''
    if prompt_path.exists():
        raw = prompt_path.read_text()
        lines = raw.splitlines()
        system_prompt = '\n'.join(lines[4:]).strip()  # skip title + paste-instruction header

    generic_file = proj / 'context' / 'compaction-generic.md'
    snapshot = generic_file.read_text().strip() if generic_file.exists() else \
        f'_No snapshot yet. Run `ci snapshots --generate` in {proj.name}._'

    import datetime
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    return f'''<!-- CI Intelligence Plugin — auto-generated context bundle -->
<!-- Fetching this URL loads both your instructions AND project context. -->
<!-- Project: {proj.name} | Updated: {ts} -->

{system_prompt}

---

## Current Project Context

{snapshot}
'''


def _gist_push(proj: Path, platform: str = 'generic') -> str:
    """Push combined system-prompt+context to a GitHub Gist. Returns the gist URL."""
    import urllib.request
    import urllib.error

    content = _build_gist_content(proj)
    if not content.strip():
        raise FileNotFoundError('No snapshot file found. Run: ci snapshots --generate')

    # Load stored gist ID (so we update instead of creating duplicates)
    gist_id_file = Path.home() / '.claude-intel' / 'gist-id'
    gist_id = gist_id_file.read_text().strip() if gist_id_file.exists() else None

    # Prefer gh CLI (handles auth automatically, works with SSO/2FA/proxy)
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True)
        if result.returncode == 0:
            if gist_id:
                # Update existing gist
                r = subprocess.run(
                    ['gh', 'gist', 'edit', gist_id, '--filename', 'ci-context.md',
                     '--desc', f'CI context snapshot — {proj.name}'],
                    input=content, text=True, capture_output=True
                )
                if r.returncode == 0:
                    url = f'https://gist.github.com/{gist_id}'
                    return url
            # Create new gist
            r = subprocess.run(
                ['gh', 'gist', 'create', '--secret',
                 '--desc', f'CI context snapshot — {proj.name}',
                 '--filename', 'ci-context.md'],
                input=content, text=True, capture_output=True
            )
            if r.returncode == 0:
                url = r.stdout.strip()
                gist_id = url.split('/')[-1]
                gist_id_file.parent.mkdir(parents=True, exist_ok=True)
                gist_id_file.write_text(gist_id)
                return url
    except FileNotFoundError:
        pass  # gh not installed — fall through to token method

    # Fallback: GitHub API with token from env
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        payload = json.dumps({
            'description': f'CI context snapshot — {proj.name}',
            'public': False,
            'files': {'ci-context.md': {'content': content}},
        }).encode()
        headers = {
            'Authorization': f'token {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.github+json',
        }
        if gist_id:
            req = urllib.request.Request(f'https://api.github.com/gists/{gist_id}',
                                         data=payload, headers=headers, method='PATCH')
        else:
            req = urllib.request.Request('https://api.github.com/gists',
                                         data=payload, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            url = data['html_url']
            gist_id_file.parent.mkdir(parents=True, exist_ok=True)
            gist_id_file.write_text(data['id'])
            return url
        except Exception:
            pass

    # Zero-config fallback: anonymous public paste (0x0.st) — no account needed
    url_cache = Path.home() / '.claude-intel' / 'paste-url'
    try:
        data_bytes = content.encode('utf-8')
        boundary = b'----CIBoundary'
        body = (
            b'--' + boundary + b'\r\n'
            b'Content-Disposition: form-data; name="file"; filename="ci-context.md"\r\n'
            b'Content-Type: text/markdown\r\n\r\n' +
            data_bytes + b'\r\n'
            b'--' + boundary + b'--\r\n'
        )
        req = urllib.request.Request(
            'https://0x0.st',
            data=body,
            headers={'Content-Type': f'multipart/form-data; boundary={boundary.decode()}'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            url = resp.read().decode().strip()
        if url.startswith('http'):
            url_cache.parent.mkdir(parents=True, exist_ok=True)
            url_cache.write_text(url)
            return url
    except Exception:
        pass

    raise RuntimeError(
        'Could not reach any paste service.\n'
        'For private uploads: gh auth login  (https://cli.github.com)\n'
        'For manual push:     export GITHUB_TOKEN=<token> from https://github.com/settings/tokens'
    )


def cmd_snapshots(proj: Path, args: list) -> None:
    """List compaction snapshots saved when sessions hit context limits.

    ci snapshots                  — list all saved snapshots
    ci snapshots --push           — push snapshot to GitHub Gist (auto-persists for Mode C)
    ci snapshots claude           — show the Claude snapshot
    ci snapshots chatgpt          — show ChatGPT snapshot
    ci snapshots <url>            — detect platform from URL, show that snapshot
    """
    _URL_TO_PLATFORM = {
        'claude.ai':      'claude',
        'chat.openai.com':'chatgpt',
        'chatgpt.com':    'chatgpt',
        'gemini.google':  'gemini',
        'bard.google':    'gemini',
        'github.com/copilot': 'copilot',
        'cursor.':        'cursor',
        'windsurf.':      'windsurf',
    }
    _KNOWN_PLATFORMS = ['claude', 'chatgpt', 'gemini', 'copilot', 'cursor', 'windsurf', 'generic']

    index_path = proj / '.ai' / 'compaction-index.json'
    ctx = proj / 'context'

    # Resolve target platform from args
    target = args[0] if args else None
    if target:
        # URL → platform
        for url_fragment, platform in _URL_TO_PLATFORM.items():
            if url_fragment in target:
                target = platform
                break

    # List mode
    if not target:
        if not index_path.exists():
            print("No compaction snapshots found.")
            print("Snapshots are saved automatically when a session approaches its context limit.")
            print("Trigger manually: ci snapshots --generate")
            return
        idx = json.loads(index_path.read_text())
        print(f"Compaction snapshots for: {proj.name}\n")
        for p, info in idx.items():
            fpath = proj / info['file']
            exists = '✓' if fpath.exists() else '✗'
            print(f"  {exists}  {p:12s}  {info.get('updated','')[:16]}  → {info['file']}")
        print("\nView a snapshot:  ci snapshots <platform>  (e.g. ci snapshots chatgpt)")
        print("Or pass a URL:    ci snapshots https://chatgpt.com/...")
        return

    if target == '--generate':
        hook = Path(__file__).resolve().parent.parent / 'hooks' / 'precompact_snapshot.py'
        if hook.exists():
            env = dict(os.environ)
            env['CLAUDE_PROJECT_DIR'] = str(proj)
            result = subprocess.run([sys.executable, '-I', str(hook)], env=env)
            sys.exit(result.returncode)
        else:
            print("ERROR: precompact_snapshot.py not found")
            sys.exit(1)

    if target == '--push':
        try:
            url = _gist_push(proj)
            print('✓ Snapshot pushed to GitHub Gist')
            print(f'  {url}')
            print()
            print('Share this URL with your next chat session.')
            print('The LLM will fetch it automatically (Mode C in SYSTEM_PROMPT_UNIVERSAL.md).')
        except Exception as e:
            print(f'ERROR: {e}')
            sys.exit(1)
        return

    # Show a specific platform snapshot
    if target not in _KNOWN_PLATFORMS:
        print(f"Unknown platform: {target}")
        print(f"Known: {', '.join(_KNOWN_PLATFORMS)}")
        sys.exit(1)

    snap_file = ctx / f'compaction-{target}.md'
    if not snap_file.exists():
        print(f"No snapshot for '{target}' yet.")
        print("Snapshots are created automatically when sessions hit context limits.")
        print("Create one now: ci snapshots --generate")
        sys.exit(1)

    print(snap_file.read_text())


def cmd_surgical_test(proj: Path, args: list) -> None:
    """Surgical test runner: only run tests for changed/broken components.

    Principles:
    - Map recently changed files to their test IDs via git diff
    - Run only those tests (not the full suite) unless --all is passed
    - Zero in on failures, print them clearly
    - Exit non-zero if any test fails
    """
    run_all = '--all' in args

    test_dir = proj / 'tests'
    if not test_dir.exists():
        # Fall back to plugin dir
        test_dir = Path(__file__).resolve().parent.parent / 'tests'
    if not test_dir.exists():
        print("No tests/ directory found. Run ci install first.")
        sys.exit(1)

    # --- Map source files → test node IDs ---
    # Each entry: (glob_pattern_in_changed_files, [pytest_node_id, ...])
    FILE_TO_TESTS = [
        ('dashboard_server.py',  ['tests/test_new_features.py::test_dashboard_server_script_exists',
                                   'tests/test_new_features.py::test_dashboard_cmd_resolves_server',
                                   'tests/test_new_features.py::test_dashboard_security_api',
                                   'tests/test_new_features.py::test_dashboard_security_api_with_report']),
        ('pentest_runner.py',    ['tests/test_new_features.py::test_pentest_runner_exists',
                                   'tests/test_new_features.py::test_pentest_pattern_scan',
                                   'tests/test_new_features.py::test_pentest_docker_scan',
                                   'tests/test_new_features.py::test_pentest_cli_dispatch']),
        ('intelligence_cli.py', ['tests/test_new_features.py::test_export_context_runs',
                                   'tests/test_new_features.py::test_export_context_to_file',
                                   'tests/test_cli.py']),
        ('rebuild_db.py',       ['tests/test_db.py']),
        ('sync_context.py',     ['tests/test_cli.py']),
        ('registry.py',         ['tests/test_registry.py']),
        ('adapters/',           ['tests/test_new_features.py::test_cloud_llm_adapter_files_exist',
                                   'tests/test_new_features.py::test_cloud_llm_readme_has_three_modes']),
        ('agents/',             ['tests/test_new_features.py::test_pentest_agent_exists']),
        ('skills/',             ['tests/test_new_features.py::test_pentest_skill_exists']),
    ]

    # Collect changed files via git diff (staged + unstaged vs HEAD)
    changed: set = set()
    if not run_all:
        try:
            r1 = subprocess.run(['git', '-C', str(proj), 'diff', '--name-only', 'HEAD'],
                                capture_output=True, text=True)
            r2 = subprocess.run(['git', '-C', str(proj), 'diff', '--name-only', '--cached'],
                                capture_output=True, text=True)
            changed = set((r1.stdout + r2.stdout).splitlines())
            if not changed:
                # Nothing uncommitted — look at last commit
                r3 = subprocess.run(['git', '-C', str(proj), 'diff', '--name-only', 'HEAD~1', 'HEAD'],
                                    capture_output=True, text=True)
                changed = set(r3.stdout.splitlines())
        except Exception:
            changed = set()

    if run_all or not changed:
        if run_all:
            print("Running full test suite (--all)...")
        else:
            print("No changed files detected — running full test suite...")
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', str(test_dir), '-v', '--tb=short'],
            cwd=str(proj)
        )
        sys.exit(result.returncode)

    # Select tests that match changed files
    selected: list = []
    seen: set = set()
    for changed_file in changed:
        for pattern, test_ids in FILE_TO_TESTS:
            if pattern in changed_file:
                for tid in test_ids:
                    if tid not in seen:
                        seen.add(tid)
                        selected.append(tid)

    if not selected:
        print(f"Changed files: {', '.join(sorted(changed))}")
        print("No mapped tests for these files — running full suite to be safe...")
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', str(test_dir), '-v', '--tb=short'],
            cwd=str(proj)
        )
        sys.exit(result.returncode)

    print(f"Changed: {', '.join(sorted(changed))}")
    print(f"Surgical tests ({len(selected)}):")
    for t in selected:
        print(f"  {t}")
    print()

    result = subprocess.run(
        [sys.executable, '-m', 'pytest'] + selected + ['-v', '--tb=short'],
        cwd=str(proj)
    )

    if result.returncode != 0:
        print("\n[ci test] FAILURES — zero in on the above and fix before pushing.")
    else:
        print("\n[ci test] All surgical tests GREEN.")
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
