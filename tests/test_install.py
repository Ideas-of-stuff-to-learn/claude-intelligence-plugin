"""Tests for install command, version_check, and wrapper files."""
import sys
import shutil
import tempfile
from pathlib import Path

# Ensure .ai/ is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
AI_DIR = REPO_ROOT / '.ai'
sys.path.insert(0, str(AI_DIR))

from intelligence_cli import version_check, cmd_install, HOOK_FILES  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_temp_project():
    """Return a temporary directory as a project path (caller must clean up)."""
    return Path(tempfile.mkdtemp())


# ---------------------------------------------------------------------------
# version_check tests
# ---------------------------------------------------------------------------

def test_version_check_all_missing():
    """When the project has no hooks directory, all hook files are 'missing'."""
    proj = make_temp_project()
    try:
        results = version_check(str(proj), str(REPO_ROOT))
        missing = [r for r in results if r['status'] == 'missing']
        # At least the canonical hook files that exist in plugin should be missing
        hook_missing = [r for r in missing if '.claude/hooks/' in r['file']]
        assert len(hook_missing) > 0, "Expected missing hook files"
    finally:
        shutil.rmtree(str(proj))


def test_version_check_current():
    """When installed hooks match canonical, status is 'current'."""
    proj = make_temp_project()
    try:
        hooks_dst = proj / '.claude' / 'hooks'
        hooks_dst.mkdir(parents=True)
        hooks_src = REPO_ROOT / 'hooks'
        # Copy all canonical hook files verbatim
        for fname in HOOK_FILES:
            src = hooks_src / fname
            if src.exists():
                shutil.copy2(str(src), str(hooks_dst / fname))
        results = version_check(str(proj), str(REPO_ROOT))
        hook_results = [r for r in results if '.claude/hooks/' in r['file']]
        current = [r for r in hook_results if r['status'] == 'current']
        assert len(current) > 0, "Expected at least one 'current' hook"
        outdated = [r for r in hook_results if r['status'] == 'outdated']
        assert len(outdated) == 0, "No hooks should be outdated"
    finally:
        shutil.rmtree(str(proj))


def test_version_check_outdated():
    """When installed hook content differs from canonical, status is 'outdated'."""
    proj = make_temp_project()
    try:
        hooks_dst = proj / '.claude' / 'hooks'
        hooks_dst.mkdir(parents=True)
        hooks_src = REPO_ROOT / 'hooks'
        # Write a hook with modified content
        for fname in HOOK_FILES:
            src = hooks_src / fname
            if src.exists():
                (hooks_dst / fname).write_bytes(b'# modified content\n')
                break
        results = version_check(str(proj), str(REPO_ROOT))
        hook_results = [r for r in results if '.claude/hooks/' in r['file']]
        outdated = [r for r in hook_results if r['status'] == 'outdated']
        assert len(outdated) >= 1, "Expected at least one 'outdated' hook"
    finally:
        shutil.rmtree(str(proj))


def test_version_check_returns_list_of_dicts():
    """version_check always returns a list of dicts with required keys."""
    proj = make_temp_project()
    try:
        results = version_check(str(proj), str(REPO_ROOT))
        assert isinstance(results, list)
        for item in results:
            assert 'file' in item
            assert 'status' in item
            assert 'action' in item
            assert item['status'] in ('current', 'outdated', 'missing')
    finally:
        shutil.rmtree(str(proj))


def test_cmd_install_creates_hooks_dir():
    """cmd_install creates .claude/hooks/ if it does not exist."""
    proj = make_temp_project()
    try:
        cmd_install(str(proj))
        hooks_dir = proj / '.claude' / 'hooks'
        assert hooks_dir.exists(), ".claude/hooks/ should be created by install"
    finally:
        shutil.rmtree(str(proj))


def test_cmd_install_idempotent():
    """Running cmd_install twice does not raise errors."""
    proj = make_temp_project()
    try:
        cmd_install(str(proj))
        cmd_install(str(proj))  # second run — should not raise
    finally:
        shutil.rmtree(str(proj))


def test_cmd_install_copies_hook_files():
    """cmd_install copies canonical hook files that exist in the plugin."""
    proj = make_temp_project()
    try:
        cmd_install(str(proj))
        hooks_dst = proj / '.claude' / 'hooks'
        hooks_src = REPO_ROOT / 'hooks'
        copied = 0
        for fname in HOOK_FILES:
            if (hooks_src / fname).exists() and (hooks_dst / fname).exists():
                copied += 1
        assert copied > 0, "At least one hook file should be copied"
    finally:
        shutil.rmtree(str(proj))


def test_cmd_install_does_not_create_context_dir():
    """cmd_install does not create context/ when it doesn't already exist."""
    proj = make_temp_project()
    try:
        cmd_install(str(proj))
        assert not (proj / 'context').exists(), "Should not create context/ dir"
    finally:
        shutil.rmtree(str(proj))


# ---------------------------------------------------------------------------
# Wrapper file existence tests
# ---------------------------------------------------------------------------

def test_ci_wrapper_exists():
    """`ci` shell wrapper exists in the repo root."""
    ci = REPO_ROOT / 'ci'
    assert ci.exists(), "ci wrapper must exist in repo root"
    content = ci.read_text()
    assert '#!/bin/sh' in content
    assert 'intelligence_cli.py' in content


def test_ci_bat_exists():
    """`ci.bat` Windows wrapper exists in the repo root."""
    bat = REPO_ROOT / 'ci.bat'
    assert bat.exists(), "ci.bat must exist in repo root"
    content = bat.read_text()
    assert 'intelligence_cli.py' in content


def test_install_sh_exists():
    """`install.sh` exists in the repo root."""
    sh = REPO_ROOT / 'install.sh'
    assert sh.exists(), "install.sh must exist in repo root"
    content = sh.read_text()
    assert 'claude-intelligence-plugin' in content


def test_install_ps1_exists():
    """`install.ps1` exists in the repo root."""
    ps1 = REPO_ROOT / 'install.ps1'
    assert ps1.exists(), "install.ps1 must exist in repo root"
    content = ps1.read_text()
    assert 'claude-intelligence-plugin' in content


def test_install_md_exists():
    """`INSTALL.md` exists and contains the curl URL."""
    md = REPO_ROOT / 'INSTALL.md'
    assert md.exists(), "INSTALL.md must exist in repo root"
    content = md.read_text()
    assert 'curl -fsSL' in content
    assert 'install.sh' in content
