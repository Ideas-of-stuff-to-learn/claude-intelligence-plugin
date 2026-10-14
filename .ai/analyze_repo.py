#!/usr/bin/env python3 -I
"""
analyze_repo.py — Scan a project and record analysis passes.
Usage: python .ai/analyze_repo.py [project_dir]
"""
import os
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', '.ai'}
_IGNORE_PATTERNS = ['knowledge.db', 'knowledge.db-shm', 'knowledge.db-wal']


def _get_db_path(project_dir: str) -> Path:
    return Path(project_dir) / ".ai" / "knowledge.db"


def _open_conn(project_dir: str) -> Optional[sqlite3.Connection]:
    db_path = _get_db_path(project_dir)
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        # Ensure tables
        conn.executescript("""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS first_encounter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT NOT NULL,
    project_id TEXT,
    files_discovered INTEGER,
    files_indexed INTEGER,
    structure_summary TEXT,
    semantic_summary TEXT,
    constraints_found INTEGER,
    decisions_found INTEGER,
    known_problems_found INTEGER,
    hook_events_wired INTEGER,
    schema_version INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS analysis_passes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passed_at TEXT NOT NULL,
    project_id TEXT,
    trigger TEXT,
    lens TEXT NOT NULL,
    findings TEXT,
    files_examined INTEGER,
    duration_ms INTEGER,
    schema_version INTEGER DEFAULT 1
);
""")
        conn.commit()
        return conn
    except Exception:
        return None


def _get_project_id(project_dir: str) -> str:
    return str(Path(project_dir).resolve())


def _discover_files(project_dir: str) -> List[str]:
    """Discover all files, respecting gitignore-style patterns."""
    found = []
    base = Path(project_dir).resolve()
    for root, dirs, files in os.walk(str(base)):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS]
        for fname in files:
            if any(p in fname for p in _IGNORE_PATTERNS):
                continue
            found.append(os.path.join(root, fname))
    return found


def record_first_encounter(
    project_dir: str,
    structure_summary: Dict[str, Any],
    semantic_summary: Dict[str, Any],
    stats: Dict[str, Any],
) -> bool:
    """Write one row; idempotent (only inserts if none exists for this project_id)."""
    try:
        conn = _open_conn(project_dir)
        if conn is None:
            return False
        pid = _get_project_id(project_dir)
        try:
            existing = conn.execute(
                "SELECT id FROM first_encounter WHERE project_id=? LIMIT 1", (pid,)
            ).fetchone()
            if existing:
                return True
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT INTO first_encounter
                   (recorded_at, project_id, files_discovered, files_indexed,
                    structure_summary, semantic_summary,
                    constraints_found, decisions_found, known_problems_found,
                    hook_events_wired, schema_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,1)""",
                (
                    now, pid,
                    stats.get('files_discovered', 0),
                    stats.get('files_indexed', 0),
                    json.dumps(structure_summary),
                    json.dumps(semantic_summary),
                    stats.get('constraints_found', 0),
                    stats.get('decisions_found', 0),
                    stats.get('known_problems_found', 0),
                    stats.get('hook_events_wired', 0),
                )
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception:
        return False


def record_analysis_pass(
    project_dir: str,
    trigger: str,
    lens: str,
    findings: Dict[str, Any],
    files_examined: int,
    duration_ms: int,
) -> bool:
    """Append a row to analysis_passes."""
    try:
        conn = _open_conn(project_dir)
        if conn is None:
            return False
        pid = _get_project_id(project_dir)
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT INTO analysis_passes
                   (passed_at, project_id, trigger, lens, findings,
                    files_examined, duration_ms, schema_version)
                   VALUES (?,?,?,?,?,?,?,1)""",
                (now, pid, trigger, lens, json.dumps(findings), files_examined, duration_ms)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception:
        return False


def get_first_encounter(project_dir: str) -> Optional[Dict[str, Any]]:
    """Return the first_encounter row as dict or None."""
    try:
        conn = _open_conn(project_dir)
        if conn is None:
            return None
        pid = _get_project_id(project_dir)
        try:
            row = conn.execute(
                "SELECT * FROM first_encounter WHERE project_id=? LIMIT 1", (pid,)
            ).fetchone()
            if row is None:
                return None
            d = dict(row)
            for key in ('structure_summary', 'semantic_summary'):
                if d.get(key):
                    try:
                        d[key] = json.loads(d[key])
                    except Exception:
                        pass
            return d
        finally:
            conn.close()
    except Exception:
        return None


