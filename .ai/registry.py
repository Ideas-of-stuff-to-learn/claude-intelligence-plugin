#!/usr/bin/env python3 -I
"""
registry.py — Global project registry for the Claude intelligence plugin.
Manages ~/.claude-intelligence/projects.json
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY_PATH = Path.home() / ".claude-intelligence" / "projects.json"


def _load() -> List[Dict[str, Any]]:
    try:
        if REGISTRY_PATH.exists():
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save(projects: List[Dict[str, Any]]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(projects, indent=2, default=str), encoding="utf-8")
    tmp.rename(REGISTRY_PATH)


def register_project(project_dir: str, project_name: Optional[str] = None) -> Dict[str, Any]:
    """Add or update an entry in the registry. Idempotent."""
    path = str(Path(project_dir).resolve())
    name = project_name or Path(path).name
    now = datetime.now(timezone.utc).isoformat()
    projects = _load()
    for entry in projects:
        if entry.get("path") == path:
            entry["last_seen"] = now
            entry["name"] = name
            _save(projects)
            return entry
    entry = {
        "path": path,
        "name": name,
        "registered_at": now,
        "last_seen": now,
    }
    projects.append(entry)
    _save(projects)
    return entry


def list_projects() -> List[Dict[str, Any]]:
    """Return list of all registered project dicts."""
    return _load()


def unregister_project(project_dir: str) -> bool:
    """Remove an entry from the registry. Returns True if removed."""
    path = str(Path(project_dir).resolve())
    projects = _load()
    before = len(projects)
    projects = [p for p in projects if p.get("path") != path]
    if len(projects) < before:
        _save(projects)
        return True
    return False


def get_project(project_dir: str) -> Optional[Dict[str, Any]]:
    """Return a single entry or None."""
    path = str(Path(project_dir).resolve())
    for entry in _load():
        if entry.get("path") == path:
            return entry
    return None
