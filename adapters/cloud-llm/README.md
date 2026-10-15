# Cloud LLM Adapter

Use this intelligence system with any cloud LLM chat window — Claude.ai, ChatGPT, Gemini, etc.

---

## Setup (all modes)

Paste **one** file into your LLM's system prompt or project instructions:

```
adapters/cloud-llm/SYSTEM_PROMPT_UNIVERSAL.md
```

That's it. The prompt auto-detects which mode it is running in at the start of each session.

---

## How Auto-Detection Works

The LLM checks for access in this order every session:

```
1. Can I read local files?  →  Mode B (Native)   — full direct access
2. Can I access the repo?   →  Mode A (Remote)    — git branch memory
3. Neither?                 →  Mode C (Snapshot)  — clipboard workflow

If BOTH 1 and 2 succeed    →  Dual mode: local primary + repo backup
```

The LLM announces which mode it detected at the start of every session. If it gets it wrong,
tell it and it will switch.

---

## Mode B — Native (Local Folder Access)

**For:** Claude Code, Claude Desktop with folder connected, Cursor, Windsurf, etc.

- LLM reads/writes `context/*.md` directly
- Hooks fire automatically (no extra setup beyond `ci install`)
- Full `ci` commands available in terminal

**The hook confirms detection:**
```
[Mode B: Native — local file access confirmed]
  Project:  /path/to/your-project
  context/: ✓
  knowledge.db: ✓
```

**No extra configuration.** Just `ci install` in the project, then open the project in your LLM.

---

## Mode A — Remote (Repo Access)

**For:** Claude.ai Projects with GitHub connected, GPT with a repo tool, etc.

- LLM creates `ci/memory/YYYY-MM-DD` branches per session
- Reads context from `ci/memory/main` at session start
- PRs memory back to main at session end

**Optional: set up branches manually first:**
```bash
sh adapters/cloud-llm/memory_branch.sh setup   # creates ci/memory/main
sh adapters/cloud-llm/memory_branch.sh status  # list memory branches
```

**Branch naming:**
```
ci/memory/main              — long-term merged memory
ci/memory/YYYY-MM-DD        — today's session branch
ci/memory/YYYY-MM-DD-2      — second session same day
```

---

## Mode C — Cloud Only (No Access)

**For:** Bare chat windows with no file or repo access (Claude.ai, ChatGPT, etc.)

The universal prompt enforces this protocol automatically:

1. **Every session start** — LLM asks for the snapshot if not pasted
2. **You run** `ci export-context` in your terminal and paste the output
3. **LLM confirms:** `"Loaded context: [project] — last session [date]"`
4. **Every session end** — LLM outputs an updated snapshot block (no exceptions)
5. **You save** the snapshot for next session

```bash
# Generate snapshot
ci export-context

# Write to file instead
ci export-context --file    # → .ai/cloud-context.txt
```

The universal prompt enforces the session-end snapshot even if you don't ask for it —
context will not silently be lost.

---

## Dual Mode (Both Local + Repo)

If your LLM has both local folder access AND repo access (e.g. Claude Code with GitHub connected):

- **Reads/writes:** local files (faster, atomic)
- **Backup:** session context also committed to `ci/memory/YYYY-MM-DD` branch
- **Result:** local speed + full git history of every session

The universal prompt handles this automatically.

---

## Files

| File | Purpose |
|------|---------|
| `SYSTEM_PROMPT_UNIVERSAL.md` | Single prompt — paste this, covers all modes |
| `SYSTEM_PROMPT_REPO.md` | Legacy Mode A only prompt (still works) |
| `SYSTEM_PROMPT_CLOUD_ONLY.md` | Legacy Mode C only prompt (still works) |
| `memory_branch.sh` | Branch lifecycle helper for Mode A |
