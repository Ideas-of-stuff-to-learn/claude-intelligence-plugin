#!/usr/bin/env python3 -I
"""
budget_manager.py — Task-local usage budget manager.

Tracks tool calls, agent calls, and index operations per task.
DOES NOT track provider subscription limits — those are not available
through the shared intelligence engine without authorised API integration.
Provider usage information must be obtained through each provider's own
authenticated API; this module stores only local budget observations.

Usage:
  from budget_manager import create_budget, allocate, consume, get_status, preflight_estimate
"""
import sqlite3
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, NamedTuple

_TABLES_SQL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS budgets (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    created_at TEXT NOT NULL,
    total_tool_calls INTEGER,
    total_agent_calls INTEGER,
    total_index_ops INTEGER,
    used_tool_calls INTEGER DEFAULT 0,
    used_agent_calls INTEGER DEFAULT 0,
    used_index_ops INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    project_id TEXT
);

CREATE TABLE IF NOT EXISTS budget_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_id TEXT NOT NULL,
    component TEXT NOT NULL,
    allocated_tool_calls INTEGER DEFAULT 0,
    allocated_agent_calls INTEGER DEFAULT 0,
    allocated_index_ops INTEGER DEFAULT 0,
    allocated_at TEXT NOT NULL
);
"""

_STRATEGY_THRESHOLDS = {
    "continue_as_is": 0.70,
    "reduce_parallelism": 0.85,
    "defer_optionals": 0.95,
    "checkpoint_and_stop": 1.01,
}


class BudgetEstimate(NamedTuple):
    estimated_tool_calls: int
    estimated_agent_calls: int
    estimated_index_ops: int
    confidence: str  # 'low' / 'medium' / 'high'
    notes: str


class StrategyRecommendation(NamedTuple):
    action: str  # continue_as_is / reduce_parallelism / defer_optionals / checkpoint_and_stop
    reason: str
    utilization: float


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


def _project_id(project_dir: Optional[str] = None) -> str:
    base = Path(project_dir) if project_dir else Path(
        os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    )
    return str(base.resolve())


def create_budget(
    task_id: str,
    total_tool_calls: int = 200,
    total_agent_calls: int = 20,
    total_index_ops: int = 10,
    project_dir: Optional[str] = None,
) -> Optional[str]:
    """
    Create a new task-local budget. Returns budget_id or None on failure.
    NOTE: This tracks local operation budgets only, not provider API quotas.
    """
    try:
        bid = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        pid = _project_id(project_dir)
        conn = _open_conn(project_dir)
        if conn is None:
            return None
        try:
            conn.execute(
                """INSERT INTO budgets
                   (id, task_id, created_at, total_tool_calls, total_agent_calls,
                    total_index_ops, used_tool_calls, used_agent_calls,
                    used_index_ops, status, project_id)
                   VALUES (?,?,?,?,?,?,0,0,0,'active',?)""",
                (bid, task_id, ts, total_tool_calls, total_agent_calls,
                 total_index_ops, pid),
            )
            conn.commit()
        finally:
            conn.close()
        return bid
    except Exception:
        return None


def allocate(
    budget_id: str,
    component: str,
    amounts: Dict[str, int],
    project_dir: Optional[str] = None,
) -> bool:
    """
    Record a budget allocation for a component.
    amounts keys: tool_calls, agent_calls, index_ops
    Returns True on success.
    """
    try:
        ts = datetime.now(timezone.utc).isoformat()
        conn = _open_conn(project_dir)
        if conn is None:
            return False
        try:
            conn.execute(
                """INSERT INTO budget_allocations
                   (budget_id, component, allocated_tool_calls,
                    allocated_agent_calls, allocated_index_ops, allocated_at)
                   VALUES (?,?,?,?,?,?)""",
                (budget_id, component,
                 amounts.get("tool_calls", 0),
                 amounts.get("agent_calls", 0),
                 amounts.get("index_ops", 0),
                 ts),
            )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception:
        return False


def consume(
    budget_id: str,
    component: str,
    amounts: Dict[str, int],
    project_dir: Optional[str] = None,
) -> bool:
    """
    Record actual consumption against the budget.
    amounts keys: tool_calls, agent_calls, index_ops
    Returns True on success.
    """
    try:
        conn = _open_conn(project_dir)
        if conn is None:
            return False
        try:
            conn.execute(
                """UPDATE budgets SET
                   used_tool_calls = used_tool_calls + ?,
                   used_agent_calls = used_agent_calls + ?,
                   used_index_ops = used_index_ops + ?
                   WHERE id = ?""",
                (amounts.get("tool_calls", 0),
                 amounts.get("agent_calls", 0),
                 amounts.get("index_ops", 0),
                 budget_id),
            )
            # Mark exhausted if any dimension exceeded
            row = conn.execute(
                "SELECT * FROM budgets WHERE id = ?", (budget_id,)
            ).fetchone()
            if row:
                tc = row["total_tool_calls"] or 0
                ac = row["total_agent_calls"] or 0
                io = row["total_index_ops"] or 0
                if (tc and row["used_tool_calls"] >= tc) or \
                   (ac and row["used_agent_calls"] >= ac) or \
                   (io and row["used_index_ops"] >= io):
                    conn.execute(
                        "UPDATE budgets SET status = 'exhausted' WHERE id = ?",
                        (budget_id,),
                    )
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception:
        return False


def get_status(
    budget_id: str,
    project_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return budget status dict or None if not found."""
    try:
        conn = _open_conn(project_dir)
        if conn is None:
            return None
        try:
            row = conn.execute(
                "SELECT * FROM budgets WHERE id = ?", (budget_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            # Compute utilisation ratios
            for key, total_key, used_key in [
                ("tool_calls", "total_tool_calls", "used_tool_calls"),
                ("agent_calls", "total_agent_calls", "used_agent_calls"),
                ("index_ops", "total_index_ops", "used_index_ops"),
            ]:
                total = d.get(total_key) or 0
                used = d.get(used_key) or 0
                d[f"{key}_utilization"] = (used / total) if total else 0.0
            return d
        finally:
            conn.close()
    except Exception:
        return None


def preflight_estimate(
    task_description: str,
    complexity: str = "medium",
    project_dir: Optional[str] = None,
) -> BudgetEstimate:
    """
    Heuristic budget estimate for a described task.
    complexity: 'low' / 'medium' / 'high'
    Returns a BudgetEstimate. Never raises.
    """
    try:
        desc_lower = task_description.lower()
        words = len(task_description.split())

        # Heuristic multipliers
        mult = {"low": 0.5, "medium": 1.0, "high": 2.5}.get(complexity, 1.0)
        high_signals = ["refactor", "migrate", "all", "entire", "full", "rewrite",
                        "comprehensive", "complete", "every"]
        low_signals = ["fix", "typo", "rename", "update version", "bump"]
        if any(s in desc_lower for s in high_signals):
            mult *= 1.8
        if any(s in desc_lower for s in low_signals):
            mult *= 0.4

        base_tools = max(20, min(words * 3, 300))
        base_agents = max(2, min(words // 10, 30))
        base_index = max(1, min(words // 20, 10))

        est_tools = int(base_tools * mult)
        est_agents = int(base_agents * mult)
        est_index = int(base_index * mult)

        if mult <= 0.6:
            confidence = "high"
        elif mult <= 1.5:
            confidence = "medium"
        else:
            confidence = "low"

        notes = (
            f"Heuristic estimate (complexity={complexity}). "
            "Provider usage information is not available through the shared "
            "intelligence engine without authorised API integration — this "
            "estimate covers local tool_calls, agent_calls, and index_ops only."
        )
        return BudgetEstimate(est_tools, est_agents, est_index, confidence, notes)
    except Exception as exc:
        return BudgetEstimate(100, 10, 5, "low", f"Estimation failed: {exc}")


def adapt_strategy(budget_status: Dict[str, Any]) -> StrategyRecommendation:
    """
    Given a budget status dict from get_status(), recommend a strategy.
    Never raises.
    """
    try:
        utils = [
            budget_status.get("tool_calls_utilization", 0.0),
            budget_status.get("agent_calls_utilization", 0.0),
            budget_status.get("index_ops_utilization", 0.0),
        ]
        max_util = max(utils) if utils else 0.0

        if max_util < _STRATEGY_THRESHOLDS["continue_as_is"]:
            return StrategyRecommendation(
                "continue_as_is",
                f"Budget utilization at {max_util:.0%} — within safe range",
                max_util,
            )
        if max_util < _STRATEGY_THRESHOLDS["reduce_parallelism"]:
            return StrategyRecommendation(
                "reduce_parallelism",
                f"Budget utilization at {max_util:.0%} — reduce parallel agents",
                max_util,
            )
        if max_util < _STRATEGY_THRESHOLDS["defer_optionals"]:
            return StrategyRecommendation(
                "defer_optionals",
                f"Budget utilization at {max_util:.0%} — defer non-critical work",
                max_util,
            )
        return StrategyRecommendation(
            "checkpoint_and_stop",
            f"Budget utilization at {max_util:.0%} — checkpoint and stop",
            max_util,
        )
    except Exception as exc:
        return StrategyRecommendation("continue_as_is", f"Strategy error: {exc}", 0.0)


if __name__ == "__main__":
    pd = sys.argv[1] if len(sys.argv) > 1 else None
    est = preflight_estimate("refactor the entire authentication system", "high", pd)
    print(f"Estimate: tools={est.estimated_tool_calls}, agents={est.estimated_agent_calls}, "
          f"index={est.estimated_index_ops}, confidence={est.confidence}")
    bid = create_budget("test-task-1", 100, 10, 5, pd)
    print(f"Created budget: {bid}")
    consume(bid, "cli", {"tool_calls": 30}, pd)
    status = get_status(bid, pd)
    rec = adapt_strategy(status)
    print(f"Strategy: {rec.action} ({rec.reason})")


# ---------------------------------------------------------------------------
# Real token usage from Claude Code's ~/.claude/projects/ JSONL transcripts
# ---------------------------------------------------------------------------

def _claude_projects_dir() -> Path:
    return Path.home() / '.claude' / 'projects'


def read_session_usage(session_id: str = None) -> Dict[str, Any]:
    """
    Read actual token usage from Claude Code JSONL transcripts.
    Deduplicates by requestId (last event wins, matching cctrack behaviour).
    Returns aggregated totals for one session, or all sessions if None.
    """
    projects_dir = _claude_projects_dir()
    if not projects_dir.exists():
        return {}

    totals: Dict[str, int] = {
        'input_tokens': 0,
        'output_tokens': 0,
        'cache_creation_input_tokens': 0,
        'cache_read_input_tokens': 0,
        'thinking_tokens': 0,
        'turns': 0,
    }
    seen: Dict[str, dict] = {}  # requestId -> usage dict

    import json as _json
    jsonl_files = list(projects_dir.glob('**/*.jsonl'))

    for jf in jsonl_files:
        # Filter to specific session if requested
        if session_id and session_id not in jf.name:
            continue
        try:
            with open(jf, encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = _json.loads(line)
                    except Exception:
                        continue
                    if d.get('type') != 'assistant':
                        continue
                    msg = d.get('message', {})
                    if not isinstance(msg, dict):
                        continue
                    usage = msg.get('usage')
                    if not isinstance(usage, dict):
                        continue
                    rid = d.get('uuid') or d.get('requestId') or id(d)
                    seen[str(rid)] = usage
        except Exception:
            pass

    for usage in seen.values():
        totals['input_tokens'] += usage.get('input_tokens', 0)
        totals['output_tokens'] += usage.get('output_tokens', 0)
        totals['cache_creation_input_tokens'] += usage.get('cache_creation_input_tokens', 0)
        totals['cache_read_input_tokens'] += usage.get('cache_read_input_tokens', 0)
        totals['thinking_tokens'] += (
            usage.get('output_tokens_details', {}).get('thinking_tokens', 0)
        )
        totals['turns'] += 1

    return totals


# Anthropic list prices (USD per million tokens) — update as needed
_PRICES = {
    'claude-sonnet-4-6': {'input': 3.0,  'output': 15.0, 'cache_read': 0.30, 'cache_write': 3.75},
    'claude-opus-5-5':   {'input': 15.0, 'output': 75.0, 'cache_read': 1.50, 'cache_write': 18.75},
    'claude-haiku-5-5':  {'input': 0.80, 'output': 4.0,  'cache_read': 0.08, 'cache_write': 1.0},
    'default':           {'input': 3.0,  'output': 15.0, 'cache_read': 0.30, 'cache_write': 3.75},
}


def estimate_cost(usage: Dict[str, Any], model: str = 'default') -> Dict[str, float]:
    """
    Estimate USD cost from a usage dict returned by read_session_usage().
    Uses list prices — actual cost may differ (Max plan, discounts, etc.).
    """
    prices = _PRICES.get(model, _PRICES['default'])
    M = 1_000_000
    cost = {
        'input':       usage.get('input_tokens', 0) / M * prices['input'],
        'output':      usage.get('output_tokens', 0) / M * prices['output'],
        'cache_read':  usage.get('cache_read_input_tokens', 0) / M * prices['cache_read'],
        'cache_write': usage.get('cache_creation_input_tokens', 0) / M * prices['cache_write'],
    }
    cost['total'] = sum(cost.values())
    return cost
