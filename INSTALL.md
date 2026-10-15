# Claude Intelligence Plugin

## Install (once)

**bash / zsh / fish / WSL / Git Bash / any Unix shell:**
```bash
curl -fsSL https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.sh | sh
```

**PowerShell (Windows):**
```powershell
irm https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1 | iex
```

**CMD (Windows):**
```cmd
powershell -Command "irm https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1 | iex"
```

Restart your terminal after installing.

## Enable in any project

```bash
cii
```

Same command in every terminal. Detects new vs existing automatically.

---

## Connect your LLM

Paste `adapters/cloud-llm/SYSTEM_PROMPT_UNIVERSAL.md` into your LLM once.
It auto-detects which mode it's in at the start of every session:

| Mode | Condition | What happens |
|------|-----------|--------------|
| **Native** | Local folder connected (Claude Code, Cursor, Windsurf) | Hooks fire automatically |
| **Remote** | Repo connected, no local folder | LLM uses git memory branches |
| **Cloud-only** | No folder, no repo | LLM enforces snapshot handoff each session |
| **Dual** | Both connected | Local primary, repo as backup |

---

## Verify

```bash
ci health
```

---

## Commands

```
ci install          enable in project (new or existing)
ci health           check everything
ci dashboard        web dashboard :7654
ci rebuild          refresh index
ci test             surgical tests (changed files only)
ci test --all       full suite
ci pentest source . security scan
ci pentest web URL  OWASP scan
ci snapshots        list session-limit snapshots
ci snapshots <llm>  show snapshot for claude/chatgpt/gemini/...
ci snapshots URL    detect platform from URL
ci export-context   snapshot for manual paste
ci search <term>    search knowledge index
ci sync             sync context docs
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ci: not found` | Restart terminal after install |
| `health: ISSUES` | Run `cii` again |
| No dashboard data | `ci rebuild` |
| Port in use | `ci dashboard 8080` |
| WSL: "cannot execute" | Re-run the bash installer (fixes CRLF) |
| Windows: `cii` not found | Restart terminal; PATH is set for new sessions only |

**Requirements:** Python 3.8+, Git 2.20+

**Uninstall:** `rm -rf .ai .claude/hooks` (project) · `rm -rf ~/.claude-intel` (global, Unix) · `rmdir /s %USERPROFILE%\.claude-intel` (Windows)
