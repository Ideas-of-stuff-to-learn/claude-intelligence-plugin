#!/bin/sh
# Claude Intelligence Plugin installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.sh | sh

set -e

REPO_URL="https://github.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin"
INSTALL_DIR="$HOME/.claude-intel"

# Check for required tools
if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required. Install git and try again."
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    echo "ERROR: Python 3 is required. Install Python 3 and try again."
    exit 1
fi

# Clone or update
if [ -d "$INSTALL_DIR" ]; then
    existing_url=$(git -C "$INSTALL_DIR" remote get-url origin 2>/dev/null || echo "")
    if echo "$existing_url" | grep -q "Ideas-of-stuff-to-learn/claude-intelligence-plugin"; then
        echo "Updating existing installation..."
        git -C "$INSTALL_DIR" pull
        echo "✓ Updated ~/.claude-intel"
    else
        echo "WARNING: ~/.claude-intel exists but points to a different repo: $existing_url"
        echo "Remove it manually and re-run this script."
        exit 1
    fi
else
    echo "Cloning claude-intelligence-plugin..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    echo "✓ Cloned to ~/.claude-intel"
fi

# Strip Windows CRLF from the ci script — git with core.autocrlf=true
# (common on Windows/WSL) can add \r even when .gitattributes says eol=lf,
# and bash/sh reject a shebang of '#!/bin/sh\r' with "file not found".
if command -v sed >/dev/null 2>&1; then
    sed -i 's/\r//' "$INSTALL_DIR/ci"
fi

# Make ci executable
chmod +x "$INSTALL_DIR/ci"
echo "✓ Made ci executable"

# Detect shell and add to PATH
SHELL_NAME=$(basename "$SHELL")
PATH_LINE='export PATH="$HOME/.claude-intel:$PATH"'
RC_FILE=""

if [ "$SHELL_NAME" = "zsh" ] || [ -f "$HOME/.zshrc" ]; then
    RC_FILE="$HOME/.zshrc"
elif [ "$SHELL_NAME" = "bash" ] || [ -f "$HOME/.bashrc" ]; then
    RC_FILE="$HOME/.bashrc"
elif [ "$SHELL_NAME" = "fish" ] || [ -f "$HOME/.config/fish/config.fish" ]; then
    RC_FILE="$HOME/.config/fish/config.fish"
    PATH_LINE='set -gx PATH ~/.claude-intel $PATH'
elif [ "$SHELL_NAME" = "nu" ] || [ "$SHELL_NAME" = "nushell" ] || [ -f "$HOME/.config/nushell/config.nu" ]; then
    RC_FILE="$HOME/.config/nushell/config.nu"
    PATH_LINE='$env.PATH = ($env.PATH | prepend ~/.claude-intel)'
elif [ "$SHELL_NAME" = "tcsh" ] || [ "$SHELL_NAME" = "csh" ]; then
    if [ -f "$HOME/.tcshrc" ]; then
        RC_FILE="$HOME/.tcshrc"
    else
        RC_FILE="$HOME/.cshrc"
    fi
    PATH_LINE='setenv PATH "$HOME/.claude-intel:$PATH"'
elif [ "$SHELL_NAME" = "dash" ] || [ "$SHELL_NAME" = "sh" ]; then
    RC_FILE="$HOME/.profile"
fi

if [ -n "$RC_FILE" ]; then
    mkdir -p "$(dirname "$RC_FILE")"
    if [ -f "$RC_FILE" ] && grep -qF ".claude-intel" "$RC_FILE"; then
        echo "✓ PATH already set in $RC_FILE (skipping)"
    else
        printf '\n# Claude Intelligence CLI\n%s\n' "$PATH_LINE" >> "$RC_FILE"
        echo "✓ Added to PATH in $RC_FILE"
    fi
else
    echo "Could not detect shell rc file."
    echo "Add this line to your shell config manually:"
    echo "  $PATH_LINE"
fi

echo ""
echo "Restart your terminal, then run 'ci help' to see what you can do."
