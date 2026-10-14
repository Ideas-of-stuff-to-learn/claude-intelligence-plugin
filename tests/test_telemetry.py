"""
tests/test_telemetry.py — Tests for event_logger, budget_manager, dashboard_server.
Requires: Python stdlib only, pytest.
"""
import json, os, sys, sqlite3, tempfile, threading, time, urllib.request
from pathlib import Path

# Ensure .ai/ is importable
_AI_DIR = Path(__file__).parent.parent / ".ai"
sys.path.insert(0, str(_AI_DIR))

import event_logger
import budget_manager
import dashboard_server


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _make_proj(tmp_path: Path) -> Path:
    """Create a minimal project directory with .ai/ subdir."""
    ai = tmp_path / ".ai"
    ai.mkdir(parents=True, exist_ok=True)
    return tmp_path


def _proj_str(tmp_path: Path) -> str:
    return str(tmp_path)


# ──────────────────────────────────────────────────────────────
# event_logger tests
# ──────────────────────────────────────────────────────────────

def test_event_logger_log_event_writes_to_db(tmp_path):
    proj = _make_proj(tmp_path)
    eid = event_logger.log_event(
        "task.created", "test_component", "active",
        metadata={"title": "test task"},
        project_dir=_proj_str(proj),
    )
    assert eid is not None
    db = proj / ".ai" / "knowledge.db"
    assert db.exists()
    conn = sqlite3.connect(str(db))
    row = conn.execute("SELECT * FROM events WHERE id = ?", (eid,)).fetchone()
    conn.close()
    assert row is not None
    assert row[5] == "task.created"  # event_type column


def test_event_logger_query_events_retrieves(tmp_path):
    proj = _make_proj(tmp_path)
    for etype in ["task.created", "task.planning", "task.completed"]:
        event_logger.log_event(etype, "test", "ok", project_dir=_proj_str(proj))
    events = event_logger.query_events(project_dir=_proj_str(proj), limit=10)
    assert len(events) == 3
    types = {e["event_type"] for e in events}
    assert "task.created" in types
    assert "task.completed" in types


def test_event_logger_dedup_by_id(tmp_path):
    proj = _make_proj(tmp_path)
    eid = "fixed-event-id-dedup"
    r1 = event_logger.log_event(
        "hook.fired", "test", "active",
        event_id=eid, project_dir=_proj_str(proj),
    )
    r2 = event_logger.log_event(
        "hook.fired", "test", "active",
        event_id=eid, project_dir=_proj_str(proj),
    )
    assert r1 == eid
    assert r2 == eid  # INSERT OR IGNORE — second call also returns same id
    events = event_logger.query_events(project_dir=_proj_str(proj))
    hook_events = [e for e in events if e["event_type"] == "hook.fired"]
    assert len(hook_events) == 1  # only one row


def test_event_logger_query_with_filter(tmp_path):
    proj = _make_proj(tmp_path)
    event_logger.log_event("agent.started", "explorer", "active", project_dir=_proj_str(proj))
    event_logger.log_event("skill.started", "verifier", "active", project_dir=_proj_str(proj))
    events = event_logger.query_events(
        project_dir=_proj_str(proj),
        filters={"event_type": "agent.started"},
    )
    assert len(events) == 1
    assert events[0]["event_type"] == "agent.started"


def test_event_logger_metadata_stored_and_retrieved(tmp_path):
    proj = _make_proj(tmp_path)
    meta = {"files_changed": ["foo.py", "bar.py"], "count": 2}
    eid = event_logger.log_event(
        "task.completed", "cli", "done",
        metadata=meta, project_dir=_proj_str(proj),
    )
    events = event_logger.query_events(project_dir=_proj_str(proj))
    ev = next((e for e in events if e["id"] == eid), None)
    assert ev is not None
    assert isinstance(ev["metadata"], dict)
    assert ev["metadata"]["count"] == 2


def test_event_logger_tables_created(tmp_path):
    proj = _make_proj(tmp_path)
    ok = event_logger.ensure_tables(project_dir=_proj_str(proj))
    assert ok is True
    db = proj / ".ai" / "knowledge.db"
    conn = sqlite3.connect(str(db))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "events" in tables
    assert "task_history" in tables
    assert "resource_observations" in tables


def test_event_logger_fails_open_on_bad_path(tmp_path):
    # Should not raise even with a bad project_dir
    result = event_logger.log_event(
        "session.started", "test", "active",
        project_dir="/nonexistent/__bad__/path",
    )
    # May return None or a uuid depending on whether dir creation succeeded
    # The key requirement is: no exception raised


def test_event_logger_query_empty_db_returns_list(tmp_path):
    proj = _make_proj(tmp_path)
    event_logger.ensure_tables(project_dir=_proj_str(proj))
    events = event_logger.query_events(project_dir=_proj_str(proj))
    assert isinstance(events, list)
    assert len(events) == 0


# ──────────────────────────────────────────────────────────────
# budget_manager tests
# ──────────────────────────────────────────────────────────────

