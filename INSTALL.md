# Claude Intelligence Plugin

## Install (once)

**bash / zsh / fish / WSL / Git Bash:**
```bash
curl -fsSL https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.sh | sh
```

**PowerShell:**
```powershell
irm https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1 | iex
```

**CMD:**
```cmd
powershell -Command "irm https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1 | iex"
```

> **Blocked?** See [Firewall / Corporate Network](#firewall--corporate-network) at the bottom.

Restart terminal, then in any project:
```bash
cii
```

---

## Connect your LLM

Paste `adapters/cloud-llm/SYSTEM_PROMPT_UNIVERSAL.md` into your LLM once.
Auto-detects mode every session:

| Mode | Condition | What happens |
|------|-----------|--------------|
| **Native** | Local folder connected (Claude Code, Cursor, Windsurf) | Hooks fire automatically |
| **Remote** | Repo connected, no local folder | LLM uses git memory branches |
| **Cloud-only** | No folder, no repo | Snapshot auto-synced via GitHub Gist |
| **Dual** | Both connected | Local primary, repo as backup |

**Mode C (cloud-only) setup — once:**
```bash
gh auth login           # or: export GITHUB_TOKEN=<token>
ci snapshots --push     # creates a private Gist, prints the URL
```
Paste that URL at the start of any cloud session — the LLM fetches it automatically.
After each session it reminds you to push; or the hook pushes it for you in Claude Code.

---

## Verify

```bash
ci health
```

---

## Commands

```
cii / ci install        enable in project (new or existing)
ci health               check everything
ci dashboard            web dashboard :7654
ci rebuild              refresh index
ci test                 surgical tests (changed files only)
ci test --all           full suite
ci pentest source .     security scan
ci pentest web URL      OWASP scan
ci snapshots            list session-limit snapshots
ci snapshots --push     push snapshot to GitHub Gist (Mode C)
ci snapshots <llm>      show snapshot for claude/chatgpt/gemini/...
ci snapshots URL        detect platform from URL
ci export-context       snapshot for manual paste
ci search <term>        search knowledge index
ci sync                 sync context docs
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ci: not found` | Restart terminal |
| `health: ISSUES` | `cii` again from project root |
| No dashboard data | `ci rebuild` |
| Port in use | `ci dashboard 8080` |
| WSL: "cannot execute" | Re-run the bash installer |
| Defender flags ci.bat | Add `%USERPROFILE%\.claude-intel` to Defender exclusions |

**Requirements:** Python 3.8+, Git 2.20+

**Uninstall:** `rm -rf ~/.claude-intel .ai .claude/hooks`

---

## Firewall / Corporate Network

| Problem | Fix |
|---------|-----|
| `curl` blocked | `export https_proxy=http://proxy:port` then re-run |
| PowerShell policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first |
| Corporate proxy (Windows) | Installer reads system proxy automatically; if still failing: `$env:HTTPS_PROXY="http://proxy:port"` |
| Defender / SmartScreen | Installer runs `Unblock-File` automatically; if still blocked add `%USERPROFILE%\.claude-intel` to exclusions |
| MITM SSL cert | `git config --global http.sslCAInfo /path/to/corp-ca.crt` |
| macOS Gatekeeper | Installer strips quarantine flag automatically |
| SELinux | `restorecon -v ~/.claude-intel/ci` |
| github.com fully blocked | Download zip: `github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/archive/refs/heads/main.zip` → extract to `~/.claude-intel` → re-run installer |