def get_analysis_passes(
    project_dir: str, lens: Optional[str] = None, limit: int = 20
) -> List[Dict[str, Any]]:
    """Return list of analysis_passes rows."""
    try:
        conn = _open_conn(project_dir)
        if conn is None:
            return []
        pid = _get_project_id(project_dir)
        try:
            if lens:
                rows = conn.execute(
                    "SELECT * FROM analysis_passes WHERE project_id=? AND lens=? "
                    "ORDER BY passed_at DESC LIMIT ?",
                    (pid, lens, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM analysis_passes WHERE project_id=? "
                    "ORDER BY passed_at DESC LIMIT ?",
                    (pid, limit)
                ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get('findings'):
                    try:
                        d['findings'] = json.loads(d['findings'])
                    except Exception:
                        pass
                result.append(d)
            return result
        finally:
            conn.close()
    except Exception:
        return []


def _run_semantic_lens(project_dir: str) -> tuple[Dict[str, Any], int]:
    """Read context/*.md and extract purpose, domains, key abstractions."""
    findings: Dict[str, Any] = {
        'purpose': '',
        'domains': [],
        'key_abstractions': [],
    }
    files_examined = 0
    ctx_dir = Path(project_dir) / 'context'
    if not ctx_dir.exists():
        return findings, files_examined

    overview = ctx_dir / 'overview.md'
    if overview.exists():
        files_examined += 1
        try:
            text = overview.read_text(encoding='utf-8', errors='replace')
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and not p.startswith('#')]
            if paragraphs:
                findings['purpose'] = paragraphs[0][:500]
        except Exception:
            pass

    domains = set()
    abstractions = set()
    for md_file in ctx_dir.glob('*.md'):
        files_examined += 1
        try:
            text = md_file.read_text(encoding='utf-8', errors='replace')
            # Extract headings as domains/abstractions
            for line in text.splitlines():
                if line.startswith('## '):
                    domains.add(line[3:].strip())
                elif line.startswith('### '):
                    abstractions.add(line[4:].strip())
        except Exception:
            pass

    findings['domains'] = sorted(list(domains))[:20]
    findings['key_abstractions'] = sorted(list(abstractions))[:30]
    return findings, files_examined


def _run_structural_lens(project_dir: str, all_files: List[str]) -> tuple[Dict[str, Any], int]:
    """Inspect file tree and imports."""
    base = Path(project_dir).resolve()
    dirs_seen = set()
    entry_points = []
    test_dirs = set()
    hook_scripts = []
    adapter_files = []

    for fpath in all_files:
        p = Path(fpath)
        rel = p.relative_to(base) if p.is_relative_to(base) else p
        parts = rel.parts
        if len(parts) > 1:
            dirs_seen.add(parts[0])
        if p.suffix == '.py':
            # Check for __main__ block
            try:
                text = p.read_text(encoding='utf-8', errors='replace')
                if 'if __name__' in text and '__main__' in text:
                    entry_points.append(str(rel))
                if 'hook' in p.name.lower():
                    hook_scripts.append(str(rel))
                if 'adapter' in p.name.lower():
                    adapter_files.append(str(rel))
            except Exception:
                pass
        # Test dirs
        for part in parts:
            if part in ('tests', 'test', '__tests__', 'spec'):
                test_dirs.add(part)

    findings = {
        'dirs': sorted(list(dirs_seen)),
        'entry_points': sorted(entry_points)[:20],
        'test_dirs': sorted(list(test_dirs)),
        'hook_scripts': sorted(hook_scripts)[:20],
        'adapter_files': sorted(adapter_files)[:20],
    }
    return findings, len(all_files)


def _run_exact_lens(project_dir: str) -> tuple[Dict[str, Any], int]:
    """Query SQLite DB for top referenced files, known_problems, verifications, constraints."""
    findings: Dict[str, Any] = {
        'top_referenced_files': [],
        'files_with_known_problems': [],
        'files_with_verifications': [],
        'constraint_count': 0,
    }
    files_examined = 0
    db_path = _get_db_path(project_dir)
    if not db_path.exists():
        return findings, files_examined
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            # Top referenced files
            try:
                rows = conn.execute(
                    "SELECT path, COUNT(*) as cnt FROM file_deps GROUP BY path "
                    "ORDER BY cnt DESC LIMIT 10"
                ).fetchall()
                findings['top_referenced_files'] = [dict(r) for r in rows]
                files_examined += len(rows)
            except Exception:
                pass
            # Files with known problems
            try:
                rows = conn.execute(
                    "SELECT DISTINCT file_path FROM known_problems LIMIT 20"
                ).fetchall()
                findings['files_with_known_problems'] = [r[0] for r in rows]
            except Exception:
                pass
            # Files with verifications
            try:
                rows = conn.execute(
                    "SELECT DISTINCT file_path FROM verifications LIMIT 20"
                ).fetchall()
                findings['files_with_verifications'] = [r[0] for r in rows]
            except Exception:
                pass
            # Constraint count
            try:
                count = conn.execute("SELECT COUNT(*) FROM constraints").fetchone()[0]
                findings['constraint_count'] = count
            except Exception:
                pass
        finally:
            conn.close()
    except Exception:
        pass
    return findings, files_examined


def run_analysis(
    project_dir: str,
    trigger: str = 'manual',
    lenses: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run analysis passes and record them. Returns a summary dict."""
    if lenses is None:
        lenses = ['semantic', 'structural', 'exact']

    all_files = _discover_files(project_dir)
    results = {}

    for lens in lenses:
        t0 = time.time()
        try:
            if lens == 'semantic':
                findings, files_examined = _run_semantic_lens(project_dir)
            elif lens == 'structural':
                findings, files_examined = _run_structural_lens(project_dir, all_files)
            elif lens == 'exact':
                findings, files_examined = _run_exact_lens(project_dir)
            else:
                continue
        except Exception as e:
            findings = {'error': str(e)}
            files_examined = 0
        duration_ms = int((time.time() - t0) * 1000)
        record_analysis_pass(project_dir, trigger, lens, findings, files_examined, duration_ms)
        results[lens] = findings

    # Register project in global registry (fail-open)
    try:
        from registry import register_project
        register_project(project_dir)
    except Exception:
        pass

    return {
        'files_discovered': len(all_files),
        'lenses_run': lenses,
        'results': results,
    }


def get_repo_summary(project_dir: str) -> Dict[str, Any]:
    """Return a combined summary dict for a project."""
    from pathlib import Path as _Path
    try:
        from git_history import get_install_date, get_last_active, get_component_touches
        install_date = get_install_date(project_dir)
        last_active = get_last_active(project_dir)
        component_touches = get_component_touches(project_dir)
    except Exception:
        install_date = None
        last_active = None
        component_touches = {}

    first_encounter = get_first_encounter(project_dir)

    db_path = _get_db_path(project_dir)
    db_exists = db_path.exists()
    files_indexed = 0
    events_count = 0
    task_count = 0
    if db_exists:
        try:
            conn = sqlite3.connect(str(db_path), timeout=5)
            try:
                try:
                    files_indexed = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
                except Exception:
                    pass
                try:
                    events_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                except Exception:
                    pass
                try:
                    task_count = conn.execute("SELECT COUNT(*) FROM task_history").fetchone()[0]
                except Exception:
                    pass
            finally:
                conn.close()
        except Exception:
            pass

    proj = _Path(project_dir)
    hooks_wired = (proj / 'hooks').exists() and any((proj / 'hooks').glob('*.py'))
    context_populated = (proj / 'context').exists() and any((proj / 'context').glob('*.md'))

    return {
        'first_encounter': first_encounter,
        'install_date': install_date,
        'last_active': last_active,
        'component_touches': component_touches,
        'files_indexed': files_indexed,
        'events_count': events_count,
        'task_count': task_count,
        'health': {
            'db_exists': db_exists,
            'hooks_wired': hooks_wired,
            'context_populated': context_populated,
        },
    }


def main() -> None:
    project_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        'CLAUDE_PROJECT_DIR', os.getcwd()
    )
    project_dir = str(Path(project_dir).resolve())
    print(f"Analyzing: {project_dir}")

    all_files = _discover_files(project_dir)
    print(f"Files discovered: {len(all_files)}")

    # Record first encounter if needed
    enc = get_first_encounter(project_dir)
    if enc is None:
        print("Recording first encounter...")
        structural_findings, _ = _run_structural_lens(project_dir, all_files)
        semantic_findings, _ = _run_semantic_lens(project_dir)
        # Gather stats from DB
        stats: Dict[str, Any] = {
            'files_discovered': len(all_files),
            'files_indexed': 0,
            'constraints_found': 0,
            'decisions_found': 0,
            'known_problems_found': 0,
            'hook_events_wired': len(structural_findings.get('hook_scripts', [])),
        }
        db_path = _get_db_path(project_dir)
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path), timeout=5)
                for tbl, key in [('files', 'files_indexed'), ('constraints', 'constraints_found'),
                                  ('decisions', 'decisions_found'), ('known_problems', 'known_problems_found')]:
                    try:
                        stats[key] = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                    except Exception:
                        pass
                conn.close()
            except Exception:
                pass
        record_first_encounter(project_dir, structural_findings, semantic_findings, stats)
        print("First encounter recorded.")
    else:
        print("First encounter already recorded.")

    print("\nRunning analysis passes...")
    summary = run_analysis(project_dir, trigger='manual')
    for lens in summary['lenses_run']:
        print(f"  [{lens}] done")

    print("\nSummary:")
    print(f"  Files discovered: {summary['files_discovered']}")
    print(f"  Lenses run: {', '.join(summary['lenses_run'])}")
    if 'semantic' in summary['results']:
        purpose = summary['results']['semantic'].get('purpose', '')
        if purpose:
            print(f"  Purpose: {purpose[:100]}")
    if 'structural' in summary['results']:
        dirs = summary['results']['structural'].get('dirs', [])
        print(f"  Top-level dirs: {', '.join(dirs[:10])}")
    print("Done.")


if __name__ == '__main__':
    main()
