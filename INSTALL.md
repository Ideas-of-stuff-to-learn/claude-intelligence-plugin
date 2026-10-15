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

Restart your terminal, then in any project:
```bash
cii
```

---

## Firewall / Corporate Network Fixes

### curl blocked (Linux / macOS / WSL)
```bash
# Set proxy first, then install
export https_proxy=http://your-proxy:port
curl -fsSL .../install.sh | sh

# Or skip curl entirely — clone directly
git clone https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin ~/.claude-intel
sh ~/.claude-intel/install.sh
```

### PowerShell execution policy blocked
```powershell
# Bypass for current session only (no permanent change)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
irm .../install.ps1 | iex
```

### Corporate proxy (Windows)
```powershell
# The installer auto-reads your system proxy.
# If it still fails, set it explicitly:
$env:HTTPS_PROXY = "http://your-proxy:port"
irm .../install.ps1 | iex
```

### Windows Defender / SmartScreen blocks the download
The installer runs `Unblock-File` automatically. If Defender still flags it:
1. Add an exclusion: **Windows Security → Virus & threat protection → Exclusions → Add folder → `%USERPROFILE%\.claude-intel`**
2. Or install manually (see below)

### Corporate SSL inspection (MITM certificate)
```bash
# Linux/macOS — point git at your corporate CA bundle
git config --global http.sslCAInfo /path/to/corporate-ca.crt

# Windows — import the cert into Windows cert store, then git picks it up automatically
```

### github.com is blocked entirely — manual install
```bash
# On a machine with access, download the zip:
# https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/archive/refs/heads/main.zip
# Transfer it, then:
unzip main.zip
mv claude-intelligence-plugin-main ~/.claude-intel
sh ~/.claude-intel/install.sh
```

### macOS Gatekeeper blocks execution
```bash
# The installer removes the quarantine flag automatically.
# If you still see "cannot be opened because the developer cannot be verified":
xattr -dr com.apple.quarantine ~/.claude-intel
```

### SELinux / AppArmor (Linux)
```bash
# If ci is blocked by SELinux, restore default context:
restorecon -v ~/.claude-intel/ci
# Or run with python directly as a fallback:
python3 ~/.claude-intel/.ai/intelligence_cli.py install
```

---

## Connect your LLM

Paste `adapters/cloud-llm/SYSTEM_PROMPT_UNIVERSAL.md` into your LLM once.
Auto-detects mode every session:

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
ci install / cii    enable in project (new or existing)
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
| `ci: not found` after install | Restart terminal |
| `health: ISSUES` | `cii` again from project root |
| No dashboard data | `ci rebuild` |
| Port in use | `ci dashboard 8080` |
| WSL: "cannot execute" | Re-run `sh ~/.claude-intel/install.sh` (fixes CRLF) |
| Windows: `cii` not found | Restart terminal; PATH set for new sessions only |
| Defender flags ci.bat | Add `%USERPROFILE%\.claude-intel` to exclusions |

**Requirements:** Python 3.8+, Git 2.20+

**Uninstall:**
```bash
rm -rf ~/.claude-intel          # global (Unix)
rmdir /s %USERPROFILE%\.claude-intel   # global (Windows CMD)
rm -rf .ai .claude/hooks        # project only
```
