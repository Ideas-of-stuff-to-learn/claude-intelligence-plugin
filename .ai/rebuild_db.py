#!/usr/bin/env python3
"""
rebuild_db.py — Full SQLite knowledge base builder.
Usage: python .ai/rebuild_db.py [project_dir]
Builds .ai/knowledge.db from scratch with versioned schema.
Safe: never destroys the last valid DB on failure.
"""
import sqlite3, os, sys, json, hashlib, re
from datetime import datetime
from pathlib import Path

SCHEMA_VERSION = 2
EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', 'dist', 'build', '.expo', 'venv', '.venv', '.ai'}
CONTEXT_EXTENSIONS = {'.md', '.txt', '.json', '.yaml', '.yml'}


def get_file_hash(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            description TEXT,
            tags TEXT,
            content_hash TEXT,
            indexed_at TEXT NOT NULL,
            file_size INTEGER,
            is_context_doc INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS dependencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            relationship TEXT NOT NULL,
            target TEXT NOT NULL,
            evidence TEXT,
            indexed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS constraints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            severity TEXT DEFAULT 'high',
            source_file TEXT,
            indexed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            rationale TEXT,
            alternatives TEXT,
            source_file TEXT,
            indexed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS known_problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            source_file TEXT,
            indexed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS context_freshness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_path TEXT NOT NULL UNIQUE,
            last_modified TEXT,
            last_indexed TEXT,
            is_stale INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS project_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS verification_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_fingerprint TEXT NOT NULL,
            status TEXT NOT NULL,
            checks_run TEXT,
            recorded_at TEXT NOT NULL,
            project_id TEXT
        );
        CREATE TABLE IF NOT EXISTS sync_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
            path, description, tags, content=files, content_rowid=id
        );
        CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
        CREATE INDEX IF NOT EXISTS idx_deps_source ON dependencies(source);
        CREATE INDEX IF NOT EXISTS idx_deps_target ON dependencies(target);
        CREATE INDEX IF NOT EXISTS idx_constraints_severity ON constraints(severity);
    """)


def index_context_docs(conn, proj):
    ctx_dir = Path(proj) / 'context'
    if not ctx_dir.exists():
        return
    now = datetime.now().isoformat()
    for md_file in ctx_dir.glob('*.md'):
        rel = str(md_file.relative_to(proj))
        content_hash = get_file_hash(md_file)
        try:
            text = md_file.read_text(encoding='utf-8', errors='replace')
        except Exception:
            text = ''
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        description = lines[1] if len(lines) > 1 else lines[0] if lines else ''
        tags = md_file.stem
        conn.execute("""
            INSERT OR REPLACE INTO files (path, description, tags, content_hash, indexed_at, is_context_doc)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (rel, description[:500], tags, content_hash, now))
        conn.execute("""
            INSERT OR REPLACE INTO context_freshness (doc_path, last_modified, last_indexed)
            VALUES (?, ?, ?)
        """, (rel, datetime.fromtimestamp(md_file.stat().st_mtime).isoformat(), now))


def index_source_files(conn, proj):
    now = datetime.now().isoformat()
    for root, dirs, files in os.walk(proj):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            rel = str(fpath.relative_to(proj))
            if rel.startswith('context/'):
                continue
            ext = fpath.suffix.lower()
            if ext not in {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java',
                           '.rb', '.php', '.sql', '.sh', '.json', '.yaml', '.yml',
                           '.md', '.toml'}:
                continue
            try:
                size = fpath.stat().st_size
                if size > 500_000:
                    continue
                content_hash = get_file_hash(fpath)
            except Exception:
                continue
            conn.execute("""
                INSERT OR IGNORE INTO files (path, description, tags, content_hash, indexed_at, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (rel, f'{ext[1:]} file', ext[1:], content_hash, now, size))


def parse_constraints_from_context(conn, proj):
    """Extract hard constraints from context/constraints.md"""
    cfile = Path(proj) / 'context' / 'constraints.md'
    if not cfile.exists():
        return
    now = datetime.now().isoformat()
    text = cfile.read_text(encoding='utf-8', errors='replace')
    for line in text.splitlines():
        stripped = line.strip().lstrip('-*• ').strip()
        if len(stripped) > 20 and any(w in stripped.upper() for w in
                                       ('MUST', 'NEVER', 'ALWAYS', 'REQUIRED', 'FORBIDDEN')):
            conn.execute("""
                INSERT INTO constraints (description, severity, source_file, indexed_at)
                VALUES (?, 'high', 'context/constraints.md', ?)
            """, (stripped[:500], now))


def set_project_config(conn, proj):
    cfg_path = Path(proj) / '.ai' / 'system-config.json'
    now = datetime.now().isoformat()
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            for k, v in cfg.items():
                conn.execute("INSERT OR REPLACE INTO project_config VALUES (?, ?, ?)",
                             (k, str(v), now))
        except Exception:
            pass
    conn.execute("INSERT OR REPLACE INTO project_config VALUES (?, ?, ?)",
                 ('last_full_rebuild', now, now))


def main():
    proj = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
    ai_dir = Path(proj) / '.ai'
    ai_dir.mkdir(exist_ok=True)

    db_path = ai_dir / 'knowledge.db'
    tmp_path = ai_dir / 'knowledge.db.tmp'

    if tmp_path.exists():
        tmp_path.unlink()

    try:
        conn = sqlite3.connect(str(tmp_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        init_db(conn)
        conn.execute("INSERT OR REPLACE INTO schema_version VALUES (?, ?)",
                     (SCHEMA_VERSION, datetime.now().isoformat()))

        index_context_docs(conn, proj)
        index_source_files(conn, proj)
        parse_constraints_from_context(conn, proj)
        set_project_config(conn, proj)

        conn.commit()
        conn.close()

        if db_path.exists():
            db_path.rename(ai_dir / 'knowledge.db.bak')
        tmp_path.rename(db_path)

        conn2 = sqlite3.connect(str(db_path))
        (file_count,) = conn2.execute("SELECT COUNT(*) FROM files").fetchone()
        conn2.close()
        print(f"[rebuild_db] Built knowledge.db: {file_count} files indexed. Schema v{SCHEMA_VERSION}.")
        sys.exit(0)
    except Exception as e:
        print(f"[rebuild_db] ERROR: {e}", file=sys.stderr)
        if tmp_path.exists():
            tmp_path.unlink()
        sys.exit(1)


if __name__ == '__main__':
    main()
