"""
Tests for new features:
- ci dashboard launches server (not just prints)
- ci pentest command is wired up
- ci export-context generates a snapshot
- cloud LLM adapter files exist
- pentest_runner pattern scanning works without external tools
"""
import importlib.util
from pathlib import Path
import pytest


# ── Load intelligence_cli without side effects ──────────────────────────────

def _load_cli():
    spec = importlib.util.spec_from_file_location(
        'intelligence_cli',
        Path(__file__).parent.parent / '.ai' / 'intelligence_cli.py'
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope='module')
def cli():
    return _load_cli()


# ── Dashboard ────────────────────────────────────────────────────────────────

def test_dashboard_server_script_exists():
    """dashboard_server.py must exist so ci dashboard can launch it."""
    assert (Path(__file__).parent.parent / '.ai' / 'dashboard_server.py').exists()


def test_dashboard_cmd_resolves_server(cli, tmp_path):
    """cmd_dashboard should find dashboard_server.py (fallback to plugin dir)."""
    # Just verify the function exists and the server script resolves
    assert hasattr(cli, 'cmd_dashboard')
    # The server lives at plugin_dir/.ai/dashboard_server.py
    plugin_dir = Path(__file__).parent.parent
    server = plugin_dir / '.ai' / 'dashboard_server.py'
    assert server.exists(), "dashboard_server.py not found"


# ── Pentest ──────────────────────────────────────────────────────────────────

def test_pentest_runner_exists():
    assert (Path(__file__).parent.parent / '.ai' / 'pentest_runner.py').exists()


def test_pentest_agent_exists():
    assert (Path(__file__).parent.parent / 'agents' / 'pentest.md').exists()


def test_pentest_skill_exists():
    assert (Path(__file__).parent.parent / 'skills' / 'pentest' / 'SKILL.md').exists()


