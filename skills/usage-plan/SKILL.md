---
name: usage-plan
description: Estimate resource budget before starting a large task. Checks index health, estimates agent calls, tool calls, and indexing operations needed. Reports confidence level and recommended allocation. Manual-only.
---

## Step 1 — Assess task scope

Read the requested work. Identify:
- Mandatory deliverables
- Subsystems affected  
- Whether index is fresh (run: `python .ai/intelligence_cli.py status`)
- Whether broad scan or targeted retrieval is needed

## Step 2 — Run budget estimate

```bash
python .ai/intelligence_cli.py budget "describe the task here"
```

Report the estimate: tool calls, agent calls, index ops, confidence.

## Step 3 — Allocation plan

For each workstream, note:
- Whether it can be skipped if resources tighten
- What the minimum viable version looks like

## Step 4 — Record allocation

Log the plan:
```bash
python .ai/intelligence_cli.py log-event resource.allocated budget-manager active
```

## Step 5 — Checkpoint policy

State clearly: if tool/agent calls exceed 2× the estimate, checkpoint and reassess before continuing.

Never skip mandatory verification to stay within a soft budget.
