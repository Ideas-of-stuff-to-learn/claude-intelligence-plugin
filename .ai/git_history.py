#!/usr/bin/env python3 -I
"""
git_history.py — Git history mining for plugin-relevant history.
All functions return empty/None gracefully; never raise.
"""
import os
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

_PLUGIN_PATHS = ['.ai/', 'hooks/', 'context/', 'tasks/', 'skills/', 'agents/']
_TIMEOUT = 10


def _run(args: List[str], cwd: str) -> Optional[str]:
    """Run a git command; return stdout or None on any failure."""
    try:
        proc = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=_TIMEOUT
        )
        if proc.returncode != 0:
            return None
        return proc.stdout
    except Exception:
        return None


def get_install_date(project_dir: str) -> Optional[str]:
    """Return ISO date of earliest commit that added plugin files, or None."""
    out = _run(
        ['git', 'log', '--follow', '--diff-filter=A', '--pretty=format:%ad',
         '--date=short', '--', '.ai/', 'hooks/', 'context/'],
        cwd=project_dir
    )
    if not out:
        return None
    dates = [line.strip() for line in out.splitlines() if line.strip()]
    if not dates:
        return None
    return sorted(dates)[0]


def get_commit_activity(project_dir: str, days: int = 90) -> List[Dict[str, Any]]:
    """Return list of {date, count} dicts (commits per day for last N days)."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
    out = _run(
        ['git', 'log', f'--since={since}', '--pretty=format:%ad', '--date=short'],
        cwd=project_dir
    )
    counts: Dict[str, int] = {}
    if out:
        for line in out.splitlines():
            d = line.strip()
            if d:
                counts[d] = counts.get(d, 0) + 1
    return [{'date': d, 'count': c} for d, c in sorted(counts.items())]


def get_component_touches(project_dir: str) -> Dict[str, int]:
    """Return dict of how many commits touched each component."""
    out = _run(
        ['git', 'log', '--name-only', '--pretty=format:'],
        cwd=project_dir
    )
    components = {'context': 0, 'hooks': 0, '.ai': 0, 'tasks': 0, 'skills': 0, 'agents': 0}
    if not out:
        return components
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        for comp in components:
            if line.startswith(comp + '/') or line.startswith(comp + os.sep):
                components[comp] += 1
                break
    return components


def get_recent_commits(project_dir: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Return list of {hash, date, message, files_changed} for recent commits touching plugin paths."""
    out = _run(
        ['git', 'log', f'-{limit * 5}', '--name-only',
         '--pretty=format:COMMIT:%H %ad %s', '--date=short'],
        cwd=project_dir
    )
    if not out:
        return []
    results = []
    current: Optional[Dict[str, Any]] = None
    for line in out.splitlines():
        if line.startswith('COMMIT:'):
            if current and current.get('_plugin'):
                results.append({
                    'hash': current['hash'],
                    'date': current['date'],
                    'message': current['message'],
                    'files_changed': current['files_changed'],
                })
            rest = line[len('COMMIT:'):]
            parts = rest.split(' ', 2)
            current = {
                'hash': parts[0] if len(parts) > 0 else '',
                'date': parts[1] if len(parts) > 1 else '',
                'message': parts[2] if len(parts) > 2 else '',
                'files_changed': [],
                '_plugin': False,
            }
        elif current is not None and line.strip():
            f = line.strip()
            current['files_changed'].append(f)
            if any(f.startswith(p) for p in _PLUGIN_PATHS):
                current['_plugin'] = True
    if current and current.get('_plugin'):
        results.append({
            'hash': current['hash'],
            'date': current['date'],
            'message': current['message'],
            'files_changed': current['files_changed'],
        })
    return results[:limit]


def get_last_active(project_dir: str) -> Optional[str]:
    """Return ISO date of most recent commit touching any plugin path, or None."""
    args = ['git', 'log', '-1', '--pretty=format:%ad', '--date=short', '--'] + _PLUGIN_PATHS
    out = _run(args, cwd=project_dir)
    if not out:
        return None
    date = out.strip()
    return date or None
