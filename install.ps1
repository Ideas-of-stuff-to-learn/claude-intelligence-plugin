# Claude Intelligence Plugin — Windows installer (PowerShell 5+ / PowerShell Core)
#
# Usage:
#   irm https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1 | iex
#
# If blocked by execution policy, run this first (current session only):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#
# If behind a corporate proxy:
#   $env:HTTPS_PROXY = "http://your-proxy:port"
#   irm ... | iex
#
# If Defender blocks the download, download the zip manually:
#   https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/archive/refs/heads/main.zip

# Bypass execution policy for this session (needed when AllSigned or Restricted is set)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force 2>$null
$ErrorActionPreference = "Stop"

$REPO_URL  = "https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin"
$INSTALL_DIR = "$env:USERPROFILE\.claude-intel"

# ── Force TLS 1.2+ (Windows 7/Server 2012 default to TLS 1.0 which GitHub rejects) ──
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13 2>$null

# ── Respect system proxy ──────────────────────────────────────────────────────
[System.Net.WebRequest]::DefaultWebProxy = [System.Net.WebRequest]::GetSystemWebProxy()
[System.Net.WebRequest]::DefaultWebProxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials

# ── Check git ─────────────────────────────────────────────────────────────────
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error @"
git is required.
Install options:
  • winget install --id Git.Git
  • https://git-scm.com/download/win
  • choco install git
"@
    exit 1
}

# ── Check Python ──────────────────────────────────────────────────────────────
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd -c "import sys; print(sys.version_info.major)" 2>$null
        if ($ver -eq "3") { $python = $cmd; break }
    } catch {}
}
if (-not $python) {
    Write-Error @"
Python 3 is required.
Install options:
  • winget install --id Python.Python.3
  • https://python.org/downloads
  • Microsoft Store: search 'Python 3'
"@
    exit 1
}

Write-Host "Using $python ($(& $python --version))"

# ── Clone or update ───────────────────────────────────────────────────────────
if (Test-Path "$INSTALL_DIR\.git") {
    $existing = git -C $INSTALL_DIR remote get-url origin 2>$null
    if ($existing -like "*claude-intelligence-plugin*") {
        Write-Host "Updating existing installation..."
        git -C $INSTALL_DIR pull --ff-only
        Write-Host "✓ Updated $INSTALL_DIR"
    } else {
        Write-Error "$INSTALL_DIR exists but points to a different repo. Remove it and retry: rmdir /s /q `"$INSTALL_DIR`""
        exit 1
    }
} elseif (Test-Path $INSTALL_DIR) {
    Write-Host "Removing stale $INSTALL_DIR..."
    Remove-Item -Recurse -Force $INSTALL_DIR
    git clone $REPO_URL $INSTALL_DIR
    Write-Host "✓ Cloned to $INSTALL_DIR"
} else {
    Write-Host "Cloning claude-intelligence-plugin..."
    try {
        git clone $REPO_URL $INSTALL_DIR
    } catch {
        Write-Error @"
git clone failed. Possible causes:
  • Firewall blocking github.com — set HTTPS_PROXY and retry
  • Corporate SSL inspection — ask IT to whitelist github.com / raw.githubusercontent.com
  • Defender quarantine — download zip manually from:
    $REPO_URL/archive/refs/heads/main.zip
    Extract to $INSTALL_DIR and re-run this script.
Error: $_
"@
        exit 1
    }
    Write-Host "✓ Cloned to $INSTALL_DIR"
}

# ── Unblock all files (Defender / SmartScreen marks downloads as untrusted) ──
Get-ChildItem -Path $INSTALL_DIR -Recurse -ErrorAction SilentlyContinue |
    ForEach-Object { Unblock-File -Path $_.FullName -ErrorAction SilentlyContinue }
Write-Host "✓ Unblocked files (SmartScreen)"

# ── Write ci.bat wrapper ──────────────────────────────────────────────────────
$bat = "@echo off`r`n$python `"$INSTALL_DIR\.ai\intelligence_cli.py`" %*`r`n"
[System.IO.File]::WriteAllText("$INSTALL_DIR\ci.bat", $bat, [System.Text.Encoding]::ASCII)

# ── Write cii.bat (alias for ci install) ─────────────────────────────────────
$cii = "@echo off`r`n$python `"$INSTALL_DIR\.ai\intelligence_cli.py`" install %*`r`n"
[System.IO.File]::WriteAllText("$INSTALL_DIR\cii.bat", $cii, [System.Text.Encoding]::ASCII)
Write-Host "✓ Created ci.bat + cii.bat"

# ── Add to user PATH ──────────────────────────────────────────────────────────
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if (-not $userPath) { $userPath = "" }
if ($userPath -notlike "*claude-intel*") {
    [Environment]::SetEnvironmentVariable("PATH", "$INSTALL_DIR;$userPath", "User")
    # Also update current session PATH so cii works without restart (best effort)
    $env:PATH = "$INSTALL_DIR;$env:PATH"
    Write-Host "✓ Added to PATH (user scope)"
} else {
    Write-Host "✓ PATH already set"
}

# ── Defender exclusion hint (optional, not enforced) ─────────────────────────
Write-Host ""
Write-Host "Note: if Windows Defender flags ci.bat, add an exclusion:"
Write-Host "  Settings → Windows Security → Virus & threat protection → Exclusions → Add: $INSTALL_DIR"
Write-Host ""
Write-Host "✓ Install complete"
Write-Host ""
Write-Host "  → Restart your terminal (PATH update takes effect in new sessions)"
Write-Host "  → In any project: cii"
Write-Host ""
