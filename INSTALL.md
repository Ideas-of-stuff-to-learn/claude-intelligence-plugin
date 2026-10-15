# Installation Guide — Claude Intelligence Plugin

Full instructions for every platform and usage mode.

---

## Quick Start (Linux / macOS / WSL)

```bash
curl -fsSL https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.sh | sh
```

Restart your terminal, then go to any git project and run:

```bash
ci install
```

That's it. The intelligence system is now active in that project.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Install the `ci` Tool](#2-install-the-ci-tool)
   - [Linux / macOS / WSL](#linux--macos--wsl)
   - [Windows (PowerShell)](#windows-powershell)
   - [Windows (CMD)](#windows-cmd)
3. [Enable the Plugin in a Project](#3-enable-the-plugin-in-a-project)
4. [Verify Installation](#4-verify-installation)
5. [Dashboard](#5-dashboard)
6. [Security / Pentest](#6-security--pentest)
7. [Cloud LLM Integration](#7-cloud-llm-integration)
   - [Mode A: Repo Access](#mode-a-repo-access)
   - [Mode B: Local Folder Access](#mode-b-local-folder-access)
   - [Mode C: Cloud Only](#mode-c-cloud-only)
8. [WSL-specific Notes](#8-wsl-specific-notes)
9. [Troubleshooting](#9-troubleshooting)
10. [Uninstall](#10-uninstall)

---

## 1. System Requirements

| Requirement | Minimum version |
|-------------|-----------------|
| Python      | 3.8+ |
| Git         | 2.20+ |
| OS          | Linux, macOS, Windows 10+ (WSL recommended), Git Bash |

Python 3 must be on your PATH as `python3` (or `python` on Windows).
Check: `python3 --version`

---

## 2. Install the `ci` Tool

### Linux / macOS / WSL

**One-line install:**
```bash
curl -fsSL https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.sh | sh
```

**What it does:**
1. Clones the plugin to `~/.claude-intel`
2. Writes a `ci` wrapper script with correct LF line endings (no CRLF issues)
3. Adds `~/.claude-intel` to your shell's PATH in `.bashrc` / `.zshrc` / etc.

**After install:**
```bash
# Restart terminal or source your rc file:
source ~/.bashrc    # bash
source ~/.zshrc     # zsh

ci help             # verify it works
```

**Manual install (if curl fails):**
```bash
git clone https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin ~/.claude-intel
~/.claude-intel/install.sh
```

### Windows (PowerShell)

```powershell
Invoke-Expression (Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1" -UseBasicParsing).Content
```

Or manually:
```powershell
git clone https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin $env:USERPROFILE\.claude-intel
# Then add $env:USERPROFILE\.claude-intel to your PATH
```

Use `ci.bat` on Windows instead of `ci`:
```cmd
ci.bat help
```

### Windows (CMD)

```cmd
git clone https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin %USERPROFILE%\.claude-intel
```

Add `%USERPROFILE%\.claude-intel` to your system PATH manually (System Properties → Environment Variables).

Then: `ci.bat help`

---

## 3. Enable the Plugin in a Project

Navigate to any git repository and run:

```bash
cd /path/to/your-project
ci install
```

This copies hooks, `.ai/` scripts, and context templates into the project. It then rebuilds the index.

**First-time output looks like:**
```
Installing claude-intel in: /path/to/your-project
✓ Patched/added 6 hook file(s)
✓ Patched/added 8 .ai file(s)
✓ Added 16 missing context templates
✓ Created .claude/settings.json (hooks wired)
✓ Index rebuilt (83 files)
✓ Analysis complete (semantic, structural, exact)
✓ Registered in global registry

Done. Run: ci status
```

**Run this in every project you want to track.**

---

## 4. Verify Installation

```bash
ci help          # show all commands
ci status        # show index stats for current project
ci health        # check all components (hooks, context docs, DB)
ci repos         # list all registered repos (interactive navigation)
```

Expected `ci health` output when everything is OK:
```
Intelligence system health: OK
```

If you see `MISSING` entries, run `ci install` again from the project root.

---

## 5. Dashboard

The dashboard is a local web app showing your project's intelligence data:
stats, events, analysis passes, security findings, and all connected repos.

**Start it:**
```bash
ci dashboard
# or on a different port:
ci dashboard 8080
```

Then open: **http://localhost:7654** (or the port you chose).

**Dashboard tabs:**
- **Overview** — health stats, recent tasks, event timeline
- **First Encounter** — initial analysis of the project when plugin was installed
- **Analysis** — semantic / structural / exact analysis passes
- **Plugin Tests** — run the plugin's own test suite from the UI
- **Projects** — all registered repos with drill-down (git activity, events)
- **Security** — latest pentest findings (from `context/security.md`)
- **All Repos** — cross-repo view: current task, context docs, security status

**Note:** The dashboard reads your project's `context/` docs and SQLite database.
Run `ci rebuild` to refresh the index if data looks stale.

---

## 6. Security / Pentest

The plugin includes a sandboxed penetration testing tool. All scans run inside
a throwaway Python venv that is deleted after each scan. No changes are made to
your project source.

```bash
# Scan source code for secrets, dangerous patterns, vulnerable deps
ci pentest source .

# Scan a running web app (OWASP-style checks)
ci pentest web http://localhost:3000

# Check shell scripts for dangerous patterns
ci pentest cli ./scripts

# Check Dockerfile/docker-compose for misconfigurations
ci pentest docker .

# Show the last scan report
ci pentest report
```

**Results** are printed to the terminal and written to `context/security.md`.
The dashboard's Security tab also shows them.

**What it checks:**
- Hardcoded secrets (passwords, API keys, AWS credentials, private keys)
- Python code: `bandit` static analysis (if available)
- Dependencies: `safety` vulnerability check against `requirements.txt`
- Web: missing security headers, exposed paths (`.env`, `.git`), CORS, clickjacking
- Docker: root container, privileged flags, secrets in ENV, `:latest` tags

---

## 7. Cloud LLM Integration

You can use this intelligence system with cloud LLM chat windows that have
no local CLI access. Three modes are supported.

### Mode A: Repo Access

**For:** Claude.ai Projects with a connected repo, GPT with a repo tool, etc.

1. Connect your GitHub repo to the LLM (in Claude.ai → Projects → Connect repo, etc.)
2. Copy the contents of `adapters/cloud-llm/SYSTEM_PROMPT_REPO.md` into your
   project's system prompt or custom instructions
3. The LLM will create branches named `ci/memory/YYYY-MM-DD` and write context
   updates there at the end of each session

**Branch workflow:**
```bash
# Optional: set up branches manually first
sh adapters/cloud-llm/memory_branch.sh setup
```

The LLM handles the rest. After each session it commits to the memory branch.

### Mode B: Local Folder Access

**For:** Claude Code CLI, Claude Desktop with a connected folder, Cursor, Windsurf, etc.

This is the full native mode. No extra setup beyond `ci install`.

The hooks (`session_start.py`, etc.) fire automatically when your LLM begins
a session. Context docs are read and written directly.

**When you type a prompt into your LLM**, the hooks:
1. Load `context/overview.md`, `context/handoff.md`, `context/current-task.md`
2. Feed them into the LLM's context
3. After the session, write updates back to the context files

**The dashboard** updates automatically each session. Run `ci rebuild` to refresh.

### Mode C: Cloud Only (no local or repo access)

**For:** Bare chat windows (Claude.ai, ChatGPT, etc.) with no file access.

1. In your terminal, generate a context snapshot:
   ```bash
   ci export-context
   ```
2. Copy the output block (between `=== CI CONTEXT SNAPSHOT ===` and `=== END ===`)
3. Paste it at the start of your LLM conversation
4. Optionally, paste `adapters/cloud-llm/SYSTEM_PROMPT_CLOUD_ONLY.md` as your
   system prompt so the LLM knows what to do with it

**At the end of each session:**
- Ask the LLM: "generate a context snapshot"
- It will output an updated `=== CI CONTEXT SNAPSHOT ===` block
- Save that block (copy to a file or your notes)
- Paste it next session

**To save a snapshot to a file:**
```bash
ci export-context --file
# writes to .ai/cloud-context.txt
```

---

## 8. WSL-specific Notes

**Problem:** `ci help` gives "cannot execute: required file not found"

**Cause:** Windows git with `core.autocrlf=true` writes CRLF line endings to the
`ci` wrapper file. Linux/WSL can't execute scripts with `\r` in the shebang line.

**Fix 1 (permanent):** Re-run the installer — it rewrites `ci` with guaranteed LF:
```bash
curl -fsSL https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.sh | sh
```

**Fix 2 (immediate, without re-installing):**
```bash
printf '#!/bin/sh\nPLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"\nif command -v python3 >/dev/null 2>&1; then\n    exec python3 "$PLUGIN_DIR/.ai/intelligence_cli.py" "$@"\nelse\n    exec python "$PLUGIN_DIR/.ai/intelligence_cli.py" "$@"\nfi\n' > ~/.claude-intel/ci
chmod +x ~/.claude-intel/ci
ci help
```

**Problem:** `python3` not found

WSL may only have `python3` (not `python`). The `ci` wrapper already handles
this — it tries `python3` first. If that also fails:
```bash
which python3     # confirm python3 is on PATH
sudo apt install python3  # install if missing
```

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| `ci: command not found` | Run `. ~/.bashrc` or restart terminal; confirm `~/.claude-intel` is on PATH |
| `knowledge.db not found` | Run `ci install` or `ci rebuild` in project root |
| `ci install` says "no .git found" | You must be inside a git repository (`git init` if needed) |
| Dashboard shows no data | Run `ci rebuild` then refresh the browser |
| Hook not firing | Check `.claude/settings.json` exists; run `ci health` |
| Dashboard port in use | `ci dashboard 8080` to use a different port |
| Pentest: `bandit not found` | Run the scan anyway — the pattern-based scan still works; `bandit` auto-installs in its sandbox |

**Check all issues:**
```bash
ci health
```

**Run tests surgically (only tests for files you changed):**
```bash
ci test         # maps changed files → relevant tests, runs only those
ci test --all   # full suite
```

**Re-run everything from scratch:**
```bash
ci install    # re-copies files, creates context/, settings.json, and rebuilds
ci rebuild    # rebuild the SQLite index only
ci sync       # sync context docs into index only
```

---

## 10. Uninstall

**Remove from a project:**
```bash
cd /path/to/project
rm -rf .ai .claude/hooks context/.ai-*
```

**Remove the `ci` tool entirely:**
```bash
rm -rf ~/.claude-intel
# Then remove the PATH line from ~/.bashrc or ~/.zshrc
```

---

## Where Does `ci install` Actually Run?

**Always in a normal terminal** — not inside the LLM chat window.

| Step | Where to run |
|------|-------------|
| `ci install` (install tool) | Your terminal (bash, zsh, PowerShell, CMD, WSL) |
| `ci install` (enable in project) | Your terminal, inside the project directory |
| `ci dashboard` | Your terminal — opens browser dashboard |
| `ci pentest source .` | Your terminal — runs the scan |
| Typing a prompt into Claude/GPT | Inside the LLM chat or Claude Code session |

**Does typing a prompt update the dashboard?**

Yes — when you work with Claude Code (the CLI tool) or any LLM with Mode B
(local folder access), the hooks automatically:
1. Load context at session start
2. Log events during the session
3. Update `context/handoff.md` and `context/current-task.md` at session end

The dashboard reads these in real time. Refresh the browser to see updates.
Run `ci rebuild` if you want the full index refreshed.

---

## Quick Command Reference

```bash
ci help                    # show all commands
ci install                 # enable plugin in current project
ci status                  # index stats
ci health                  # component health check
ci repos                   # list all repos (interactive nav)
ci dashboard               # start web dashboard (port 7654)
ci dashboard 8080          # use custom port
ci pentest source .        # security scan — source code
ci pentest web <url>       # security scan — web app
ci pentest report          # show last scan
ci search <term>           # search knowledge index
ci events                  # recent telemetry events
ci budget "task desc"      # estimate resource cost
ci rebuild                 # rebuild SQLite index
ci sync                    # sync context docs
ci export-context          # generate cloud LLM snapshot
ci export-context --file   # write snapshot to .ai/cloud-context.txt
ci test                    # surgical tests — only tests for recently changed files
ci test --all              # run full test suite
```
