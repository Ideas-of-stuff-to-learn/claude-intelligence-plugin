"""Tests for analyze_repo.py and analysis-related DB/API functions."""
import importlib.util, json, os, sys, tempfile, threading, time
from pathlib import Path
from http.server import HTTPServer

import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

PLUGIN_DIR = Path(__file__).parent.parent
ANALYZE_REPO = PLUGIN_DIR / ".ai" / "analyze_repo.py"
EVENT_LOGGER = PLUGIN_DIR / ".ai" / "event_logger.py"
DASHBOARD = PLUGIN_DIR / ".ai" / "dashboard_server.py"


def _make_project(tmp_path):
    """Create a minimal project structure for testing."""
    (tmp_path / ".ai").mkdir()
    (tmp_path / "context").mkdir()
    (tmp_path / "context" / "overview.md").write_text(
        "# Overview\n\nThis is a test project for CI.\n\n## Domains\n### Core\n"
    )
    (tmp_path / "main.py").write_text('if __name__ == "__main__":\n    pass\n')
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "session_hook.py").write_text("# hook\n")
    return tmp_path


# ── DB function tests ─────────────────────────────────────────────────────────

def test_first_encounter_recorded(tmp_path):
    proj = str(_make_project(tmp_path))
    ar = _load_module("analyze_repo", ANALYZE_REPO)
    ok = ar.record_first_encounter(proj, {"dirs": ["src"]}, {"purpose": "test"}, {"files_discovered": 10})
    assert ok is True
    enc = ar.get_first_encounter(proj)
    assert enc is not None
    assert enc["files_discovered"] == 10


def test_first_encounter_idempotent(tmp_path):
    proj = str(_make_project(tmp_path))
    ar = _load_module("analyze_repo", ANALYZE_REPO)
    ar.record_first_encounter(proj, {}, {}, {"files_discovered": 5})
    ar.record_first_encounter(proj, {}, {}, {"files_discovered": 99})
    enc = ar.get_first_encounter(proj)
    # Should still be 5 — second call is a no-op
    assert enc["files_discovered"] == 5


def test_analysis_pass_semantic(tmp_path):
    proj = str(_make_project(tmp_path))
    ar = _load_module("analyze_repo", ANALYZE_REPO)
    ok = ar.record_analysis_pass(proj, "manual", "semantic", {"purpose": "x"}, 3, 50)
    assert ok is True
    passes = ar.get_analysis_passes(proj, lens="semantic")
    assert len(passes) == 1
    assert passes[0]["lens"] == "semantic"


def test_analysis_pass_structural(tmp_path):
    proj = str(_make_project(tmp_path))
    ar = _load_module("analyze_repo", ANALYZE_REPO)
    ok = ar.record_analysis_pass(proj, "manual", "structural", {"dirs": ["src"]}, 5, 30)
    assert ok is True
    passes = ar.get_analysis_passes(proj, lens="structural")
    assert len(passes) >= 1
    assert passes[0]["lens"] == "structural"


def test_analysis_pass_exact(tmp_path):
    proj = str(_make_project(tmp_path))
    ar = _load_module("analyze_repo", ANALYZE_REPO)
    ok = ar.record_analysis_pass(proj, "hook", "exact", {"constraint_count": 0}, 0, 10)
    assert ok is True
    passes = ar.get_analysis_passes(proj, lens="exact")
    assert len(passes) >= 1
    assert passes[0]["trigger"] == "hook"


def test_get_analysis_passes_filter_by_lens(tmp_path):
    proj = str(_make_project(tmp_path))
    ar = _load_module("analyze_repo", ANALYZE_REPO)
    ar.record_analysis_pass(proj, "manual", "semantic", {}, 1, 10)
    ar.record_analysis_pass(proj, "manual", "structural", {}, 2, 20)
    ar.record_analysis_pass(proj, "manual", "exact", {}, 3, 30)
    sem = ar.get_analysis_passes(proj, lens="semantic")
    struct = ar.get_analysis_passes(proj, lens="structural")
    assert all(p["lens"] == "semantic" for p in sem)
    assert all(p["lens"] == "structural" for p in struct)


def test_analyze_repo_script_runs(tmp_path):
    import subprocess
    proj = str(_make_project(tmp_path))
    result = subprocess.run(
        [sys.executable, str(ANALYZE_REPO), proj],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Done." in result.stdout


# ── API tests via dashboard_server ───────────────────────────────────────────

def _start_server(project_dir, port=17654):
    ds = _load_module("dashboard_server", DASHBOARD)
    handler = ds.make_handler(project_dir)
    server = HTTPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    return server


def _get(port, path, timeout=5):
    import urllib.request
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as resp:
        return json.loads(resp.read())


def test_api_first_encounter_empty(tmp_path):
    proj = str(tmp_path)
    server = _start_server(proj, port=17760)
    try:
        data = _get(17760, "/api/first-encounter")
        assert data.get("exists") is False
    finally:
        server.shutdown()


def test_api_first_encounter_populated(tmp_path):
    proj = str(_make_project(tmp_path))
    ar = _load_module("analyze_repo", ANALYZE_REPO)
    ar.record_first_encounter(proj, {"dirs": ["x"]}, {"purpose": "hi"}, {"files_discovered": 7})
    server = _start_server(proj, port=17761)
    try:
        data = _get(17761, "/api/first-encounter")
        assert data.get("files_discovered") == 7
    finally:
        server.shutdown()


def test_api_analysis_empty(tmp_path):
    proj = str(tmp_path)
    server = _start_server(proj, port=17762)
    try:
        data = _get(17762, "/api/analysis")
        assert data["semantic"] == []
        assert data["structural"] == []
        assert data["exact"] == []
    finally:
        server.shutdown()


def test_api_tests_endpoint(tmp_path):
    proj = str(PLUGIN_DIR)
    server = _start_server(proj, port=17763)
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:17763/api/tests", timeout=90) as resp:
            data = json.loads(resp.read())
        assert "passed" in data
        assert "failed" in data
        assert "output" in data
        assert "ran_at" in data
    finally:
        server.shutdown()


def test_dashboard_tabs_html(tmp_path):
    import urllib.request
    proj = str(tmp_path)
    server = _start_server(proj, port=17764)
    try:
        with urllib.request.urlopen("http://127.0.0.1:17764/", timeout=5) as resp:
            html = resp.read().decode()
        assert "First Encounter" in html
        assert "Plugin Tests" in html
    finally:
        server.shutdown()
