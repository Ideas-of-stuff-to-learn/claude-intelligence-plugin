"""
Unit tests for .ai/intelligence_cli.py.
Run with: pytest tests/test_cli.py -v
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
CLI = REPO / '.ai' / 'intelligence_cli.py'
REBUILD_DB = REPO / '.ai' / 'rebuild_db.py'


def run_cli(args, proj_dir=None, env_extra=None):
    import os
    env = os.environ.copy()
    if proj_dir:
        env['CLAUDE_PROJECT_DIR'] = str(proj_dir)
        # Ensure the temp dir looks like a git repo so the not-in-repo guard passes
        git_dir = Path(proj_dir) / '.git'
        if not git_dir.exists():
            git_dir.mkdir()
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        [sys.executable, str(CLI)] + args,
        capture_output=True, text=True, env=env
    )
    return result.returncode, result.stdout, result.stderr


class TestCliStatus:
    def test_errors_without_db(self, tmp_path):
        rc, out, err = run_cli(['status'], proj_dir=tmp_path)
        assert rc != 0
        assert 'ERROR' in out

    def test_shows_status_after_rebuild(self, tmp_path):
        subprocess.run([sys.executable, str(REBUILD_DB), str(tmp_path)], capture_output=True)
        rc, out, err = run_cli(['status'], proj_dir=tmp_path)
        assert rc == 0
        assert 'Schema version' in out
        assert 'Files indexed' in out


class TestCliSearch:
    def test_search_finds_file(self, tmp_path):
        ctx = tmp_path / 'context'
        ctx.mkdir()
        (ctx / 'overview.md').write_text('# Overview\n\nThis is a Python project.')
        subprocess.run([sys.executable, str(REBUILD_DB), str(tmp_path)], capture_output=True)
        rc, out, err = run_cli(['search', 'overview'], proj_dir=tmp_path)
        assert rc == 0
        assert 'context/overview.md' in out

    def test_search_no_results(self, tmp_path):
        subprocess.run([sys.executable, str(REBUILD_DB), str(tmp_path)], capture_output=True)
        rc, out, err = run_cli(['search', 'xyzzy_nonexistent_term_99'], proj_dir=tmp_path)
        assert rc == 0
        assert 'No results' in out


class TestCliHealth:
    def test_reports_missing_context(self, tmp_path):
        rc, out, err = run_cli(['health'], proj_dir=tmp_path)
        assert 'MISSING' in out

    def test_reports_ok_with_full_setup(self, tmp_path):
        # Build DB
        subprocess.run([sys.executable, str(REBUILD_DB), str(tmp_path)], capture_output=True)

        # Create all 8 required context docs
        ctx = tmp_path / 'context'
        ctx.mkdir(exist_ok=True)
        for doc in ['overview.md', 'architecture.md', 'dependencies.md', 'decisions.md',
                    'constraints.md', 'known-problems.md', 'handoff.md', 'current-task.md']:
            (ctx / doc).write_text(f'# {doc}\n\nContent.')

        # Create settings.json with all hooks
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir(exist_ok=True)
        import json
        settings = {
            "hooks": {
                "SessionStart": [],
                "Stop": [],
                "PreToolUse": [],
                "PostToolUse": [],
                "PreCompact": []
            }
        }
        (claude_dir / 'settings.json').write_text(json.dumps(settings))

        # Copy the .ai scripts into the tmp project so health check finds them
        import shutil
        (tmp_path / '.ai').mkdir(exist_ok=True)
        shutil.copy(REBUILD_DB, tmp_path / '.ai' / 'rebuild_db.py')
        shutil.copy(REPO / '.ai' / 'sync_context.py', tmp_path / '.ai' / 'sync_context.py')

        rc, out, err = run_cli(['health'], proj_dir=tmp_path)
        # After full setup the only remaining issues should be missing context docs
        # that aren't in our 8-doc subset; the main structural issues should be gone.
        # Check that the critical structural issues are not reported.
        assert 'MISSING: .ai/knowledge.db' not in out
        assert 'MISSING: .ai/rebuild_db.py' not in out
        assert 'MISSING: .claude/settings.json' not in out


class TestCliUnknownCommand:
    def test_unknown_command_exits_nonzero(self, tmp_path):
        rc, out, err = run_cli(['blorp'], proj_dir=tmp_path)
        assert rc != 0

    def test_no_args_exits_zero_and_shows_help(self, tmp_path):
        rc, out, err = run_cli([], proj_dir=tmp_path)
        assert rc == 0
        assert 'USAGE' in out or 'COMMANDS' in out
