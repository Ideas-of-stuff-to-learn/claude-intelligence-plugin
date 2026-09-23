# Intelligence System Bootstrap

You are an AI assistant reading this file in order to install the Claude Code intelligence system into a project. Follow these steps exactly.

---

## Step 1 — Add the marketplace to global settings

Read `~/.claude/settings.json`. If it doesn't exist, create it as `{}`.

Add or merge this into it:

```json
{
  "extraKnownMarketplaces": [
    {
      "name": "Ideas of Stuff to Learn",
      "url": "https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/.claude-plugin/marketplace.json"
    }
  ]
}
```

Preserve any existing keys — do not overwrite the whole file.

## Step 2 — Install the plugin

Run in the project root:

```bash
claude plugin add claude-intelligence
```

This copies all skills and agents into the project's `.claude/` directory.

## Step 3 — Detect state and trigger the right skill

Check whether the intelligence system is already in place:

- If `context/` exists AND has at least 5 `.md` files AND `.ai/knowledge.db` exists → run `/catch-up`
- Otherwise → run `/build-intelligence`

Do not ask the user which one. Detect it yourself and proceed.

---

## Why this file exists

So you never need to remember any URLs, plugin names, or installation steps.
The single instruction to give Claude Code in any project is:

> Fetch `https://raw.githubusercontent.com/Ideas-of-stuff-to-learn/claude-intelligence-plugin/main/BOOTSTRAP.md` and follow the steps.
