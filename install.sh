#!/bin/sh
# Claude Intelligence Plugin installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.sh | sh
#
# Firewall/proxy: if curl fails, set https_proxy first:
#   export https_proxy=http://your-proxy:port
#   curl -fsSL ... | sh
# Or clone manually:
#   git clone https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin ~/.claude-intel
#   sh ~/.claude-intel/install.sh

set -e

REPO_URL="https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin"
INSTALL_DIR="$HOME/.claude-intel"

# ── macOS: remove quarantine flag if running from a downloaded script ─────────
if [ "$(uname)" = "Darwin" ]; then
    xattr -d com.apple.quarantine "$0" 2>/dev/null || true
fi

# ── Check for required tools ──────────────────────────────────────────────────
if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required."
    echo "  macOS:  brew install git   (or install Xcode Command Line Tools)"
    echo "  Ubuntu: sudo apt install git"
    echo "  Other:  https://git-scm.com/downloads"
    exit 1
fi

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        ver=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "0")
        if [ "$ver" = "3" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3 is required."
    echo "  macOS:  brew install python3"
    echo "  Ubuntu: sudo apt install python3"
    echo "  Other:  https://python.org/downloads"
    exit 1
fi

# ── Clone or update ───────────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    existing_url=$(git -C "$INSTALL_DIR" remote get-url origin 2>/dev/null || echo "")
    if echo "$existing_url" | grep -q "claude-intelligence-plugin"; then
        echo "Updating existing installation..."
        if ! git -C "$INSTALL_DIR" pull --ff-only 2>/dev/null; then
            git -C "$INSTALL_DIR" fetch origin && git -C "$INSTALL_DIR" reset --hard origin/main
        fi
        echo "✓ Updated $INSTALL_DIR"
    else
        echo "WARNING: $INSTALL_DIR exists but points to a different repo."
        echo "Remove it and re-run: rm -rf $INSTALL_DIR"
        exit 1
    fi
elif [ -d "$INSTALL_DIR" ]; then
    # Directory exists but not a git repo — treat as stale, overwrite
    echo "Removing stale $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    echo "✓ Cloned to $INSTALL_DIR"
else
    echo "Cloning claude-intelligence-plugin..."
    # Try HTTPS first; fall back with advice if blocked
    if ! git clone "$REPO_URL" "$INSTALL_DIR" 2>/tmp/_ci_git_err; then
        echo ""
        echo "ERROR: git clone failed. Possible causes:"
        echo "  • Firewall blocking github.com — set https_proxy and retry"
        echo "  • Corporate SSL inspection — try: git config --global http.sslVerify false (ask IT first)"
        echo "  • No internet — download the zip from github.com and extract to $INSTALL_DIR"
        cat /tmp/_ci_git_err
        exit 1
    fi
    echo "✓ Cloned to $INSTALL_DIR"
fi

# ── Write ci wrapper (LF-only, no CRLF issues) ───────────────────────────────
# Heredoc written via printf to guarantee LF endings even on systems where
# git core.autocrlf=true would corrupt the file.
printf '#!/bin/sh\nPLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"\nexec %s "$PLUGIN_DIR/.ai/intelligence_cli.py" "$@"\n' \
    "$PYTHON" > "$INSTALL_DIR/ci"
chmod +x "$INSTALL_DIR/ci"
echo "✓ Created ci wrapper ($PYTHON)"

# ── macOS: remove quarantine from installed files ────────────────────────────
if [ "$(uname)" = "Darwin" ]; then
    xattr -dr com.apple.quarantine "$INSTALL_DIR" 2>/dev/null || true
fi

# ── Detect shell rc and add PATH + alias ─────────────────────────────────────
SHELL_NAME=$(basename "${SHELL:-sh}")
RC_FILE=""

# ci() shell function: runs ci, then cds if a nav file was written (ci repos navigation)
# cii = shorthand for ci install
case "$SHELL_NAME" in
    zsh|bash)
        case "$SHELL_NAME" in
            zsh)  RC_FILE="$HOME/.zshrc" ;;
            bash) RC_FILE="$HOME/.bashrc" ;;
        esac
        # macOS login shells use .bash_profile
        if [ "$SHELL_NAME" = "bash" ] && [ "$(uname)" = "Darwin" ] && [ -f "$HOME/.bash_profile" ]; then
            RC_FILE="$HOME/.bash_profile"
        fi
        SHELL_BLOCK='
# Claude Intelligence CLI
export PATH="$HOME/.claude-intel:$PATH"
ci() { command ci "$@"; _f="$(mktemp -d)/ci_nav"; [ -f /tmp/ci_nav_dir.txt ] && { cd "$(cat /tmp/ci_nav_dir.txt)"; rm -f /tmp/ci_nav_dir.txt; }; }
alias cii="ci install"'
        ;;
    fish)
        RC_FILE="$HOME/.config/fish/config.fish"
        SHELL_BLOCK="
# Claude Intelligence CLI
fish_add_path ~/.claude-intel
function ci; command ci \$argv; if test -f /tmp/ci_nav_dir.txt; cd (cat /tmp/ci_nav_dir.txt); rm -f /tmp/ci_nav_dir.txt; end; end
alias cii='ci install'"
        ;;
    nu|nushell)
        RC_FILE="$HOME/.config/nushell/config.nu"
        # Nushell doesn't support shell functions in the same way; PATH + alias only
        SHELL_BLOCK='
# Claude Intelligence CLI
$env.PATH = ($env.PATH | prepend ~/.claude-intel)
alias cii = ci install'
        ;;
    tcsh|csh)
        RC_FILE="${HOME}/.tcshrc"
        [ -f "$HOME/.cshrc" ] && RC_FILE="$HOME/.cshrc"
        SHELL_BLOCK='
# Claude Intelligence CLI
setenv PATH "$HOME/.claude-intel:$PATH"
alias cii "ci install"'
        ;;
    *)
        RC_FILE="$HOME/.profile"
        SHELL_BLOCK='
# Claude Intelligence CLI
export PATH="$HOME/.claude-intel:$PATH"
alias cii="ci install"'
        ;;
esac

if [ -n "$RC_FILE" ]; then
    mkdir -p "$(dirname "$RC_FILE")"
    if [ -f "$RC_FILE" ] && grep -qF ".claude-intel" "$RC_FILE" 2>/dev/null; then
        echo "✓ PATH already in $RC_FILE"
    else
        printf '%s\n' "$SHELL_BLOCK" >> "$RC_FILE"
        echo "✓ Added PATH + ci() function to $RC_FILE"
    fi
else
    echo "Could not detect shell config. Add manually:"
    echo "  export PATH=\"\$HOME/.claude-intel:\$PATH\""
fi

echo ""
echo "✓ Install complete"
echo ""
echo "  → Restart your terminal"
echo "  → In any project: cii"
echo ""
