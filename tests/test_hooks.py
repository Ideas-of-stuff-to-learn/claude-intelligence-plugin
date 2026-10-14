"""
Unit tests for hook scripts.
Run with: pytest tests/test_hooks.py -v
"""
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import date

REPO = Path(__file__).parent.parent
HOOKS = REPO / 'hooks'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_hook(script_name, stdin_payload=None, env_extra=None):
    """Run a hook script in a subprocess and return (returncode, stdout, stderr)."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    input_bytes = json.dumps(stdin_payload or {}).encode() if stdin_payload is not None else b'{}'
    result = subprocess.run(
        [sys.executable, str(HOOKS / script_name)],
        input=input_bytes,
        capture_output=True,
        env=env,
    )
    return result.returncode, result.stdout.decode(), result.stderr.decode()


# ---------------------------------------------------------------------------
# session_start.py
# ---------------------------------------------------------------------------

class TestSessionStart:
    def test_exits_zero_with_no_context_dir(self, tmp_path):
        rc, out, err = run_hook('session_start.py', env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)})
        assert rc == 0

    def test_prints_banner(self, tmp_path):
        rc, out, err = run_hook('session_start.py', env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)})
        assert 'SESSION START' in out

    def test_shows_snapshot_when_starts_with_heading(self, tmp_path):
        ctx = tmp_path / 'context'
        ctx.mkdir()
        snap = ctx / 'session-snapshot.md'
        snap.write_text('# Session Snapshot\n\nSome recovery context here.')
        rc, out, err = run_hook('session_start.py', env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)})
        assert rc == 0
        assert 'Session Snapshot' in out

    def test_does_not_show_snapshot_without_heading(self, tmp_path):
        ctx = tmp_path / 'context'
        ctx.mkdir()
        snap = ctx / 'session-snapshot.md'
        snap.write_text('Just some notes without the heading.')
        rc, out, err = run_hook('session_start.py', env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)})
        assert rc == 0
        assert 'Session Snapshot' not in out

    def test_shows_handoff_when_present(self, tmp_path):
        ctx = tmp_path / 'context'
        ctx.mkdir()
        (ctx / 'handoff.md').write_text('## What Was Just Done\n\nFixed the login bug.\n')
        rc, out, err = run_hook('session_start.py', env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)})
        assert rc == 0
        assert 'Fixed the login bug' in out


# ---------------------------------------------------------------------------
# safe_point_guard.py
# ---------------------------------------------------------------------------

class TestSafePointGuard:
    def _make_payload(self, file_path):
        return {'tool_input': {'file_path': file_path}}

    def test_exits_zero_for_context_file(self, tmp_path):
        ctx_file = str(tmp_path / 'context' / 'overview.md')
        rc, out, err = run_hook(
            'safe_point_guard.py',
            stdin_payload=self._make_payload(ctx_file),
            env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)}
        )
        assert rc == 0

    def test_blocks_source_file_without_safe_point(self, tmp_path):
        src_file = str(tmp_path / 'src' / 'main.py')
        rc, out, err = run_hook(
            'safe_point_guard.py',
            stdin_payload=self._make_payload(src_file),
            env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)}
        )
        assert rc == 2
        assert 'safe-point' in err.lower()

    def test_allows_source_file_with_valid_safe_point(self, tmp_path):
        ctx = tmp_path / 'context'
        ctx.mkdir()
        today = date.today().isoformat()
        revert = ctx / 'revert-state.md'
        revert.write_text(
            f'| Date | Status | Git Ref | Description |\n'
            f'|------|--------|---------|-------------|\n'
            f'| {today} | in-progress | abc1234 | Starting work |\n'
        )
        src_file = str(tmp_path / 'src' / 'main.py')
        rc, out, err = run_hook(
            'safe_point_guard.py',
            stdin_payload=self._make_payload(src_file),
            env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)}
        )
        assert rc == 0

    def test_does_not_match_partial_date_string(self, tmp_path):
        """Ensures old loose matching (in content) is gone — only exact table row matches."""
        ctx = tmp_path / 'context'
        ctx.mkdir()
        today = date.today().isoformat()
        revert = ctx / 'revert-state.md'
        # The word "in-progress" appears in text but NOT in a table row with today's date
        revert.write_text(
            f'This task is in-progress since {today} but not in a table.\n'
        )
        src_file = str(tmp_path / 'src' / 'main.py')
        rc, out, err = run_hook(
            'safe_point_guard.py',
            stdin_payload=self._make_payload(src_file),
            env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)}
        )
        assert rc == 2  # should block — loose matching would wrongly pass


# ---------------------------------------------------------------------------
# context_sync.py
# ---------------------------------------------------------------------------

class TestContextSync:
    def test_exits_zero_always(self, tmp_path):
        rc, out, err = run_hook(
            'context_sync.py',
            stdin_payload={'tool_input': {'file_path': str(tmp_path / 'main.py')}},
            env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)}
        )
        assert rc == 0

    def test_writes_edit_hash_file(self, tmp_path):
        """After a git repo edit, .claude/.last_edit_hash should be written."""
        # Init a git repo so git commands don't fail
        subprocess.run(['git', 'init', str(tmp_path)], capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.email', 'test@test.com'], capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.name', 'Test'], capture_output=True)
        (tmp_path / 'main.py').write_text('print("hello")')
        subprocess.run(['git', '-C', str(tmp_path), 'add', '.'], capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'commit', '-m', 'init'], capture_output=True)

        rc, out, err = run_hook(
            'context_sync.py',
            stdin_payload={'tool_input': {'file_path': str(tmp_path / 'main.py')}},
            env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)}
        )
        assert rc == 0
        hash_file = tmp_path / '.claude' / '.last_edit_hash'
        assert hash_file.exists()
        content = hash_file.read_text().strip()
        assert len(content) == 64  # sha256 hex digest


# ---------------------------------------------------------------------------
# check_handoff.py
# ---------------------------------------------------------------------------

class TestCheckHandoff:
    def test_exits_zero_when_no_edit_hash(self, tmp_path):
        rc, out, err = run_hook(
            'check_handoff.py',
            stdin_payload={},
            env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)}
        )
        assert rc == 0

    def test_exits_zero_when_stop_hook_active(self, tmp_path):
        (tmp_path / '.claude').mkdir()
        (tmp_path / '.claude' / '.last_edit_hash').write_text('abc123')
        rc, out, err = run_hook(
            'check_handoff.py',
            stdin_payload={'stop_hook_active': True},
            env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)}
        )
        assert rc == 0

    def test_blocks_when_edit_hash_exists_but_verified_missing(self, tmp_path):
        """Bug 4 fix: if .last_edit_hash exists but .last_verified does not, block."""
        subprocess.run(['git', 'init', str(tmp_path)], capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.email', 'test@test.com'], capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.name', 'Test'], capture_output=True)
        (tmp_path / 'main.py').write_text('x = 1')
        subprocess.run(['git', '-C', str(tmp_path), 'add', '.'], capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'commit', '-m', 'init'], capture_output=True)

        # Record edit hash and update handoff
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        (claude_dir / '.last_edit_hash').write_text('somehash')

        ctx = tmp_path / 'context'
        ctx.mkdir()
        # Commit handoff.md so it shows up in git diff on modification
        (ctx / 'handoff.md').write_text('original handoff')
        subprocess.run(['git', '-C', str(tmp_path), 'add', '.'], capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'commit', '-m', 'add handoff'], capture_output=True)
        # Now modify handoff and main.py so git shows both as changed
        (ctx / 'handoff.md').write_text('updated handoff')
        (tmp_path / 'main.py').write_text('x = 2')

        rc, out, err = run_hook(
            'check_handoff.py',
            stdin_payload={},
            env_extra={'CLAUDE_PROJECT_DIR': str(tmp_path)}
        )
        # Should block: handoff updated but verifier never run
        assert rc == 2
        assert 'verifier' in err.lower()
