# Claude Intelligence Plugin — Install Guide

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.sh | sh
```

Restart terminal, then in any git project:

```bash
ci install
```

Done.

---

## Verify

```bash
ci health     # should print: Intelligence system health: OK
ci dashboard  # opens http://localhost:7654
```

---

## Use with any LLM

Paste `adapters/cloud-llm/SYSTEM_PROMPT_UNIVERSAL.md` into your LLM's system prompt.
The LLM auto-detects its mode every session:

| Mode | When | How |
|------|------|-----|
| **Native** | Claude Code / Cursor / Windsurf / local folder | Hooks fire automatically — nothing to do |
| **Remote** | Repo connected (Claude.ai Projects, Copilot, etc.) | LLM creates `ci/memory/YYYY-MM-DD` branches |
| **Cloud-only** | Bare chat window, no file/repo access | Paste snapshot; LLM enforces snapshot at session end |
| **Dual** | Both local + repo | Local primary, repo branch as backup |

**Session limit hit?** A compaction snapshot is saved automatically to `context/compaction-<platform>.md`.
View snapshots: `ci snapshots` — or pass a URL to get the right one: `ci snapshots https://chatgpt.com/...`

---

## Security scans

```bash
ci pentest source .           # secrets, dangerous patterns
ci pentest web http://...     # OWASP headers, CORS, exposed paths
ci pentest docker .           # Dockerfile misconfigurations
ci pentest report             # show last scan
```

---

## Surgical testing

```bash
ci test        # runs only tests for files you changed (~1s)
ci test --all  # full suite
```

---

## Windows / WSL

**WSL:** If `ci` fails with "cannot execute", re-run the installer (it fixes CRLF).
**Windows CMD/PowerShell:**
```cmd
git clone https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin %USERPROFILE%\.claude-intel
```
Add `%USERPROFILE%\.claude-intel` to PATH, then use `ci.bat` instead of `ci`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ci: command not found` | `. ~/.bashrc` or restart terminal |
| `health: ISSUES FOUND` | `ci install` again from project root |
| Dashboard shows no data | `ci rebuild` then refresh |
| Port in use | `ci dashboard 8080` |
| Pentest: bandit not found | Pattern scan still runs; bandit auto-installs in sandbox |

---

## All commands

```bash
ci install                 # enable plugin in current project
ci health                  # check everything
ci status                  # index stats
ci dashboard               # web dashboard (port 7654)
ci dashboard 8080          # custom port
ci rebuild                 # refresh index
ci sync                    # sync context docs
ci search <term>           # search knowledge index
ci events                  # recent events
ci repos                   # list all registered repos
ci pentest source .        # security scan
ci pentest web <url>       # OWASP scan
ci pentest report          # last scan report
ci export-context          # snapshot for cloud LLM paste
ci export-context --file   # write to .ai/cloud-context.txt
ci snapshots               # list session-limit snapshots
ci snapshots <platform>    # show snapshot for that LLM (claude/chatgpt/gemini/...)
ci snapshots <url>         # detect platform from URL
ci snapshots --generate    # create snapshot now
ci test                    # surgical tests (changed files only)
ci test --all              # full test suite
ci help                    # this list
```

---

## System requirements

Python 3.8+, Git 2.20+. Linux / macOS / WSL / Windows (Git Bash or CMD).

## Uninstall

```bash
# Remove from a project
rm -rf .ai .claude/hooks context/.ai-*

# Remove ci tool entirely
rm -rf ~/.claude-intel
# Remove the PATH line from ~/.bashrc or ~/.zshrc
```
