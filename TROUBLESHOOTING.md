# Troubleshooting

## Windows installation issues

### `Trojan:Win32/Commando.A!ml` — Windows Defender false positive

**Why it happens:**  
The original install command used `iwr | iex` — downloading a script and piping it directly into memory for execution. Windows Defender's ML model flags this pattern because it's identical to how malware installers behave. It never touches disk so Defender can't scan it before it runs.

**The fix:**  
We changed to download-then-run: `iwr -OutFile install.ps1` saves the file to disk first, Defender scans it, then `-File install.ps1` runs it. The script is identical — only the delivery method changed.

---

### `profile.ps1 cannot be loaded — running scripts is disabled`

**Why it happens:**  
Windows ships with PowerShell script execution disabled by default (`Restricted` policy). When PowerShell starts, it tries to load your profile script (`profile.ps1`) before running anything else. If that profile is blocked, PowerShell errors out before our script even starts.

**The fix:**  
Added `-NoProfile` to skip loading the profile entirely, and `-ExecutionPolicy Bypass` to allow our script to run for that one session only. Neither change is permanent — they only apply to that single command.

---

### `Missing closing '}' — ParserError` on a script that looks correct

**Why it happens:**  
PowerShell 5 (the version built into Windows) cannot reliably parse `.ps1` files with Unix line endings (LF only). It misreads the line structure and reports false syntax errors — in our case a `missing closing }` on line 21, which had nothing wrong with it.

PowerShell 7 handles LF fine, but PS5 is what ships with Windows by default.

**The fix:**  
Converted `install.ps1` to CRLF line endings and added `.gitattributes` to enforce `eol=crlf` for `.ps1` and `.bat` files so git never converts them back to LF on push.

---

### `✓` checkmark causing parser errors

**Why it happens:**  
The original `install.ps1` used Unicode checkmark characters (`✓`, U+2713) in `Write-Host` output. PowerShell 5 misparsed the UTF-8 encoded file when it contained non-ASCII characters in combination with LF line endings.

**The fix:**  
Replaced all `✓` with plain ASCII `[OK]`.

---

## General

### `ci: command not found` after install

You need to restart your terminal after the install script runs — the PATH change only takes effect in new terminal sessions.

### `ci install` says hooks are outdated on a fresh repo

This is expected if you cloned the repo a while ago and the plugin has been updated since. `ci install` patches them automatically.

### Dashboard shows no data

Run `ci install` first in the repo — this builds the index and records the first encounter. The dashboard reads from `knowledge.db` which doesn't exist until then.
