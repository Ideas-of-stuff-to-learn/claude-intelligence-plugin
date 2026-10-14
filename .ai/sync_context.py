#!/usr/bin/env python3
"""
sync_context.py — Incremental sync of context/*.md into knowledge.db.
Usage: python .ai/sync_context.py [project_dir]
Only updates rows for files that changed since last index. Safe: never destroys DB.
"""
import sqlite3
import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path


def get_file_hash(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def main():
    proj = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
    db_path = Path(proj) / '.ai' / 'knowledge.db'

    if not db_path.exists():
        # Fall back to full rebuild
        rebuild = Path(proj) / '.ai' / 'rebuild_db.py'
        if rebuild.exists():
            import subprocess
            subprocess.run([sys.executable, str(rebuild), proj])
        return

    ctx_dir = Path(proj) / 'context'
    if not ctx_dir.exists():
        print("[sync_context] No context/ directory found.")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        now = datetime.now().isoformat()
        updated = 0

        for md_file in ctx_dir.glob('*.md'):
            rel = str(md_file.relative_to(proj))
            new_hash = get_file_hash(md_file)
            row = conn.execute("SELECT content_hash FROM files WHERE path=?", (rel,)).fetchone()
            if row and row[0] == new_hash:
                continue  # unchanged
            try:
                text = md_file.read_text(encoding='utf-8', errors='replace')
            except Exception:
                text = ''
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            description = lines[1] if len(lines) > 1 else (lines[0] if lines else '')
            conn.execute("""
                INSERT OR REPLACE INTO files (path, description, tags, content_hash, indexed_at, is_context_doc)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (rel, description[:500], md_file.stem, new_hash, now))
            conn.execute("""
                INSERT OR REPLACE INTO context_freshness (doc_path, last_modified, last_indexed, is_stale)
                VALUES (?, ?, ?, 0)
            """, (rel, datetime.fromtimestamp(md_file.stat().st_mtime).isoformat(), now))
            updated += 1

        conn.commit()
        conn.close()
        print(f"[sync_context] Synced {updated} changed context docs.")
    except Exception as e:
        print(f"[sync_context] warning: {e}", file=sys.stderr)


if __name__ == '__main__':
    main()