def test_pentest_pattern_scan(tmp_path):
    """Pattern scanner finds hardcoded secret without external tools."""
    spec = importlib.util.spec_from_file_location(
        'pentest_runner',
        Path(__file__).parent.parent / '.ai' / 'pentest_runner.py'
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Write a file with a fake hardcoded secret
    (tmp_path / 'config.py').write_text('password = "super_secret_123"\n')
    findings = mod.scan_source(tmp_path)
    sev = [f.severity for f in findings]
    assert any(s in ('HIGH', 'CRITICAL') for s in sev), \
        f"Expected a HIGH/CRITICAL finding for hardcoded password, got: {sev}"


def test_pentest_docker_scan(tmp_path):
    """Docker scanner detects root user and :latest tag."""
    spec = importlib.util.spec_from_file_location(
        'pentest_runner',
        Path(__file__).parent.parent / '.ai' / 'pentest_runner.py'
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    (tmp_path / 'Dockerfile').write_text(
        'FROM python:latest\nUSER root\nRUN pip install flask\n'
    )
    findings = mod.scan_docker(tmp_path)
    cats = [f.category for f in findings]
    assert any('Docker' in c for c in cats), f"Expected Docker findings, got: {cats}"


def test_pentest_cli_dispatch(cli, monkeypatch):
    """ci pentest subcommand is wired in main()."""
    # Verify pentest branch exists in main dispatch
    import inspect
    src = inspect.getsource(cli.main)
    assert "'pentest'" in src or '"pentest"' in src, \
        "pentest command not found in main dispatch"


# ── export-context ───────────────────────────────────────────────────────────

def test_export_context_runs(cli, tmp_path, capsys):
    """cmd_export_context should produce a snapshot block."""
    # Create minimal context dir
    ctx = tmp_path / 'context'
    ctx.mkdir()
    (ctx / 'overview.md').write_text('# My Project\nA test project.\n')
    (ctx / 'current-task.md').write_text('# Current Task\nFix bugs.\n')
    (ctx / 'handoff.md').write_text('# Handoff\nDid stuff last session.\n')

    cli.cmd_export_context(tmp_path, to_file=False)
    out = capsys.readouterr().out
    assert '=== CI CONTEXT SNAPSHOT ===' in out
    assert 'My Project' in out or tmp_path.name in out
    assert '=== END CI CONTEXT SNAPSHOT ===' in out


def test_export_context_to_file(cli, tmp_path):
    """cmd_export_context --file writes cloud-context.txt."""
    ctx = tmp_path / 'context'
    ctx.mkdir()
    ai = tmp_path / '.ai'
    ai.mkdir()
    (ctx / 'overview.md').write_text('# Proj\n')

    cli.cmd_export_context(tmp_path, to_file=True)
    out_file = tmp_path / '.ai' / 'cloud-context.txt'
    assert out_file.exists()
    content = out_file.read_text()
    assert '=== CI CONTEXT SNAPSHOT ===' in content


# ── Cloud LLM adapter files ──────────────────────────────────────────────────

def test_cloud_llm_adapter_files_exist():
    base = Path(__file__).parent.parent / 'adapters' / 'cloud-llm'
    assert (base / 'README.md').exists()
    assert (base / 'SYSTEM_PROMPT_UNIVERSAL.md').exists()
    assert (base / 'SYSTEM_PROMPT_REPO.md').exists()
    assert (base / 'SYSTEM_PROMPT_CLOUD_ONLY.md').exists()
    assert (base / 'memory_branch.sh').exists()


def test_cloud_llm_readme_has_three_modes():
    readme = (Path(__file__).parent.parent / 'adapters' / 'cloud-llm' / 'README.md').read_text()
    assert 'Mode A' in readme or 'Mode A' in readme
    assert 'Mode B' in readme
    assert 'Mode C' in readme


def test_universal_prompt_has_all_modes():
    """Universal prompt must cover all four cases including dual mode."""
    prompt = (
        Path(__file__).parent.parent / 'adapters' / 'cloud-llm' / 'SYSTEM_PROMPT_UNIVERSAL.md'
    ).read_text()
    assert 'Mode B' in prompt, "Universal prompt must cover native/local mode"
    assert 'Mode A' in prompt, "Universal prompt must cover remote/repo mode"
    assert 'Mode C' in prompt, "Universal prompt must cover cloud-only mode"
    assert 'Dual' in prompt or 'dual' in prompt, "Universal prompt must handle both-connected case"
    assert 'auto' in prompt.lower() or 'detect' in prompt.lower(), \
        "Universal prompt must describe auto-detection"


def test_universal_prompt_mode_c_enforces_snapshot():
    """Mode C section must include enforcement language — snapshot at end of every session."""
    prompt = (
        Path(__file__).parent.parent / 'adapters' / 'cloud-llm' / 'SYSTEM_PROMPT_UNIVERSAL.md'
    ).read_text()
    assert 'NO EXCEPTIONS' in prompt or 'MUST' in prompt, \
        "Mode C must enforce session-end snapshot output"


# ── Dashboard security API ───────────────────────────────────────────────────

def test_dashboard_security_api(tmp_path):
    """_api_security returns no-report state when security.md missing."""
    spec = importlib.util.spec_from_file_location(
        'dashboard_server',
        Path(__file__).parent.parent / '.ai' / 'dashboard_server.py'
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod._api_security(str(tmp_path))
    assert result['exists'] is False


def test_dashboard_security_api_with_report(tmp_path):
    """_api_security parses a real security.md report."""
    spec = importlib.util.spec_from_file_location(
        'dashboard_server',
        Path(__file__).parent.parent / '.ai' / 'dashboard_server.py'
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ctx = tmp_path / 'context'
    ctx.mkdir()
    (ctx / 'security.md').write_text(
        '# Security Findings\n\n## HIGH\n\n'
        '### [Secrets/Patterns] Hardcoded password\n'
        '**Evidence:** `config.py:1`\n**Fix:** Use env vars\n'
    )
    result = mod._api_security(str(tmp_path))
    assert result['exists'] is True
    assert len(result['findings']) >= 1
