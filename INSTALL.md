# Claude Intelligence Plugin — Setup

---

## Step 1 — Install (everyone does this)

**Mac / Linux / WSL / Git Bash:**
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

> Blocked by firewall? See [Firewall fixes](#firewall-fixes) below.

Restart your terminal.

---

## Step 2 — Enable in your project (everyone does this)

Open a terminal in your project folder:
```bash
cii
```

---

## Step 3 — Pick your mode

### 🖥️ Local (Claude Code, Cursor, Windsurf, any IDE with folder access)
**You're done.** Hooks fire automatically every session. Nothing else to configure.

---

### ☁️ Cloud LLM with no local folder (ChatGPT, Gemini, Claude.ai chat, etc.)
Run this once in your terminal:
```bash
ci snapshots --push
```
It prints a URL. **Save it.**

Paste that URL at the start of every session in your cloud LLM.
The LLM loads your instructions and project context automatically — nothing else to paste.
The URL stays the same and updates in place.

> No login or account needed — works out of the box.
> For a private URL: `gh auth login` (optional upgrade).

---

### 🔀 Both (local IDE + cloud LLM at the same time)
Do both steps above. The local hooks handle native sessions; the URL handles cloud sessions.
They share the same context — the plugin syncs between them.

---

## Verify

```bash
ci health
```

---

## All commands

```
cii / ci install        enable plugin in project
ci health               check everything
ci dashboard            web dashboard (port 7654)
ci rebuild              refresh knowledge index
ci test                 tests for changed files only (~1s)
ci test --all           full test suite
ci pentest source .     scan for secrets / vulnerabilities
ci pentest web <url>    OWASP / header scan
ci snapshots --push     push snapshot, get/update your URL
ci snapshots            list saved snapshots
ci snapshots <llm>      show snapshot for claude/chatgpt/gemini/...
ci search <term>        search knowledge index
ci sync                 sync context docs
ci export-context       print snapshot to terminal
```

---

## Firewall fixes

| Situation | Fix |
|-----------|-----|
| `curl` blocked | `export https_proxy=http://proxy:port` then retry |
| PowerShell policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first |
| Corporate proxy (Windows) | Installer reads system proxy automatically; if still failing: `$env:HTTPS_PROXY="http://proxy:port"` |
| Defender / SmartScreen | Installer runs `Unblock-File` automatically; if still blocked: add `%USERPROFILE%\.claude-intel` to Defender exclusions |
| Corporate SSL cert | `git config --global http.sslCAInfo /path/to/corp-ca.crt` |
| macOS Gatekeeper | Installer strips quarantine flag automatically |
| SELinux | `restorecon -v ~/.claude-intel/ci` |
| github.com fully blocked | [Download zip](https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/archive/refs/heads/main.zip) → extract to `~/.claude-intel` → re-run installer |

---

## Uninstall

```bash
rm -rf ~/.claude-intel .ai .claude/hooks   # Mac/Linux
rmdir /s %USERPROFILE%\.claude-intel       # Windows
```
