#!/usr/bin/env python3 -I
"""
event_logger.py — Telemetry event system for the intelligence engine.
Usage:
  from event_logger import log_event, query_events
  log_event("task.created", "agent", "active", metadata={"title": "..."}, project_dir="/path")
Never crashes the caller — all errors are suppressed.
"""
import sqlite3, json, os, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

VALID_EVENT_TYPES = {
    "task.created", "task.planning", "task.implementing", "task.verifying",
    "task.completed", "task.failed", "task.interrupted",
    "agent.started", "agent.completed", "agent.failed",
    "skill.started", "skill.completed",
    "hook.fired", "hook.blocked",
    "index.rebuilt", "index.synced",
    "verification.recorded",
    "session.started", "session.compacted",
    "resource.allocated", "resource.observed",
}

_TABLES_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    project_id TEXT,
    task_id TEXT,
    session_id TEXT,
    event_type TEXT NOT NULL,
    component TEXT,
    status TEXT,
    parent_id TEXT,
    metadata TEXT,
    resource_measurements TEXT,
    schema_version INTEGER DEFAULT 1,
    indexed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_project ON events(project_id);

CREATE TABLE IF NOT EXISTS task_history (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    metadata TEXT,
    verification_status TEXT,
    resource_summary TEXT
);

CREATE TABLE IF NOT EXISTS resource_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at TEXT NOT NULL,
    provider TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    value_type TEXT NOT NULL,
    amount REAL,
    unit TEXT,
    remaining REAL,
    quota_window TEXT,
    reset_at TEXT,
    freshness TEXT,
    notes TEXT,
    project_id TEXT
);
"""


def _get_db_path(project_dir: Optional[str] = None) -> Path:
    base = Path(project_dir) if project_dir else Path(
        os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    )
    return base / ".ai" / "knowledge.db"


def _open_conn(project_dir: Optional[str] = None) -> Optional[sqlite3.Connection]:
    db_path = _get_db_path(project_dir)
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.executescript(_TABLES_SQL)
        return conn
    except Exception:
        return None


def _get_project_id(project_dir: Optional[str] = None) -> str:
    base = Path(project_dir) if project_dir else Path(
        os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    )
    return str(base.resolve())


def log_event(
    event_type: str,
    component: str,
    status: str,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    resource_measurements: Optional[Dict[str, Any]] = None,
    project_dir: Optional[str] = None,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    event_id: Optional[str] = None,
) -> Optional[str]:
    """
    Log a telemetry event. Returns the event id or None on failure.
    Never raises.
    """
    try:
        eid = event_id or str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        project_id = _get_project_id(project_dir)
        meta_str = json.dumps(metadata) if metadata else None
        res_str = json.dumps(resource_measurements) if resource_measurements else None

        conn = _open_conn(project_dir)
        if conn is None:
            return None
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO events
                    (id, timestamp, project_id, task_id, session_id,
                     event_type, component, status, parent_id,
                     metadata, resource_measurements, schema_version, indexed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (eid, ts, project_id, task_id, session_id,
                 event_type, component, status, parent_id,
                 meta_str, res_str, SCHEMA_VERSION, ts),
            )
            conn.commit()
        finally:
            conn.close()
        return eid
    except Exception:
        return None


def query_events(
    project_dir: Optional[str] = None,
    limit: int = 50,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Return recent events as a list of dicts. Returns [] on any failure.
    filters keys: event_type, component, status, task_id
    """
    try:
        conn = _open_conn(project_dir)
        if conn is None:
            return []
        project_id = _get_project_id(project_dir)
        try:
            where = ["project_id = ?"]
            params: List[Any] = [project_id]
            if filters:
                for col in ("event_type", "component", "status", "task_id"):
                    if col in filters:
                        where.append(f"{col} = ?")
                        params.append(filters[col])
            sql = (
                f"SELECT * FROM events WHERE {' AND '.join(where)} "
                f"ORDER BY timestamp DESC LIMIT ?"
            )
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                for key in ("metadata", "resource_measurements"):
                    if d.get(key):
                        try:
                            d[key] = json.loads(d[key])
                        except Exception:
                            pass
                result.append(d)
            return result
        finally:
            conn.close()
    except Exception:
        return []


def ensure_tables(project_dir: Optional[str] = None) -> bool:
    """Create tables if they don't exist. Returns True on success."""
    conn = _open_conn(project_dir)
    if conn is None:
        return False
    conn.close()
    return True


if __name__ == "__main__":
    pd = sys.argv[1] if len(sys.argv) > 1 else None
    eid = log_event("session.started", "event_logger", "active", project_dir=pd)
    print(f"Logged event: {eid}")
    evs = query_events(project_dir=pd, limit=5)
    print(f"Recent events: {len(evs)}")
    for e in evs:
        print(f"  {e['timestamp']} {e['event_type']} [{e['component']}]")
