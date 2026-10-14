# /project-onboard

Set up the intelligence system in a new project — scaffold context docs, configure hooks, and build the initial knowledge base.

## When to use

- First time running the intelligence plugin in a project.
- When onboarding a new codebase that has no context/ directory.
- When `python .ai/intelligence_cli.py health` reports major missing pieces.

## Steps

### Phase 1: Scaffold Context Directory

1. Create `context/` if it does not exist.
2. Copy all 15 templates from `templates/context/` into `context/`.
3. Do not overwrite existing context docs.

### Phase 2: Populate Core Docs

Read the codebase and fill in these four docs immediately:

**`context/overview.md`** — answer:
- What does this project do?
- Who uses it?
- What is the tech stack?

**`context/architecture.md`** — answer:
- What are the main components?
- How do they communicate?
- What are the entry points?

**`context/constraints.md`** — answer:
- What must never change?
- What are the hard technical limits?

**`context/dependencies.md`** — answer:
- What external libraries does it use?
- What external services does it call?

### Phase 3: Install Hooks

1. Create `.claude/` if it does not exist.
2. Copy all hooks from `hooks/` to `.claude/hooks/`.
3. Copy `templates/settings.json` to `.claude/settings.json`.
4. Verify: `cat .claude/settings.json` shows all five hook events.

### Phase 4: Build Knowledge Base

Run:
```
python .ai/rebuild_db.py
```

Verify with:
```
python .ai/intelligence_cli.py status
python .ai/intelligence_cli.py health
```

### Phase 5: First Safe Point

Run `/safe-point` to record the clean initial state before any changes.

## Verification

After onboarding, `python .ai/intelligence_cli.py health` should report no critical issues.
