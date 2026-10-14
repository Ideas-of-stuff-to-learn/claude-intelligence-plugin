# Claude Intelligence Plugin

A portable, multi-platform engineering intelligence system for AI-assisted development.
Provides persistent knowledge, specialist subagents, lifecycle hooks, and verified task
workflows that survive session boundaries and work across Claude Code, OpenAI, Gemini,
Lovable, and any generic AI agent.

---

## What It Does

- **Persistent context** — a `context/` directory of structured markdown docs keeps project
  knowledge alive across sessions, compacts, and platform switches.
- **SQLite knowledge base** — `.ai/knowledge.db` indexes all context docs and source files
  for fast retrieval by agents.
- **Lifecycle hooks** — session start, safe-point guard, context sync, snapshot, and handoff
  guard fire automatically in Claude Code to keep state consistent.
- **Specialist agents** — ten pre-built agent personas cover exploration, architecture,
  testing, security, regression hunting, and more.
- **19 skills** — slash-command workflows for common engineering tasks.
- **Cross-platform adapters** — drop-in configs for OpenAI, Gemini CLI, Lovable, and
  generic agents.

---

## Quick Start

### 1. Install into a project (Claude Code)

```bash
# Copy hooks to your project's .claude/hooks/
cp hooks/*.py /your-project/.claude/hooks/
cp templates/settings.json /your-project/.claude/settings.json

# Copy .ai/ scripts
cp -r .ai/ /your-project/.ai/

# Scaffold context documents
mkdir -p /your-project/context
cp templates/context/*.md /your-project/context/

# Build the knowledge base
cd /your-project
python .ai/rebuild_db.py

# Verify the install
python .ai/intelligence_cli.py health
```

### 2. First session

Run `/project-onboard` (or `/catch-up` if context docs already exist).

---

## Components

### Hooks (`hooks/`)

| File | Event | Purpose |
|------|-------|---------|
| `session_start.py` | SessionStart | Injects handoff, active task, and snapshot into session context |
| `check_handoff.py` | Stop | Blocks session end if handoff or verification is missing |
| `safe_point_guard.py` | PreToolUse (Edit\|Write) | Blocks source edits until a safe-point is recorded for today |
| `context_sync.py` | PostToolUse (Edit\|Write) | Syncs context docs to SQLite; records working-tree fingerprint |
| `precompact_snapshot.py` | PreCompact | Writes session state to `context/session-snapshot.md` |
| `task_complete_stats.py` | PostToolUse | Records task completion metrics |

### `.ai/` Scripts

| File | Purpose |
|------|---------|
| `rebuild_db.py` | Full SQLite knowledge base rebuild (schema v2) |
| `sync_context.py` | Incremental sync of changed context docs |
| `intelligence_cli.py` | Developer CLI: `status`, `search`, `deps`, `rebuild`, `sync`, `health` |

### Skills (`skills/`)

| Skill | Purpose |
|-------|---------|
| `/audit-context` | Audit context docs for staleness |
| `/build-intelligence` | Build or rebuild the knowledge base |
| `/catch-up` | Orient a new session from context docs |
| `/debug-systematically` | Structured bug diagnosis |
| `/discuss` | Collaborative planning mode |
| `/execute` | Standard implementation workflow |
| `/execute-careful` | High-stakes implementation with extra checks |
| `/ghost-test` | Write tests before implementation |
| `/handoff` | End-of-session handoff ritual |
| `/intelligence-health` | Check and repair the intelligence system |
| `/project-onboard` | First-time project setup |
| `/realign` | Reset direction when scope drifts |
| `/recover-session` | Resume after a compact or restart |
| `/review-change` | Structured code review |
| `/safe-point` | Record a revert-safe checkpoint |
| `/ship-branch` | Branch-based shipping workflow |
| `/ship-main` | Main-branch shipping workflow |
| `/task-done` | Mark a task complete with verification |
| `/verify` | Run verification suite and record result |

### Agents (`agents/`)

| Agent | Role |
|-------|------|
| `architecture-analyst` | Structural design review and documentation |
| `context-auditor` | Detect stale or missing context docs |
| `context-curator` | Rewrite and maintain context/ quality |
| `explorer` | Codebase discovery and mapping |
| `integration-auditor` | Verify external integration correctness |
| `librarian` | Knowledge base retrieval |
| `regression-hunter` | Root-cause regression analysis |
| `security-auditor` | Vulnerability detection and audit |
| `test-architect` | Test strategy and coverage design |
| `verifier` | Verification suite orchestration |

### Context Document Templates (`templates/context/`)

Fifteen standard documents cover the full project knowledge surface:

`overview` · `architecture` · `dependencies` · `decisions` · `constraints` ·
`known-problems` · `handoff` · `current-task` · `revert-state` · `session-snapshot` ·
`test-strategy` · `api-contracts` · `environment` · `deployment` · `security`

### Cross-Platform Adapters (`adapters/`)

| Adapter | File | For |
|---------|------|-----|
| OpenAI | `openai/AGENTS.md` | ChatGPT / Assistants API |
| Gemini | `gemini/GEMINI.md` | Gemini CLI |
| Lovable | `lovable/LOVABLE_KNOWLEDGE.md` | Lovable project knowledge |
| Generic | `generic/AI_INSTRUCTIONS.md` | Any AI agent |
| Matrix | `CAPABILITY_MATRIX.md` | Platform comparison |

---

## Intelligence CLI

```bash
# Check system status
python .ai/intelligence_cli.py status

# Search the knowledge base
python .ai/intelligence_cli.py search authentication

# Find dependencies for a file
python .ai/intelligence_cli.py deps src/auth.py

# Full rebuild
python .ai/intelligence_cli.py rebuild

# Incremental sync
python .ai/intelligence_cli.py sync

# Health check
python .ai/intelligence_cli.py health
```

---

## Hook Flow

```
Session start
  └─ session_start.py fires
       reads handoff, active task, snapshot → prints to context

Before edit/write
  └─ safe_point_guard.py fires
       blocks if no in-progress row for today in context/revert-state.md

After edit/write
  └─ context_sync.py fires
       syncs context docs to SQLite, records working-tree fingerprint

Before compact
  └─ precompact_snapshot.py fires
       writes session state to context/session-snapshot.md

On session stop
  └─ check_handoff.py fires
       blocks if handoff not updated or verifier not run since last edit
```

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Capability Matrix

See [adapters/CAPABILITY_MATRIX.md](adapters/CAPABILITY_MATRIX.md) for a full
comparison of what works on each platform.

---

## License

MIT
