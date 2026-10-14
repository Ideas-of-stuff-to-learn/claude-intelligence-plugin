"""Tests for registry.py and git_history.py."""
import json
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

import pytest

# Ensure .ai/ is on path
sys.path.insert(0, str(Path(__file__).parent.parent / ".ai"))

import registry as reg_module
from registry import (
    register_project, list_projects, unregister_project, get_project,
)


@pytest.fixture(autouse=True)
def tmp_registry(tmp_path, monkeypatch):
    """Redirect REGISTRY_PATH to a temp location for every test."""
    fake_path = tmp_path / "ci" / "projects.json"
    monkeypatch.setattr(reg_module, "REGISTRY_PATH", fake_path)
    yield fake_path


# --- registry tests ---

def test_register_project_creates_file(tmp_path):
    register_project(str(tmp_path))
    assert reg_module.REGISTRY_PATH.exists()


def test_register_idempotent(tmp_path):
    register_project(str(tmp_path))
    register_project(str(tmp_path))
    assert len(list_projects()) == 1


def test_register_updates_last_seen(tmp_path):
    e1 = register_project(str(tmp_path))
    time.sleep(0.01)
    e2 = register_project(str(tmp_path))
    assert e2["last_seen"] >= e1["last_seen"]


def test_list_projects_empty():
    assert list_projects() == []


def test_unregister_removes_entry(tmp_path):
    register_project(str(tmp_path))
    assert len(list_projects()) == 1
    unregister_project(str(tmp_path))
    assert len(list_projects()) == 0


def test_get_project_found(tmp_path):
    register_project(str(tmp_path), project_name="myrepo")
    entry = get_project(str(tmp_path))
    assert entry is not None
    assert entry["name"] == "myrepo"


def test_get_project_not_found(tmp_path):
    assert get_project(str(tmp_path)) is None


def test_register_entry_shape(tmp_path):
    entry = register_project(str(tmp_path), project_name="testproj")
    assert "path" in entry
    assert "name" in entry
    assert "registered_at" in entry
    assert "last_seen" in entry
    assert entry["name"] == "testproj"


def test_register_multiple_projects(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    register_project(str(a))
    register_project(str(b))
    assert len(list_projects()) == 2


# --- git_history tests ---

def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(path), capture_output=True)


def test_git_history_not_a_repo(tmp_path):
    from git_history import (
        get_install_date, get_commit_activity, get_component_touches,
        get_recent_commits, get_last_active,
    )
    d = str(tmp_path / "notarepo")
    Path(d).mkdir()
    assert get_install_date(d) is None
    assert get_commit_activity(d) == []
    assert isinstance(get_component_touches(d), dict)
    assert get_recent_commits(d) == []
    assert get_last_active(d) is None


def test_git_history_get_commit_activity_returns_list(tmp_path):
    from git_history import get_commit_activity
    _init_git_repo(tmp_path)
    result = get_commit_activity(str(tmp_path))
    assert isinstance(result, list)


def test_git_history_get_component_touches_returns_dict(tmp_path):
    from git_history import get_component_touches
    _init_git_repo(tmp_path)
    result = get_component_touches(str(tmp_path))
    assert isinstance(result, dict)
    assert "context" in result
    assert "hooks" in result


def test_git_history_get_recent_commits_returns_list(tmp_path):
    from git_history import get_recent_commits
    _init_git_repo(tmp_path)
    result = get_recent_commits(str(tmp_path))
    assert isinstance(result, list)


def test_git_history_get_last_active_returns_none_or_str(tmp_path):
    from git_history import get_last_active
    _init_git_repo(tmp_path)
    result = get_last_active(str(tmp_path))
    assert result is None or isinstance(result, str)


# --- API tests ---

def _make_server(project_dir):
    """Create a test HTTP handler instance."""
    import dashboard_server as ds
    handler_class = ds.make_handler(project_dir)
    return handler_class, ds


def _get_response(project_dir, path):
    import dashboard_server as ds

    class FakeSocket:
        def makefile(self, mode):
            return BytesIO()

    class FakeWFile:
        def __init__(self):
            self.data = b""
        def write(self, b):
            self.data += b

    class TestHandler(ds.make_handler(project_dir)):
        def __init__(self):
            self.path = path
            self.headers = {}
            self.wfile = FakeWFile()
            self._response_started = False
            self._status = None
            self._headers_sent = []

        def send_response(self, code):
            self._status = code

        def send_header(self, k, v):
            self._headers_sent.append((k, v))

        def end_headers(self):
            pass

        def log_message(self, fmt, *args):
            pass

    h = TestHandler()
    h.do_GET()
    body = h.wfile.data
    try:
        return h._status, json.loads(body)
    except Exception:
        return h._status, body


def test_api_projects_empty(tmp_path):
    status, data = _get_response(str(tmp_path), "/api/projects")
    assert status == 200
    assert isinstance(data, list)


def test_api_projects_register_post(tmp_path):
    import dashboard_server as ds

    class FakeWFile:
        def __init__(self): self.data = b""
        def write(self, b): self.data += b

    body_bytes = json.dumps({"path": str(tmp_path)}).encode()

    class TestHandler(ds.make_handler(str(tmp_path))):
        def __init__(self):
            self.path = "/api/projects/register"
            self.headers = {"Content-Length": str(len(body_bytes))}
            self.rfile = BytesIO(body_bytes)
            self.wfile = FakeWFile()
            self._status = None

        def send_response(self, code): self._status = code
        def send_header(self, k, v): pass
        def end_headers(self): pass
        def log_message(self, fmt, *args): pass

    h = TestHandler()
    h.do_POST()
    result = json.loads(h.wfile.data)
    assert result.get("ok") is True
    assert get_project(str(tmp_path)) is not None


def test_api_projects_drill_down(tmp_path):
    register_project(str(tmp_path), project_name="testproject")
    status, data = _get_response(str(tmp_path), "/api/projects/testproject")
    assert status == 200
    assert "name" in data
    assert "git" in data
    assert "recent_events" in data
    assert "analysis_passes" in data


def test_projects_tab_in_html(tmp_path):
    status, data = _get_response(str(tmp_path), "/")
    # data will be bytes here since it's HTML
    if isinstance(data, bytes):
        html = data.decode()
    else:
        html = str(data)
    assert "Projects" in html
