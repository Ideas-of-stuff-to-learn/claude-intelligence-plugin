# Install Claude Intelligence

## Step 1 — Run one line for your terminal

| Terminal | Command |
|---|---|
| Mac · Linux · WSL · Git Bash · zsh · bash · fish · nushell | `curl -fsSL https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.sh \| sh` |
| PowerShell (5 or 7) | `Set-ExecutionPolicy Bypass -Scope Process -Force; iwr https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1 -UseBasicParsing | iex` |
| CMD | `powershell -ExecutionPolicy Bypass -Command "iwr https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/install.ps1 -UseBasicParsing | iex"` |

Restart your terminal after running.

## Step 2 — Set up any repo

```bash
cd ~/your-project
ci install
```

That's it. Works whether the repo is fresh, has an old version of the plugin, or already has the latest.

## What `ci install` does

- Detects existing plugin files and patches any that are outdated
- Adds any missing files
- Rebuilds the intelligence index
- Runs the three analysis lenses (semantic, structural, exact)
- Registers the repo in the global project registry

## Updating

When the plugin has new changes:

```bash
cd ~/.claude-intel && git pull
ci install   # re-run in any repo to apply updates
```

## Uninstall

```bash
rm -rf ~/.claude-intel
# remove the PATH line from ~/.zshrc (or ~/.bashrc etc)
```

## Available commands

```
ci install          # install or upgrade in current repo
ci status           # index health
ci search <term>    # search the knowledge index
ci events           # recent telemetry events
ci budget <desc>    # estimate resource budget for a task
ci health           # check all components
ci dashboard        # start web dashboard at localhost:7654
ci log-event <type> <component> <status>
```
