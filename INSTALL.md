# Claude Intelligence Plugin — Setup Guide

---

## Step 1 — Install the plugin

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

Restart your terminal.

---

## Step 2 — Enable it in your project

Open a terminal in your project folder and run:
```bash
cii
```

Works on new and existing projects. Re-running is safe.

---

## Step 3 — Connect your LLM

**If you use Claude Code, Cursor, or Windsurf** — you're done. Hooks fire automatically, nothing else to do.

**If you use a cloud LLM (ChatGPT, Gemini, Claude.ai chat, etc.):**

```bash
gh auth login           # one-time GitHub login (skip if already done)
ci snapshots --push     # generates your personal context URL
```

It prints a URL like `https://gist.github.com/yourname/abc123`.

**Paste that URL into your LLM at the start of any session.**
The LLM fetches it and loads both the plugin instructions and your project context automatically — nothing else to paste.

> Don't have `gh`? Install it from [cli.github.com](https://cli.github.com) or set `GITHUB_TOKEN` instead.

---

## That's it

Every time you start a new cloud LLM session: paste the URL.
The URL stays the same — it updates in place when you push.

To push an updated snapshot after a session:
```bash
ci snapshots --push
```

Or it pushes automatically if you use Claude Code (the PreCompact hook does it).

---

## Verify everything works

```bash
ci health
```

Should print: `Intelligence system health: OK`

---

## All commands

```
cii                     enable plugin in project
ci health               check everything
ci dashboard            open web dashboard (port 7654)
ci rebuild              refresh knowledge index
ci test                 run only tests for changed files
ci test --all           full test suite
ci pentest source .     scan for secrets and vulnerabilities
ci pentest web <url>    OWASP/header scan
ci snapshots            list saved snapshots
ci snapshots --push     push snapshot to GitHub Gist (get/update your URL)
ci snapshots --generate create a snapshot now
ci search <term>        search knowledge index
ci sync                 sync context documents
ci export-context       print snapshot to terminal
```

---

## Firewall / blocked installs

| Situation | Fix |
|-----------|-----|
| `curl` blocked | `export https_proxy=http://proxy:port` then retry |
| PowerShell policy blocked | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first |
| Corporate proxy (Windows) | Installer auto-reads system proxy; if still failing: `$env:HTTPS_PROXY="http://proxy:port"` |
| Windows Defender / SmartScreen | Installer runs `Unblock-File` automatically; if still blocked: add `%USERPROFILE%\.claude-intel` to Defender exclusions |
| Corporate SSL (MITM cert) | `git config --global http.sslCAInfo /path/to/corp-ca.crt` |
| macOS Gatekeeper | Installer strips quarantine flag automatically |
| SELinux blocked | `restorecon -v ~/.claude-intel/ci` |
| github.com fully blocked | Download zip from the repo → extract to `~/.claude-intel` → re-run installer |

---

## Uninstall

```bash
rm -rf ~/.claude-intel          # remove plugin (Mac/Linux)
rm -rf .ai .claude/hooks        # remove from this project only
```

Windows: `rmdir /s %USERPROFILE%\.claude-intel`
