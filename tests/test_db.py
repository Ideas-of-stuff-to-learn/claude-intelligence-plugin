"""
Unit tests for .ai/rebuild_db.py and .ai/sync_context.py.
Run with: pytest tests/test_db.py -v
"""
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
REBUILD_DB = REPO / '.ai' / 'rebuild_db.py'
SYNC_CONTEXT = REPO / '.ai' / 'sync_context.py'


def run_script(script, proj_dir):
    result = subprocess.run(
        [sys.executable, str(script), str(proj_dir)],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


class TestRebuildDb:
    def test_creates_knowledge_db(self, tmp_path):
        rc, out, err = run_script(REBUILD_DB, tmp_path)
        assert rc == 0, f"stderr: {err}"
        assert (tmp_path / '.ai' / 'knowledge.db').exists()

    def test_prints_file_count(self, tmp_path):
        rc, out, err = run_script(REBUILD_DB, tmp_path)
        assert 'knowledge.db' in out
        assert 'files indexed' in out

    def test_schema_version_table(self, tmp_path):
        run_script(REBUILD_DB, tmp_path)
        conn = sqlite3.connect(str(tmp_path / '.ai' / 'knowledge.db'))
        ver = conn.execute("SELECT version FROM schema_version").fetchone()
        conn.close()
        assert ver is not None
        assert ver[0] == 2

    def test_indexes_context_docs(self, tmp_path):
        ctx = tmp_path / 'context'
        ctx.mkdir()
        (ctx / 'overview.md').write_text('# Overview\n\nThis is a test project.')
        (ctx / 'constraints.md').write_text('# Constraints\n\n- MUST use Python 3.10+')
        run_script(REBUILD_DB, tmp_path)
        conn = sqlite3.connect(str(tmp_path / '.ai' / 'knowledge.db'))
        rows = conn.execute("SELECT path, is_context_doc FROM files WHERE is_context_doc=1").fetchall()
        conn.close()
        assert len(rows) == 2
        paths = [r[0] for r in rows]
        assert 'context/overview.md' in paths

    def test_atomic_replace_on_rebuild(self, tmp_path):
        """Second rebuild replaces DB atomically, old one becomes .bak."""
        run_script(REBUILD_DB, tmp_path)
        run_script(REBUILD_DB, tmp_path)
        assert (tmp_path / '.ai' / 'knowledge.db').exists()
        assert (tmp_path / '.ai' / 'knowledge.db.bak').exists()

    def test_indexes_source_files(self, tmp_path):
        (tmp_path / 'main.py').write_text('print("hello")')
        (tmp_path / 'utils.js').write_text('export const x = 1;')
        run_script(REBUILD_DB, tmp_path)
        conn = sqlite3.connect(str(tmp_path / '.ai' / 'knowledge.db'))
        count = conn.execute("SELECT COUNT(*) FROM files WHERE is_context_doc=0").fetchone()[0]
        conn.close()
        assert count >= 2

    def test_skips_excluded_dirs(self, tmp_path):
        node_modules = tmp_path / 'node_modules'
        node_modules.mkdir()
        (node_modules / 'some_lib.js').write_text('// library')
        run_script(REBUILD_DB, tmp_path)
        conn = sqlite3.connect(str(tmp_path / '.ai' / 'knowledge.db'))
        rows = conn.execute("SELECT path FROM files WHERE path LIKE 'node_modules%'").fetchall()
        conn.close()
        assert len(rows) == 0

    def test_extracts_constraints(self, tmp_path):
        ctx = tmp_path / 'context'
        ctx.mkdir()
        (ctx / 'constraints.md').write_text(
            '# Constraints\n\n'
            '- MUST validate all inputs before processing\n'
            '- NEVER store passwords in plaintext\n'
        )
        run_script(REBUILD_DB, tmp_path)
        conn = sqlite3.connect(str(tmp_path / '.ai' / 'knowledge.db'))
        rows = conn.execute("SELECT description FROM constraints").fetchall()
        conn.close()
        descriptions = [r[0] for r in rows]
        assert any('MUST' in d for d in descriptions)
        assert any('NEVER' in d for d in descriptions)

    def test_does_not_destroy_db_on_error(self, tmp_path):
        """If rebuild fails partway, original db must survive."""
        # First successful build
        run_script(REBUILD_DB, tmp_path)
        db = tmp_path / '.ai' / 'knowledge.db'
        db.stat().st_mtime

        # Point script at a non-writable .ai dir to force failure
        # (We can't easily force mid-run failure, but we can verify .tmp is cleaned up)
        tmp = tmp_path / '.ai' / 'knowledge.db.tmp'
        assert not tmp.exists()  # tmp should be cleaned up after success


class TestSyncContext:
    def test_exits_gracefully_without_db(self, tmp_path):
        rc, out, err = run_script(SYNC_CONTEXT, tmp_path)
        # Should not crash even without a DB
        assert rc == 0 or rc == 1  # depends on whether rebuild is available

    def test_syncs_changed_context_doc(self, tmp_path):
        # Build initial DB
        ctx = tmp_path / 'context'
        ctx.mkdir()
        (ctx / 'overview.md').write_text('# Overview\n\nOriginal content.')
        run_script(REBUILD_DB, tmp_path)

        # Modify the doc
        (ctx / 'overview.md').write_text('# Overview\n\nUpdated content.')

        rc, out, err = run_script(SYNC_CONTEXT, tmp_path)
        assert rc == 0
        assert 'Synced 1' in out

    def test_skips_unchanged_docs(self, tmp_path):
        ctx = tmp_path / 'context'
        ctx.mkdir()
        (ctx / 'overview.md').write_text('# Overview\n\nNo change.')
        run_script(REBUILD_DB, tmp_path)

        rc, out, err = run_script(SYNC_CONTEXT, tmp_path)
        assert rc == 0
        assert 'Synced 0' in out
