# Claude Intelligence Plugin installer for PowerShell
# Usage: iwr https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin"
$installDir = "$env:USERPROFILE\.claude-intel"

# Check for required tools
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git is required. Install git and try again."
    exit 1
}

if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-Error "Python 3 is required. Install Python 3 and try again."
    exit 1
}

# Clone or update
if (Test-Path $installDir) {
    $existingUrl = & git -C $installDir remote get-url origin 2>$null
    if ($existingUrl -like "*Ideas-of-stuff-to-learn/claude-intelligence-plugin*") {
        Write-Host "Updating existing installation..."
        & git -C $installDir pull
        Write-Host "✓ Updated ~/.claude-intel"
    } else {
        Write-Warning "~\.claude-intel exists but points to a different repo: $existingUrl"
        Write-Warning "Remove it manually and re-run this script."
        exit 1
    }
} else {
    Write-Host "Cloning claude-intelligence-plugin..."
    & git clone $RepoUrl $installDir
    Write-Host "✓ Cloned to ~/.claude-intel"
}

# Add to user PATH permanently
$current = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($current -notlike "*\.claude-intel*") {
    [Environment]::SetEnvironmentVariable("PATH", "$installDir;$current", "User")
    Write-Host "✓ Added to PATH (restart terminal to apply)"
} else {
    Write-Host "✓ PATH already contains ~/.claude-intel (skipping)"
}

Write-Host ""
Write-Host "Then run:"
Write-Host "  ci install"