def test_budget_create(tmp_path):
    proj = _make_proj(tmp_path)
    bid = budget_manager.create_budget(
        "task-abc", 100, 10, 5, project_dir=_proj_str(proj)
    )
    assert bid is not None
    status = budget_manager.get_status(bid, project_dir=_proj_str(proj))
    assert status is not None
    assert status["task_id"] == "task-abc"
    assert status["total_tool_calls"] == 100
    assert status["status"] == "active"


def test_budget_allocate(tmp_path):
    proj = _make_proj(tmp_path)
    bid = budget_manager.create_budget("task-alloc", 200, 20, 10, project_dir=_proj_str(proj))
    ok = budget_manager.allocate(bid, "explorer", {"tool_calls": 50, "agent_calls": 5}, project_dir=_proj_str(proj))
    assert ok is True


def test_budget_consume_updates_used(tmp_path):
    proj = _make_proj(tmp_path)
    bid = budget_manager.create_budget("task-consume", 100, 10, 5, project_dir=_proj_str(proj))
    budget_manager.consume(bid, "cli", {"tool_calls": 30, "agent_calls": 2}, project_dir=_proj_str(proj))
    status = budget_manager.get_status(bid, project_dir=_proj_str(proj))
    assert status["used_tool_calls"] == 30
    assert status["used_agent_calls"] == 2
    assert abs(status["tool_calls_utilization"] - 0.30) < 0.01


def test_budget_exhaust(tmp_path):
    proj = _make_proj(tmp_path)
    bid = budget_manager.create_budget("task-exhaust", 10, 2, 2, project_dir=_proj_str(proj))
    budget_manager.consume(bid, "cli", {"tool_calls": 11}, project_dir=_proj_str(proj))
    status = budget_manager.get_status(bid, project_dir=_proj_str(proj))
    assert status["status"] == "exhausted"


def test_adapt_strategy_continue(tmp_path):
    status = {"tool_calls_utilization": 0.5, "agent_calls_utilization": 0.3, "index_ops_utilization": 0.2}
    rec = budget_manager.adapt_strategy(status)
    assert rec.action == "continue_as_is"


def test_adapt_strategy_reduce_parallelism(tmp_path):
    status = {"tool_calls_utilization": 0.80, "agent_calls_utilization": 0.3, "index_ops_utilization": 0.2}
    rec = budget_manager.adapt_strategy(status)
    assert rec.action == "reduce_parallelism"


def test_adapt_strategy_checkpoint(tmp_path):
    status = {"tool_calls_utilization": 1.10, "agent_calls_utilization": 0.3, "index_ops_utilization": 0.2}
    rec = budget_manager.adapt_strategy(status)
    assert rec.action == "checkpoint_and_stop"


def test_preflight_estimate_returns_estimate(tmp_path):
    proj = _make_proj(tmp_path)
    est = budget_manager.preflight_estimate("fix a typo in README", "low", _proj_str(proj))
    assert est.estimated_tool_calls > 0
    assert est.confidence in ("low", "medium", "high")
    assert "provider" in est.notes.lower() or len(est.notes) > 0


# ──────────────────────────────────────────────────────────────
# dashboard_server tests
# ──────────────────────────────────────────────────────────────

def _start_server(port: int, project_dir: str) -> threading.Thread:
    handler = dashboard_server.make_handler(project_dir)
    server = dashboard_server.HTTPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    return t


def test_dashboard_api_status_returns_json(tmp_path):
    proj = _make_proj(tmp_path)
    # Build a minimal DB so the API has something to read
    event_logger.ensure_tables(project_dir=_proj_str(proj))
    port = 17654
    _start_server(port, _proj_str(proj))
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5)
    data = json.loads(resp.read())
    assert "health" in data
    assert "index_stats" in data


def test_dashboard_api_health_returns_ok_field(tmp_path):
    proj = _make_proj(tmp_path)
    event_logger.ensure_tables(project_dir=_proj_str(proj))
    port = 17655
    _start_server(port, _proj_str(proj))
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5)
    data = json.loads(resp.read())
    assert "ok" in data
    assert isinstance(data["ok"], bool)
    assert "issues" in data


def test_dashboard_api_events_returns_list(tmp_path):
    proj = _make_proj(tmp_path)
    event_logger.log_event("session.started", "test", "active", project_dir=_proj_str(proj))
    port = 17656
    _start_server(port, _proj_str(proj))
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/events", timeout=5)
    data = json.loads(resp.read())
    assert isinstance(data, list)


def test_dashboard_graceful_missing_db(tmp_path):
    # No DB created — should return empty data, not crash
    proj = _make_proj(tmp_path)
    port = 17657
    _start_server(port, _proj_str(proj))
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5)
    data = json.loads(resp.read())
    assert "health" in data  # returns something, not 500


def test_dashboard_html_page_served(tmp_path):
    proj = _make_proj(tmp_path)
    port = 17658
    _start_server(port, _proj_str(proj))
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5)
    html = resp.read().decode()
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()
    assert "Intelligence Dashboard" in html


def test_dashboard_api_tasks_returns_list(tmp_path):
    proj = _make_proj(tmp_path)
    event_logger.ensure_tables(project_dir=_proj_str(proj))
    port = 17659
    _start_server(port, _proj_str(proj))
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/tasks", timeout=5)
    data = json.loads(resp.read())
    assert isinstance(data, list)
