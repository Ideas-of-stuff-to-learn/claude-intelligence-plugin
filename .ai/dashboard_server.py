#!/usr/bin/env python3 -I
"""
dashboard_server.py — Local intelligence dashboard HTTP server.
Serves on localhost:7654 by default (configurable via --port).
Usage:
  python .ai/dashboard_server.py [--port 7654] [project_dir]
"""
import sqlite3, json, os, sys, argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

_DEFAULT_PORT = 7654
_HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Intelligence Dashboard</title>
<style>
  :root{--bg:#0f1117;--surface:#1a1d27;--border:#2a2d3a;--text:#e2e8f0;--muted:#718096;
        --green:#48bb78;--yellow:#ecc94b;--red:#fc8181;--blue:#63b3ed;--accent:#7c3aed}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;line-height:1.6}
  header{background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;justify-content:space-between}
  header h1{font-size:18px;font-weight:700;color:var(--text)}
  header .badge{font-size:11px;color:var(--muted);background:var(--border);padding:3px 10px;border-radius:20px}
  .main{padding:24px;max-width:1200px;margin:0 auto}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:24px}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px}
  .card h2{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:12px}
  .stat-val{font-size:28px;font-weight:700;color:var(--text)}
  .stat-sub{font-size:12px;color:var(--muted);margin-top:4px}
  .ok{color:var(--green)} .warn{color:var(--yellow)} .err{color:var(--red)}
  table{width:100%;border-collapse:collapse}
  th{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);padding:8px 12px;text-align:left;border-bottom:1px solid var(--border)}
  td{padding:8px 12px;border-bottom:1px solid var(--border);font-size:13px}
  tr:last-child td{border-bottom:none}
  .tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600}
  .tag-ok{background:#1a3a2a;color:var(--green)} .tag-warn{background:#3a3010;color:var(--yellow)}
  .tag-err{background:#3a1010;color:var(--red)} .tag-info{background:#10203a;color:var(--blue)}
  .refresh-note{font-size:11px;color:var(--muted);text-align:right;margin-top:8px}
  .section{margin-bottom:24px}
  .section-title{font-size:14px;font-weight:700;margin-bottom:12px;color:var(--text)}
  .empty{color:var(--muted);font-size:13px;padding:16px;text-align:center}
</style>
</head>
<body>
<header>
  <h1>&#127760; Intelligence Dashboard</h1>
  <span class="badge" id="refresh-badge">Loading…</span>
</header>
<div class="main">
  <div class="grid" id="stat-cards">
    <div class="card"><h2>Health</h2><div class="stat-val" id="s-health">–</div><div class="stat-sub" id="s-health-sub"></div></div>
    <div class="card"><h2>Files Indexed</h2><div class="stat-val" id="s-files">–</div><div class="stat-sub" id="s-files-sub"></div></div>
    <div class="card"><h2>Stale Docs</h2><div class="stat-val" id="s-stale">–</div><div class="stat-sub" id="s-stale-sub"></div></div>
    <div class="card"><h2>Recent Tasks</h2><div class="stat-val" id="s-tasks">–</div><div class="stat-sub" id="s-tasks-sub"></div></div>
  </div>

  <div class="section">
    <div class="section-title">Recent Tasks</div>
    <div class="card">
      <table id="tasks-table"><thead><tr><th>Title</th><th>Status</th><th>Verification</th><th>Created</th></tr></thead>
      <tbody id="tasks-body"><tr><td colspan="4" class="empty">Loading…</td></tr></tbody></table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Event Timeline</div>
    <div class="card">
      <table id="events-table"><thead><tr><th>Time</th><th>Type</th><th>Component</th><th>Status</th></tr></thead>
      <tbody id="events-body"><tr><td colspan="4" class="empty">Loading…</td></tr></tbody></table>
    </div>
  </div>
  <div class="refresh-note" id="refresh-note"></div>
</div>
<script>
function tag(text, cls){return `<span class="tag ${cls}">${text}</span>`}
function statusTag(s){
  if(!s)return tag('–','tag-info');
  const l=s.toLowerCase();
  if(['completed','passed','ok','active'].includes(l))return tag(s,'tag-ok');
  if(['failed','error','exhausted','blocked'].includes(l))return tag(s,'tag-err');
  if(['pending','planning','queued','interrupted'].includes(l))return tag(s,'tag-warn');
  return tag(s,'tag-info');
}
function fmt(ts){if(!ts)return'–';try{return new Date(ts).toLocaleString();}catch{return ts;}}
async function fetchJSON(url){try{const r=await fetch(url);return await r.json();}catch{return null;}}

async function refresh(){
  const [status,tasks,events,health]=await Promise.all([
    fetchJSON('/api/status'),fetchJSON('/api/tasks'),
    fetchJSON('/api/events'),fetchJSON('/api/health')
  ]);

  // Health card
  if(health){
    const ok=health.ok;
    document.getElementById('s-health').innerHTML=ok?'<span class="ok">OK</span>':'<span class="warn">ISSUES</span>';
    const issues=health.issues||[];
    document.getElementById('s-health-sub').textContent=ok?'All checks pass':`${issues.length} issue(s)`;
  }

  // Stats from /api/status
  if(status){
    const ix=status.index_stats||{};
    document.getElementById('s-files').textContent=ix.files_count??'–';
    document.getElementById('s-files-sub').textContent='Last rebuild: '+(ix.last_rebuild?fmt(ix.last_rebuild):'never');
    document.getElementById('s-stale').textContent=ix.stale_docs??'–';
    document.getElementById('s-stale-sub').textContent='Context docs needing sync';
  }

  // Tasks count
  const taskList=Array.isArray(tasks)?tasks:[];
  document.getElementById('s-tasks').textContent=taskList.length;
  document.getElementById('s-tasks-sub').textContent='tasks in history';

  // Tasks table
  const tb=document.getElementById('tasks-body');
  if(taskList.length){
    tb.innerHTML=taskList.map(t=>`<tr>
      <td>${t.title||'–'}</td>
      <td>${statusTag(t.status)}</td>
      <td>${statusTag(t.verification_status||'none')}</td>
      <td>${fmt(t.created_at)}</td></tr>`).join('');
  }else{tb.innerHTML='<tr><td colspan="4" class="empty">No tasks recorded yet</td></tr>';}

  // Events table
  const evList=Array.isArray(events)?events:[];
  const eb=document.getElementById('events-body');
  if(evList.length){
    eb.innerHTML=evList.slice(0,30).map(e=>`<tr>
      <td>${fmt(e.timestamp)}</td>
      <td>${tag(e.event_type,'tag-info')}</td>
      <td>${e.component||'–'}</td>
      <td>${statusTag(e.status)}</td></tr>`).join('');
  }else{eb.innerHTML='<tr><td colspan="4" class="empty">No events recorded yet</td></tr>';}

  const now=new Date().toLocaleTimeString();
  document.getElementById('refresh-badge').textContent='Auto-refresh 30s';
  document.getElementById('refresh-note').textContent='Last updated: '+now;
}

refresh();
setInterval(refresh,30000);
</script>
</body>
</html>
"""


def _get_db_path(project_dir: str) -> Path:
    return Path(project_dir) / ".ai" / "knowledge.db"


def _open_db(project_dir: str) -> Optional[sqlite3.Connection]:
    db = _get_db_path(project_dir)
    if not db.exists():
        return None
    try:
        conn = sqlite3.connect(str(db), timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _api_status(project_dir: str) -> Dict[str, Any]:
    conn = _open_db(project_dir)
    if conn is None:
        return {"project": project_dir, "health": "no_db", "index_stats": {}, "last_rebuild": None}
    try:
        files_count = 0
        stale_docs = 0
        last_rebuild = None
        try:
            files_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        except Exception:
            pass
        try:
            stale_docs = conn.execute(
                "SELECT COUNT(*) FROM context_freshness WHERE is_stale=1"
            ).fetchone()[0]
        except Exception:
            pass
        try:
            row = conn.execute(
                "SELECT value FROM project_config WHERE key='last_full_rebuild'"
            ).fetchone()
            if row:
                last_rebuild = row[0]
        except Exception:
            pass
        return {
            "project": project_dir,
            "health": "ok",
            "index_stats": {
                "files_count": files_count,
                "stale_docs": stale_docs,
                "last_rebuild": last_rebuild,
            },
            "last_rebuild": last_rebuild,
        }
    finally:
        conn.close()


def _api_tasks(project_dir: str) -> List[Dict[str, Any]]:
    conn = _open_db(project_dir)
    if conn is None:
        return []
    try:
        try:
            rows = conn.execute(
                "SELECT id, title, status, created_at, verification_status "
                "FROM task_history ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []
    finally:
        conn.close()


def _api_events(project_dir: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = _open_db(project_dir)
    if conn is None:
        return []
    try:
        try:
            rows = conn.execute(
                "SELECT timestamp, event_type, component, status, metadata "
                "FROM events ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get("metadata"):
                    try:
                        d["metadata"] = json.loads(d["metadata"])
                    except Exception:
                        pass
                result.append(d)
            return result
        except Exception:
            return []
    finally:
        conn.close()


def _api_health(project_dir: str) -> Dict[str, Any]:
    issues: List[str] = []
    proj = Path(project_dir)
    if not _get_db_path(project_dir).exists():
        issues.append("knowledge.db missing — run rebuild")
    ctx = proj / "context"
    if not ctx.exists():
        issues.append("context/ directory missing")
    else:
        for doc in ["overview.md", "architecture.md", "handoff.md", "current-task.md"]:
            if not (ctx / doc).exists():
                issues.append(f"context/{doc} missing")
    return {"ok": len(issues) == 0, "issues": issues}


class _Handler(BaseHTTPRequestHandler):
    project_dir: str = os.getcwd()

    def log_message(self, fmt: str, *args: Any) -> None:  # type: ignore[override]
        pass  # suppress request logs

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        try:
            path = self.path.split("?")[0]
            if path == "/":
                self._send_html(_HTML_PAGE)
            elif path == "/api/status":
                self._send_json(_api_status(self.project_dir))
            elif path == "/api/tasks":
                self._send_json(_api_tasks(self.project_dir))
            elif path == "/api/events":
                self._send_json(_api_events(self.project_dir))
            elif path == "/api/health":
                self._send_json(_api_health(self.project_dir))
            elif path == "/api/projects":
                self._send_json({"projects": [self.project_dir]})
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as exc:
            try:
                self._send_json({"error": str(exc)}, 500)
            except Exception:
                pass

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()


def make_handler(project_dir: str) -> type:
    class Handler(_Handler):
        pass
    Handler.project_dir = project_dir
    return Handler


def run_server(port: int, project_dir: str) -> None:
    handler = make_handler(project_dir)
    server = HTTPServer(("127.0.0.1", port), handler)
    print(f"Intelligence Dashboard running at http://localhost:{port}")
    print(f"Project: {project_dir}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Intelligence Dashboard Server")
    parser.add_argument("project_dir", nargs="?",
                        default=os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT)
    args = parser.parse_args()
    run_server(args.port, args.project_dir)


if __name__ == "__main__":
    main()
