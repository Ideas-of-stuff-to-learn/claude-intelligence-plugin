# Claude Intelligence Plugin — Windows installer (PowerShell)
# Run with: irm https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$REPO_URL = "https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin"
$INSTALL_DIR = "$env:USERPROFILE\.claude-intel"

# Check git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git is required. Install from https://git-scm.com and retry."
    exit 1
}

# Check python
$python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" }
          elseif (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" }
          else { $null }
if (-not $python) {
    Write-Error "Python 3 is required. Install from https://python.org and retry."
    exit 1
}

# Clone or update
if (Test-Path $INSTALL_DIR) {
    $existing = git -C $INSTALL_DIR remote get-url origin 2>$null
    if ($existing -like "*claude-intelligence-plugin*") {
        Write-Host "Updating existing installation..."
        git -C $INSTALL_DIR pull
        Write-Host "✓ Updated $INSTALL_DIR"
    } else {
        Write-Error "$INSTALL_DIR exists but points elsewhere. Remove it and retry."
        exit 1
    }
} else {
    Write-Host "Cloning claude-intelligence-plugin..."
    git clone $REPO_URL $INSTALL_DIR
    Write-Host "✓ Cloned to $INSTALL_DIR"
}

# Write ci.bat wrapper
$bat = @"
@echo off
$python "$INSTALL_DIR\.ai\intelligence_cli.py" %*
"@
Set-Content -Path "$INSTALL_DIR\ci.bat" -Value $bat -Encoding ASCII
Write-Host "✓ Created ci.bat"

# Write cii.bat alias
$cii = @"
@echo off
$python "$INSTALL_DIR\.ai\intelligence_cli.py" install %*
"@
Set-Content -Path "$INSTALL_DIR\cii.bat" -Value $cii -Encoding ASCII
Write-Host "✓ Created cii.bat"

# Add to user PATH if not already there
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*claude-intel*") {
    [Environment]::SetEnvironmentVariable("PATH", "$INSTALL_DIR;$userPath", "User")
    Write-Host "✓ Added to PATH (user)"
} else {
    Write-Host "✓ PATH already set (skipping)"
}

Write-Host ""
Write-Host "Done. Restart your terminal, then:"
Write-Host "  cd your-project"
Write-Host "  cii"
