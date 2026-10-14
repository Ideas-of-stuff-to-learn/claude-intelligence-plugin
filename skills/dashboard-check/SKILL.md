---
name: dashboard-check
description: Check the intelligence dashboard status. Shows index health, recent tasks, and system state. Safe for automatic invocation.
---

## Step 1 — CLI status

```bash
python .ai/intelligence_cli.py status
python .ai/intelligence_cli.py health
```

## Step 2 — Recent events

```bash
python .ai/intelligence_cli.py events
```

## Step 3 — Dashboard URL

The full standalone dashboard runs at:
```bash
python .ai/dashboard_server.py
# then open http://localhost:7654
```

Report the health summary to the user.
