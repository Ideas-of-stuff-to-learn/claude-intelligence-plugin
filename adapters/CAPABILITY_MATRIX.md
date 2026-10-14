# Capability Matrix

Full comparison of what the intelligence system can do across different AI platforms.

| Capability | Claude Code | OpenAI Assistants | Gemini CLI | Lovable | Generic |
|-----------|:-----------:|:-----------------:|:----------:|:-------:|:-------:|
| **Context Management** |
| Auto session-start context injection | YES (hook) | manual | manual | manual | manual |
| Pre-compact snapshot | YES (hook) | no | no | no | no |
| Auto context sync on edit | YES (hook) | no | no | no | no |
| **Knowledge Base** |
| SQLite knowledge.db | YES | no | no | no | no |
| Incremental context sync | YES | no | no | no | no |
| Full-text search | YES | no | no | no | no |
| Stale doc detection | YES | manual | manual | manual | manual |
| **Lifecycle Hooks** |
| SessionStart hook | YES | no | no | no | no |
| Stop / handoff guard | YES | no | no | no | no |
| PreToolUse safe-point guard | YES | no | no | no | no |
| PostToolUse fingerprint | YES | no | no | no | no |
| PreCompact snapshot | YES | no | no | no | no |
| **Skills** |
| /safe-point | YES | manual | manual | manual | manual |
| /handoff | YES | manual | manual | manual | manual |
| /verify | YES | manual | manual | manual | manual |
| /catch-up | YES | manual | manual | manual | manual |
| /execute | YES | YES | YES | YES | YES |
| /execute-careful | YES | YES | YES | YES | YES |
| /ghost-test | YES | YES | YES | YES | YES |
| /debug-systematically | YES | YES | YES | YES | YES |
| /review-change | YES | YES | YES | YES | YES |
| /recover-session | YES | manual | manual | manual | manual |
| /project-onboard | YES | partial | partial | partial | partial |
| /intelligence-health | YES | partial | partial | partial | partial |
| **Agents** |
| explorer | YES | manual | manual | manual | manual |
| librarian | YES | manual | manual | manual | manual |
| context-auditor | YES | YES | YES | YES | YES |
| verifier | YES | YES | YES | YES | YES |
| architecture-analyst | YES | YES | YES | YES | YES |
| test-architect | YES | YES | YES | YES | YES |
| regression-hunter | YES | YES | YES | YES | YES |
| security-auditor | YES | YES | YES | YES | YES |
| integration-auditor | YES | YES | YES | YES | YES |
| context-curator | YES | YES | YES | YES | YES |
| **Context Templates** |
| 15 standard docs | YES | YES | YES | YES | YES |
| **Dashboard & Observability** |
| Local dashboard server (localhost:7654) | YES | no | no | no | no |
| Event timeline (events table) | YES | no | no | no | no |
| Task history tracking | YES | no | no | no | no |
| Resource observations log | YES | manual | manual | manual | manual |
| /api/status JSON endpoint | YES | no | no | no | no |
| /api/health JSON endpoint | YES | no | no | no | no |
| /api/events JSON endpoint | YES | no | no | no | no |
| Auto-refresh dashboard (30s) | YES | no | no | no | no |
| **Usage Intelligence** |
| Task-local budget manager | YES | no | no | no | no |
| Preflight budget estimate | YES | no | no | no | no |
| Strategy adaptation (adapt_strategy) | YES | no | no | no | no |
| /usage-plan skill | YES | manual | manual | manual | manual |
| /dashboard-check skill | YES | manual | manual | manual | manual |
| Provider API usage (subscription limits) | no* | no* | no* | no* | no* |

> \* Provider usage information is not available through the shared intelligence engine
> without authorised API integration. Each provider (Claude Code, OpenAI, Gemini, Lovable)
> must be queried via its own authenticated API. This system tracks local operation
> budgets only (tool_calls, agent_calls, index_ops).

## Legend

- **YES** — Fully supported, works automatically or with a simple command
- **partial** — Supported with manual steps
- **manual** — Must be done by hand without tooling assistance
- **no** — Not available on this platform
