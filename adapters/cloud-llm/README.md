# Cloud LLM Adapter

Use this intelligence system with any cloud LLM chat window — Claude.ai, ChatGPT, Gemini, etc. —
in three modes depending on what access the LLM has.

---

## Mode A — Repo Access (recommended)

**When to use:** The LLM has been given access to a GitHub/GitLab repo
(e.g. Claude Projects with a connected repo, GPT with a repo tool, etc.)

**How it works:**
- The LLM creates a branch `ci/memory/<date>` for each session
- Context docs are committed to that branch
- Pull requests merge memory back to main
- The intelligence system reads branches via the repo

**Setup:**
1. Connect your repo to the LLM (e.g. in Claude.ai → Projects → Add repo)
2. Copy `adapters/cloud-llm/SYSTEM_PROMPT_REPO.md` into your LLM system prompt or project instructions
3. On first use, the LLM will create the `ci/memory/` branch structure automatically

**Branch naming:**
```
ci/memory/YYYY-MM-DD/<session-id>    # session working branch
ci/memory/main                        # merged long-term memory
```

---

## Mode B — Local Folder Access

**When to use:** The LLM can read/write files on your machine
(e.g. Claude Code, Claude Desktop with a connected folder, Cursor, Windsurf, etc.)

**How it works:**
- The LLM reads `context/*.md` files directly
- Writes happen in-place (no branching needed)
- Full intelligence system available via `ci` commands

**Setup:**
1. Open your project folder in the LLM app
2. Run `ci install` in the project root (see INSTALL.md)
3. The LLM automatically reads context docs at session start (via hooks)

**No extra configuration needed** — this is the full native mode.

---

## Mode C — Cloud Only (no local/repo access)

**When to use:** Purely a chat window — no file access, no repo connected.

**How it works:**
- Paste a condensed project snapshot into the system prompt / first message
- The LLM maintains memory in the conversation thread
- You export memory at the end of the session and paste it back next time

**Setup:**
1. Run `ci export-context` in your terminal — this generates a compact text block
2. Paste the output at the start of your LLM conversation
3. At the end, ask the LLM: "export memory" to get the updated block
4. Save that block and paste it next session

**Generate a cloud context snapshot:**
```bash
ci export-context           # prints compact context for pasting
ci export-context --file    # writes to .ai/cloud-context.txt
```
