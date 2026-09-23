# claude-intelligence-plugin

A Claude Code plugin that packages reusable skills, hooks, subagents, and project templates for AI-assisted development workflows. Install it once into any project and get a full intelligence system — session management, context auditing, build verification, and more.

## Install

```
/plugin marketplace add Ideas-of-stuff-to-learn/claude-intelligence-plugin
/plugin install claude-intelligence-plugin@claude-intelligence-plugin
```

Or reference it in your project's `.claude/settings.json`:
```json
{
  "extraKnownMarketplaces": ["Ideas-of-stuff-to-learn/claude-intelligence-plugin"],
  "enabledPlugins": ["claude-intelligence-plugin"]
}
```

## Contents

| Type | Name | Description |
|---|---|---|
| Skills | _(coming soon)_ | build-intelligence, realign, safe-point, ghost-test, handoff, audit-context |
| Agents | _(coming soon)_ | librarian, context-auditor, verifier, explorer |
| Hooks | _(coming soon)_ | session_start, check_handoff, safe-point guard, context sync |
| Templates | _(coming soon)_ | context/*.md skeletons, .ai/ scripts |

## Development

Skills and hooks are built and stabilised in [Cashflow2.0](https://github.com/Ideas-of-stuff-to-learn/Cashflow2.0) first, then packaged here. Bump `version` in `.claude-plugin/plugin.json` on each change.
