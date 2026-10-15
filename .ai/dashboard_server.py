#!/usr/bin/env python3 -I
"""
dashboard_server.py — Local intelligence dashboard HTTP server.
Serves on localhost:7654 by default (configurable via --port).
Usage:
  python .ai/dashboard_server.py [--port 7654] [project_dir]
"""
import sqlite3
import json
import os
import sys
import argparse
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

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
  .tabs{background:var(--surface);border-bottom:1px solid var(--border);padding:0 24px;display:flex;gap:0}
  .tab-btn{background:none;border:none;border-bottom:2px solid transparent;color:var(--muted);cursor:pointer;font-size:13px;font-family:inherit;padding:10px 18px;transition:color .15s,border-color .15s}
  .tab-btn:hover{color:var(--text)}
  .tab-btn.active{color:var(--accent);border-bottom-color:var(--accent);font-weight:600}
  .tab-panel{display:none}.tab-panel.active{display:block}
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
  .kv{display:grid;grid-template-columns:160px 1fr;gap:6px 16px;font-size:13px;margin-bottom:12px}
  .kv .k{color:var(--muted);font-weight:600}
  .kv .v{color:var(--text)}
  .lens-section{margin-bottom:20px;border:1px solid var(--border);border-radius:8px;padding:14px}
  .lens-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);margin-bottom:10px}
  pre{background:#0a0c12;border:1px solid var(--border);border-radius:6px;padding:12px;font-family:monospace;font-size:12px;overflow-x:auto;white-space:pre-wrap;word-break:break-all;max-height:320px;overflow-y:auto}
  .run-btn{background:var(--accent);border:none;border-radius:6px;color:#fff;cursor:pointer;font-family:inherit;font-size:13px;font-weight:600;padding:8px 20px;transition:opacity .15s}
  .run-btn:hover{opacity:.85}.run-btn:disabled{opacity:.5;cursor:default}
  .result-row{display:flex;gap:16px;margin-top:12px;font-size:13px}
  .r-pass{color:var(--green);font-weight:700} .r-fail{color:var(--red);font-weight:700}
  .list-findings{list-style:none;padding:0;margin:0}
  .list-findings li{padding:3px 0;font-size:13px;color:var(--text);border-bottom:1px solid var(--border)}
  .list-findings li:last-child{border-bottom:none}
  .hint{color:var(--muted);font-size:12px;font-style:italic;padding:12px 0}
</style>
</head>
<body>
<header>
  <h1>&#127760; Intelligence Dashboard</h1>
  <span class="badge" id="refresh-badge">Loading…</span>
</header>
<nav class="tabs">
  <button class="tab-btn active" data-tab="overview" onclick="showTab('overview')">Overview</button>
  <button class="tab-btn" data-tab="first-encounter" onclick="showTab('first-encounter')">First Encounter</button>
  <button class="tab-btn" data-tab="analysis" onclick="showTab('analysis')">Analysis</button>
  <button class="tab-btn" data-tab="plugin-tests" onclick="showTab('plugin-tests')">Plugin Tests</button>
  <button class="tab-btn" data-tab="projects" onclick="showTab('projects')">Projects</button>
  <button class="tab-btn" data-tab="security" onclick="showTab('security')">Security</button>
  <button class="tab-btn" data-tab="allrepos" onclick="showTab('allrepos')">All Repos</button>
</nav>

<!-- OVERVIEW TAB -->
<div class="tab-panel active" id="tab-overview">
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
</div>

<!-- FIRST ENCOUNTER TAB -->
<div class="tab-panel" id="tab-first-encounter">
<div class="main">
  <div class="section">
    <div class="section-title">First Encounter Snapshot</div>
    <div id="fe-content"><div class="card"><div class="empty">Loading…</div></div></div>
  </div>
</div>
</div>

<!-- ANALYSIS TAB -->
<div class="tab-panel" id="tab-analysis">
<div class="main">
  <div class="section">
    <div class="section-title">Analysis Passes</div>
    <div id="analysis-content"><div class="card"><div class="empty">Loading…</div></div></div>
  </div>
</div>
</div>

<!-- PLUGIN TESTS TAB -->
<div class="tab-panel" id="tab-plugin-tests">
<div class="main">
  <div class="section">
    <div class="section-title">Plugin Tests</div>
    <div class="card">
      <button class="run-btn" id="run-tests-btn" onclick="runTests()">Run Tests</button>
      <div id="tests-result" style="margin-top:16px"></div>
    </div>
  </div>
</div>
</div>

<!-- SECURITY TAB -->
<div class="tab-panel" id="tab-security">
<div class="main">
  <div class="section">
    <div class="section-title">Security Scan Findings</div>
    <div id="security-content"><div class="card"><div class="empty">Loading…</div></div></div>
  </div>
  <div style="margin-top:12px;font-size:12px;color:var(--muted)">
    Run a scan: <code>ci pentest source .</code> &nbsp;|&nbsp; <code>ci pentest web http://localhost:3000</code>
  </div>
</div>
</div>

<!-- ALL REPOS TAB -->
<div class="tab-panel" id="tab-allrepos">
<div class="main">
  <div class="section">
    <div class="section-title">All Connected Repos</div>
    <div id="allrepos-content"><div class="card"><div class="empty">Loading…</div></div></div>
  </div>
</div>
</div>

<!-- PROJECTS TAB -->
<div class="tab-panel" id="tab-projects">
<div class="main">
  <div class="section">
    <div class="section-title">Registered Projects</div>
    <div id="projects-summary" style="margin-bottom:12px;font-size:13px;color:var(--muted)"></div>
    <div class="card" id="projects-table-wrap">
      <div class="empty">Loading…</div>
    </div>
    <div style="margin-top:16px">
      <button class="run-btn" onclick="registerCurrent()">Register current project</button>
      <span id="register-msg" style="margin-left:12px;font-size:12px;color:var(--muted)"></span>
    </div>
  </div>
</div>
</div>

<script>
function dot(ok){return`<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${ok?'var(--green)':'var(--red)'};margin-right:3px"></span>`;}

async function loadProjects(){
  const data=await fetchJSON('/api/projects');
  const list=Array.isArray(data)?data:[];
  document.getElementById('projects-summary').textContent=`${list.length} project${list.length===1?'':'s'} registered`;
  const wrap=document.getElementById('projects-table-wrap');
  if(!list.length){
    wrap.innerHTML=`<div class="hint">No projects registered yet. Run <code>python .ai/analyze_repo.py</code> in any repo using this plugin.</div>`;
    return;
  }
  let rows=list.map((p,i)=>`<tr>
    <td><strong>${p.name||'–'}</strong><br><span style="font-size:11px;color:var(--muted)">${p.path||''}</span></td>
    <td>${p.install_date||'–'}</td>
    <td>${p.last_active||'–'}</td>
    <td>${p.files_indexed??'–'}</td>
    <td>${p.events_count??'–'}</td>
    <td>${dot(p.health&&p.health.db_exists)}${dot(p.health&&p.health.hooks_wired)}${dot(p.health&&p.health.context_populated)}</td>
    <td><button class="run-btn" style="padding:4px 12px;font-size:12px" onclick="loadDetail('${encodeURIComponent(p.name)}',${i})">Details</button></td>
  </tr>
  <tr id="detail-row-${i}" style="display:none"><td colspan="7" id="detail-cell-${i}" style="padding:0"></td></tr>`).join('');
  wrap.innerHTML=`<table><thead><tr><th>Name</th><th>Install Date</th><th>Last Active</th><th>Files</th><th>Events</th><th>Health</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table>`;
}

async function loadDetail(encodedName,idx){
  const detailRow=document.getElementById(`detail-row-${idx}`);
  const cell=document.getElementById(`detail-cell-${idx}`);
  if(detailRow.style.display!=='none'){detailRow.style.display='none';return;}
  cell.innerHTML='<div style="padding:16px"><div class="hint">Loading…</div></div>';
  detailRow.style.display='';
  const data=await fetchJSON(`/api/projects/${encodedName}`);
  if(!data){cell.innerHTML='<div style="padding:16px" class="hint">Failed to load details.</div>';return;}
  const git=data.git||{};
  const activity=git.activity||[];
  const maxCount=Math.max(1,...activity.map(a=>a.count||0));
  const bars=activity.slice(-60).map(a=>{
    const h=Math.max(2,Math.round((a.count/maxCount)*60));
    return`<div title="${a.date}: ${a.count}" style="width:6px;height:${h}px;background:var(--accent);border-radius:2px 2px 0 0;flex-shrink:0"></div>`;
  }).join('');
  const actHtml=activity.length?`<div style="display:flex;align-items:flex-end;gap:2px;height:64px;overflow:hidden;margin-bottom:4px">${bars}</div><div style="font-size:11px;color:var(--muted)">Commit activity (last 90 days)</div>`:'<span class="hint">No activity data</span>';
  const touches=git.component_touches||{};
  const touchRows=Object.entries(touches).map(([k,v])=>`<tr><td>${k}</td><td>${v}</td></tr>`).join('');
  const commits=(git.recent_commits||[]).slice(0,10).map(c=>`<tr><td><code>${(c.hash||'').slice(0,7)}</code></td><td>${c.date||'–'}</td><td>${String(c.message||'').replace(/</g,'&lt;').slice(0,80)}</td></tr>`).join('');
  const events=(data.recent_events||[]).slice(0,5).map(e=>`<tr><td>${fmt(e.timestamp)}</td><td>${tag(e.event_type,'tag-info')}</td><td>${e.component||'–'}</td></tr>`).join('');
  cell.innerHTML=`<div style="padding:16px;display:grid;grid-template-columns:1fr 1fr;gap:16px">
    <div>
      <div class="section-title" style="font-size:12px">Git Activity</div>
      ${actHtml}
      <div class="section-title" style="font-size:12px;margin-top:12px">Component Touches</div>
      <table><thead><tr><th>Component</th><th>Commits</th></tr></thead><tbody>${touchRows||'<tr><td colspan="2" class="hint">–</td></tr>'}</tbody></table>
    </div>
    <div>
      <div class="section-title" style="font-size:12px">Recent Plugin Commits</div>
      <table><thead><tr><th>Hash</th><th>Date</th><th>Message</th></tr></thead><tbody>${commits||'<tr><td colspan="3" class="hint">–</td></tr>'}</tbody></table>
      <div class="section-title" style="font-size:12px;margin-top:12px">Last 5 Events</div>
      <table><thead><tr><th>Time</th><th>Type</th><th>Component</th></tr></thead><tbody>${events||'<tr><td colspan="3" class="hint">–</td></tr>'}</tbody></table>
    </div>
  </div>`;
}

async function loadSecurity(){
  const el=document.getElementById('security-content');
  const data=await fetchJSON('/api/security');
  if(!data||!data.exists){
    el.innerHTML=`<div class="card"><div class="hint">No security report yet. Run: <code>ci pentest source .</code></div></div>`;
    return;
  }
  const SEV_COLOR={'CRITICAL':'var(--red)','HIGH':'#f97316','MEDIUM':'var(--yellow)','LOW':'var(--blue)','INFO':'var(--muted)'};
  const counts=data.counts||{};
  const summary=Object.entries(counts).map(([s,n])=>`<span class="tag" style="background:${SEV_COLOR[s]||'#333'};color:#fff;margin-right:4px">${s}: ${n}</span>`).join('');
  const findings=data.findings||[];
  const rows=findings.map(f=>`<tr>
    <td><span class="tag" style="background:${SEV_COLOR[f.severity]||'#333'};color:#fff;font-size:10px">${f.severity}</span></td>
    <td>${f.category||'–'}</td>
    <td>${String(f.description||'').replace(/</g,'&lt;')}</td>
    <td><code style="font-size:11px">${String(f.evidence||'').replace(/</g,'&lt;').slice(0,80)}</code></td>
    <td style="color:var(--muted);font-size:12px">${String(f.fix||'').slice(0,60)}</td>
  </tr>`).join('');
  el.innerHTML=`<div class="card">
    <div style="margin-bottom:12px">${summary||'<span class="hint">No findings</span>'}</div>
    ${rows?`<table><thead><tr><th>Severity</th><th>Category</th><th>Description</th><th>Evidence</th><th>Fix</th></tr></thead><tbody>${rows}</tbody></table>`:'<div class="empty">No findings — scan passed ✓</div>'}
    <div class="refresh-note">Last scanned: ${data.scanned_at?new Date(data.scanned_at*1000).toLocaleString():'unknown'}</div>
  </div>`;
}

async function loadAllRepos(){
  const el=document.getElementById('allrepos-content');
  const data=await fetchJSON('/api/repos-summary');
  const projects=(data&&data.projects)||[];
  if(!projects.length){
    el.innerHTML=`<div class="card"><div class="hint">No repos registered. Run <code>ci install</code> in each project.</div></div>`;
    return;
  }
  const SEC_BADGE={'critical':'🔴','high':'🟠','medium':'🟡','ok':'🟢','none':'⚪'};
  const rows=projects.map(p=>`<tr>
    <td><strong>${p.name||'–'}</strong><br><span style="font-size:11px;color:var(--muted)">${p.path||''}</span></td>
    <td>${p.current_task?`<span style="font-size:12px">${String(p.current_task).replace(/</g,'&lt;').slice(0,80)}</span>`:'<span class="hint">–</span>'}</td>
    <td>${(p.context_docs||[]).map(d=>`<span class="tag tag-info" style="margin:1px;font-size:10px">${d}</span>`).join('')||'–'}</td>
    <td>${SEC_BADGE[p.security_status]||'⚪'} ${p.security_status||'none'}</td>
    <td>${p.last_seen?new Date(p.last_seen).toLocaleDateString():'–'}</td>
  </tr>`).join('');
  el.innerHTML=`<div class="card">
    <div style="margin-bottom:8px;color:var(--muted);font-size:12px">${projects.length} repo${projects.length===1?'':'s'} registered</div>
    <table><thead><tr><th>Repo</th><th>Current Task</th><th>Context Docs</th><th>Security</th><th>Last Seen</th></tr></thead>
    <tbody>${rows}</tbody></table>
  </div>`;
}

async function registerCurrent(){
  const msg=document.getElementById('register-msg');
  msg.textContent='Registering…';
  try{
    const r=await fetch('/api/projects/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:window.location.origin})});
    const d=await r.json();
    if(d&&d.ok){msg.style.color='var(--green)';msg.textContent='Registered!';loadProjects();}
    else{msg.style.color='var(--red)';msg.textContent=(d&&d.error)||'Failed';}
  }catch(e){msg.style.color='var(--red)';msg.textContent='Request failed';}
}
</script>

<script>
function showTab(name){
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('active',p.id==='tab-'+name));
  if(name==='first-encounter')loadFirstEncounter();
  if(name==='analysis')loadAnalysis();
  if(name==='projects')loadProjects();
  if(name==='security')loadSecurity();
  if(name==='allrepos')loadAllRepos();
}
function tag(text,cls){return`<span class="tag ${cls}">${text}</span>`}
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

function renderList(arr){
  if(!arr||!arr.length)return'<span class="hint">none</span>';
  return`<ul class="list-findings">${arr.map(x=>`<li>${String(x)}</li>`).join('')}</ul>`;
}
function renderFindings(f){
  if(!f)return'<span class="hint">no findings</span>';
  if(typeof f==='string')return`<pre>${f}</pre>`;
  let html='';
  for(const[k,v]of Object.entries(f)){
    html+=`<div style="margin-bottom:8px"><span style="color:var(--muted);font-size:11px;text-transform:uppercase;font-weight:600">${k}</span><div style="margin-top:4px">`;
    if(Array.isArray(v))html+=renderList(v);
    else if(typeof v==='object'&&v!==null)html+=`<pre>${JSON.stringify(v,null,2)}</pre>`;
    else html+=`<span style="font-size:13px">${String(v)}</span>`;
    html+='</div></div>';
  }
  return html;
}

async function loadFirstEncounter(){
  const enc=await fetchJSON('/api/first-encounter');
  const el=document.getElementById('fe-content');
  if(!enc||enc.exists===false){
    el.innerHTML=`<div class="card"><div class="hint">Run <code>python .ai/analyze_repo.py</code> to record the first encounter analysis.</div></div>`;
    return;
  }
  const ss=enc.structure_summary||{};
  const sem=enc.semantic_summary||{};
  el.innerHTML=`<div class="card">
    <div class="kv">
      <span class="k">Recorded</span><span class="v">${fmt(enc.recorded_at)}</span>
      <span class="k">Files Discovered</span><span class="v">${enc.files_discovered??'–'}</span>
      <span class="k">Files Indexed</span><span class="v">${enc.files_indexed??'–'}</span>
      <span class="k">Constraints</span><span class="v">${enc.constraints_found??'–'}</span>
      <span class="k">Decisions</span><span class="v">${enc.decisions_found??'–'}</span>
      <span class="k">Known Problems</span><span class="v">${enc.known_problems_found??'–'}</span>
      <span class="k">Hooks Wired</span><span class="v">${enc.hook_events_wired??'–'}</span>
    </div>
    <div class="lens-section">
      <div class="lens-title">Structure</div>
      <div class="kv">
        <span class="k">Dirs</span><span class="v">${(ss.dirs||[]).join(', ')||'–'}</span>
        <span class="k">Entry Points</span><span class="v">${(ss.entry_points||[]).join(', ')||'–'}</span>
        <span class="k">Test Dirs</span><span class="v">${(ss.test_dirs||[]).join(', ')||'–'}</span>
      </div>
    </div>
    <div class="lens-section">
      <div class="lens-title">Semantic</div>
      <div class="kv">
        <span class="k">Purpose</span><span class="v">${sem.purpose||'–'}</span>
        <span class="k">Domains</span><span class="v">${(sem.domains||[]).join(', ')||'–'}</span>
        <span class="k">Key Abstractions</span><span class="v">${(sem.key_abstractions||[]).join(', ')||'–'}</span>
      </div>
    </div>
  </div>`;
}

async function loadAnalysis(){
  const data=await fetchJSON('/api/analysis');
  const el=document.getElementById('analysis-content');
  if(!data){el.innerHTML='<div class="card"><div class="hint">Failed to load.</div></div>';return;}
  const hint='<div class="hint">Run <code>python .ai/analyze_repo.py</code> to record analysis passes.</div>';
  let html='';
  for(const lens of['semantic','structural','exact']){
    const passes=(data[lens]||[]);
    const pass=passes[0]||null;
    html+=`<div class="lens-section"><div class="lens-title">${lens}</div>`;
    if(!pass){html+=hint;}
    else{
      html+=`<div class="kv">
        <span class="k">Run at</span><span class="v">${fmt(pass.passed_at)}</span>
        <span class="k">Trigger</span><span class="v">${pass.trigger||'–'}</span>
        <span class="k">Files Examined</span><span class="v">${pass.files_examined??'–'}</span>
        <span class="k">Duration</span><span class="v">${pass.duration_ms??'–'} ms</span>
      </div>`;
      html+=`<div style="margin-top:8px">${renderFindings(pass.findings)}</div>`;
    }
    html+='</div>';
  }
  el.innerHTML=`<div class="card">${html}</div>`;
}

async function runTests(){
  const btn=document.getElementById('run-tests-btn');
  const el=document.getElementById('tests-result');
  btn.disabled=true;btn.textContent='Running…';
  el.innerHTML='<div class="hint">Running pytest…</div>';
  const data=await fetchJSON('/api/tests');
  btn.disabled=false;btn.textContent='Run Tests';
  if(!data){el.innerHTML='<div class="hint err">Request failed.</div>';return;}
  const passColor=data.failed>0||data.errors>0?'r-fail':'r-pass';
  el.innerHTML=`<div class="result-row">
    <span class="r-pass">&#10003; ${data.passed} passed</span>
    <span class="${data.failed>0?'r-fail':''}">&#10007; ${data.failed} failed</span>
    <span style="color:var(--muted);font-size:12px">ran at ${fmt(data.ran_at)}</span>
  </div>
  <pre>${(data.output||'').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</pre>`;
}

async function refresh(){
  const [status,tasks,events,health]=await Promise.all([
    fetchJSON('/api/status'),fetchJSON('/api/tasks'),
    fetchJSON('/api/events'),fetchJSON('/api/health')
  ]);
  if(health){
    const ok=health.ok;
    document.getElementById('s-health').innerHTML=ok?'<span class="ok">OK</span>':'<span class="warn">ISSUES</span>';
    const issues=health.issues||[];
    document.getElementById('s-health-sub').textContent=ok?'All checks pass':`${issues.length} issue(s)`;
  }
  if(status){
    const ix=status.index_stats||{};
    document.getElementById('s-files').textContent=ix.files_count??'–';
    document.getElementById('s-files-sub').textContent='Last rebuild: '+(ix.last_rebuild?fmt(ix.last_rebuild):'never');
    document.getElementById('s-stale').textContent=ix.stale_docs??'–';
    document.getElementById('s-stale-sub').textContent='Context docs needing sync';
  }
  const taskList=Array.isArray(tasks)?tasks:[];
  document.getElementById('s-tasks').textContent=taskList.length;
  document.getElementById('s-tasks-sub').textContent='tasks in history';
  const tb=document.getElementById('tasks-body');
  if(taskList.length){
    tb.innerHTML=taskList.map(t=>`<tr>
      <td>${t.title||'–'}</td>
      <td>${statusTag(t.status)}</td>
      <td>${statusTag(t.verification_status||'none')}</td>
      <td>${fmt(t.created_at)}</td></tr>`).join('');
  }else{tb.innerHTML='<tr><td colspan="4" class="empty">No tasks recorded yet</td></tr>';}
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


def _api_first_encounter(project_dir: str) -> Dict[str, Any]:
    db = _get_db_path(project_dir)
    if not db.exists():
        return {"exists": False}
    try:
        conn = _open_db(project_dir)
        if conn is None:
            return {"exists": False}
        try:
            conn.executescript("""
CREATE TABLE IF NOT EXISTS first_encounter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at TEXT NOT NULL,
    project_id TEXT,
    files_discovered INTEGER,
    files_indexed INTEGER,
    structure_summary TEXT,
    semantic_summary TEXT,
    constraints_found INTEGER,
    decisions_found INTEGER,
    known_problems_found INTEGER,
    hook_events_wired INTEGER,
    schema_version INTEGER DEFAULT 1
);
""")
            pid = str(Path(project_dir).resolve())
            row = conn.execute(
                "SELECT * FROM first_encounter WHERE project_id=? LIMIT 1", (pid,)
            ).fetchone()
            if row is None:
                return {"exists": False}
            d = dict(row)
            for key in ('structure_summary', 'semantic_summary'):
                if d.get(key):
                    try:
                        d[key] = json.loads(d[key])
                    except Exception:
                        pass
            return d
        finally:
            conn.close()
    except Exception:
        return {"exists": False}


def _api_analysis(project_dir: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"semantic": [], "structural": [], "exact": []}
    db = _get_db_path(project_dir)
    if not db.exists():
        return result
    try:
        conn = _open_db(project_dir)
        if conn is None:
            return result
        try:
            conn.executescript("""
CREATE TABLE IF NOT EXISTS analysis_passes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passed_at TEXT NOT NULL,
    project_id TEXT,
    trigger TEXT,
    lens TEXT NOT NULL,
    findings TEXT,
    files_examined INTEGER,
    duration_ms INTEGER,
    schema_version INTEGER DEFAULT 1
);
""")
            pid = str(Path(project_dir).resolve())
            for lens in ('semantic', 'structural', 'exact'):
                rows = conn.execute(
                    "SELECT * FROM analysis_passes WHERE project_id=? AND lens=? "
                    "ORDER BY passed_at DESC LIMIT 5",
                    (pid, lens)
                ).fetchall()
                passes = []
                for row in rows:
                    d = dict(row)
                    if d.get('findings'):
                        try:
                            d['findings'] = json.loads(d['findings'])
                        except Exception:
                            pass
                    passes.append(d)
                result[lens] = passes
            return result
        finally:
            conn.close()
    except Exception:
        return result


def _api_tests(project_dir: str) -> Dict[str, Any]:
    ran_at = datetime.now(timezone.utc).isoformat()
    Path(project_dir) / "tests"
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--tb=short", "-q"],
            capture_output=True, text=True,
            timeout=60, cwd=project_dir,
        )
        output = (proc.stdout + proc.stderr)[:8000]
        passed = 0
        failed = 0
        errors = 0
        for line in output.splitlines():
            import re
            m = re.search(r'(\d+) passed', line)
            if m:
                passed = int(m.group(1))
            m = re.search(r'(\d+) failed', line)
            if m:
                failed = int(m.group(1))
            m = re.search(r'(\d+) error', line)
            if m:
                errors = int(m.group(1))
        return {"passed": passed, "failed": failed, "errors": errors,
                "output": output, "ran_at": ran_at, "returncode": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"passed": 0, "failed": 0, "errors": 1,
                "output": "pytest timed out after 60s", "ran_at": ran_at, "returncode": -1}
    except Exception as e:
        return {"passed": 0, "failed": 0, "errors": 1,
                "output": str(e), "ran_at": ran_at, "returncode": -1}


def _api_projects_list() -> List[Dict[str, Any]]:
    """Return all registered projects with health snapshots."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from registry import list_projects
        from analyze_repo import get_repo_summary  # noqa: F401
    except Exception:
        return []
    result = []
    for proj in list_projects():
        path = proj.get('path', '')
        try:
            summary = get_repo_summary(path)
            proj['health'] = summary.get('health', {})
            proj['install_date'] = summary.get('install_date')
            proj['last_active'] = summary.get('last_active')
            proj['files_indexed'] = summary.get('files_indexed', 0)
            proj['events_count'] = summary.get('events_count', 0)
            proj['component_touches'] = summary.get('component_touches', {})
        except Exception:
            proj.setdefault('health', {})
            proj.setdefault('install_date', None)
            proj.setdefault('last_active', None)
            proj.setdefault('files_indexed', 0)
            proj.setdefault('events_count', 0)
            proj.setdefault('component_touches', {})
        result.append(proj)
    return result


def _api_project_detail(name: str) -> Optional[Dict[str, Any]]:
    """Return drill-down for one project by name."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from registry import list_projects
        from git_history import (get_install_date, get_last_active,
                                  get_commit_activity, get_component_touches,
                                  get_recent_commits)
        from analyze_repo import get_first_encounter, get_analysis_passes
    except Exception:
        return None
    entry = None
    for p in list_projects():
        if p.get('name') == name:
            entry = p
            break
    if entry is None:
        return None
    path = entry.get('path', '')
    git = {
        'install_date': get_install_date(path),
        'last_active': get_last_active(path),
        'recent_commits': get_recent_commits(path),
        'activity': get_commit_activity(path),
        'component_touches': get_component_touches(path),
    }
    recent_events = _api_events(path, limit=5)
    analysis_passes = {}
    try:
        for lens in ('semantic', 'structural', 'exact'):
            passes = get_analysis_passes(path, lens=lens, limit=3)
            analysis_passes[lens] = passes
    except Exception:
        pass
    return {
        'name': entry.get('name'),
        'path': path,
        'registered_at': entry.get('registered_at'),
        'last_seen': entry.get('last_seen'),
        'git': git,
        'first_encounter': get_first_encounter(path),
        'recent_events': recent_events,
        'analysis_passes': analysis_passes,
    }


def _api_projects_register(body: bytes) -> Dict[str, Any]:
    """Register a project from POST body {path: ...}."""
    try:
        data = json.loads(body.decode())
        path = data.get('path', '')
        if not path:
            return {'ok': False, 'error': 'path is required'}
        sys.path.insert(0, str(Path(__file__).parent))
        from registry import register_project
        register_project(path)
        return {'ok': True}
    except Exception as exc:
        return {'ok': False, 'error': str(exc)}


def _api_security(project_dir: str) -> Dict[str, Any]:
    """Return last pentest findings from context/security.md."""
    report = Path(project_dir) / 'context' / 'security.md'
    if not report.exists():
        return {'exists': False, 'findings': [], 'raw': ''}
    raw = report.read_text()
    # Parse findings sections
    findings = []
    current = {}
    for line in raw.splitlines():
        if line.startswith('### ['):
            if current:
                findings.append(current)
            # "[Category] Description"
            m = line[4:].strip()
            cat = m[1:m.index(']')] if ']' in m else 'Unknown'
            desc = m[m.index(']')+1:].strip() if ']' in m else m
            current = {'category': cat, 'description': desc,
                       'severity': '?', 'evidence': '', 'fix': ''}
        elif line.startswith('## ') and line[3:].strip().isupper():
            # severity heading
            sev = line[3:].strip()
            # next findings will get this severity
            if current:
                current['severity'] = sev
        elif line.startswith('**Evidence:**') and current:
            current['evidence'] = line[13:].strip().strip('`')
        elif line.startswith('**Fix:**') and current:
            current['fix'] = line[8:].strip()
    if current:
        findings.append(current)

    counts = {}
    for f in findings:
        sev = f.get('severity', '?')
        counts[sev] = counts.get(sev, 0) + 1

    return {
        'exists': True,
        'findings': findings,
        'counts': counts,
        'raw': raw[:4000],
        'scanned_at': report.stat().st_mtime,
    }


def _api_repos_summary() -> Dict[str, Any]:
    """Return a lightweight summary of all registered repos for the multi-repo panel."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from registry import list_projects
    except Exception:
        return {'projects': []}

    projects = []
    for proj in list_projects():
        path = proj.get('path', '')
        ctx = Path(path) / 'context'
        summary = {
            'name': proj.get('name', Path(path).name),
            'path': path,
            'last_seen': proj.get('last_seen', ''),
            'has_ci': bool(path and (Path(path) / '.ai').exists()),
            'context_docs': [],
            'current_task': '',
            'security_status': 'none',
        }
        # Read current task
        ct_file = ctx / 'current-task.md'
        if ct_file.exists():
            text = ct_file.read_text()
            # Extract first non-empty, non-heading line
            for line in text.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    summary['current_task'] = stripped[:100]
                    break
        # Check which context docs exist
        for doc in ['overview', 'architecture', 'handoff', 'constraints',
                    'known-problems', 'current-task', 'security']:
            if (ctx / f'{doc}.md').exists():
                summary['context_docs'].append(doc)
        # Security status
        sec = ctx / 'security.md'
        if sec.exists():
            raw = sec.read_text()
            if 'CRITICAL' in raw:
                summary['security_status'] = 'critical'
            elif 'HIGH' in raw:
                summary['security_status'] = 'high'
            elif 'MEDIUM' in raw:
                summary['security_status'] = 'medium'
            else:
                summary['security_status'] = 'ok'
        projects.append(summary)
    return {'projects': projects}


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
            elif path == "/api/first-encounter":
                self._send_json(_api_first_encounter(self.project_dir))
            elif path == "/api/analysis":
                self._send_json(_api_analysis(self.project_dir))
            elif path == "/api/tests":
                self._send_json(_api_tests(self.project_dir))
            elif path == "/api/security":
                self._send_json(_api_security(self.project_dir))
            elif path == "/api/repos-summary":
                self._send_json(_api_repos_summary())
            elif path == "/api/projects":
                self._send_json(_api_projects_list())
            elif path.startswith("/api/projects/") and path != "/api/projects/":
                proj_name = unquote(path[len("/api/projects/"):])
                detail = _api_project_detail(proj_name)
                if detail is None:
                    self.send_response(404)
                    self.end_headers()
                else:
                    self._send_json(detail)
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as exc:
            try:
                self._send_json({"error": str(exc)}, 500)
            except Exception:
                pass

    def do_POST(self) -> None:
        try:
            path = self.path.split("?")[0]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            if path == "/api/projects/register":
                self._send_json(_api_projects_register(body))
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
