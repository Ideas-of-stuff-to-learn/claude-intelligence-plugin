"""
PreCompact hook — precompact_snapshot.py
Fires when the LLM is approaching its context window limit (Claude Code: PreCompact event).
Creates a structured handoff snapshot that any LLM can pick up from,
and routes intelligently based on the LLM platform in use.

Supported platforms (auto-detected from environment):
  claude     — Claude Code / Claude.ai
  chatgpt    — ChatGPT / OpenAI
  gemini     — Google Gemini
  copilot    — GitHub Copilot
  cursor     — Cursor
  windsurf   — Windsurf
  generic    — any other LLM
"""
import sys
import os
import json
import datetime

# Platform detection strings → canonical name
_PLATFORM_HINTS = {
    'CLAUDE_SESSION':       'claude',
    'CLAUDE_PROJECT_DIR':   'claude',
    'OPENAI_SESSION':       'chatgpt',
    'COPILOT_SESSION':      'copilot',
    'CURSOR_SESSION':       'cursor',
    'WINDSURF_SESSION':     'windsurf',
    'GEMINI_SESSION':       'gemini',
}

# Per-platform: where to point the user and what paste format to use
_PLATFORM_PROFILES = {
    'claude': {
        'name': 'Claude',
        'snapshot_url_hint': 'claude.ai/project or Claude Code — paste snapshot as first message',
        'supports_projects': True,
        'memory_branch': True,      # can use Mode A git branch memory
        'system_prompt_note': 'Paste adapters/cloud-llm/SYSTEM_PROMPT_UNIVERSAL.md as project instructions',
    },
    'chatgpt': {
        'name': 'ChatGPT',
        'snapshot_url_hint': 'chatgpt.com — paste snapshot as first message in a new chat, or use a Project',
        'supports_projects': True,   # ChatGPT Projects support custom instructions
        'memory_branch': False,
        'system_prompt_note': 'Paste adapters/cloud-llm/SYSTEM_PROMPT_UNIVERSAL.md into Custom Instructions',
    },
    'gemini': {
        'name': 'Gemini',
        'snapshot_url_hint': 'gemini.google.com — paste snapshot as first message',
        'supports_projects': False,
        'memory_branch': False,
        'system_prompt_note': 'Paste adapters/cloud-llm/SYSTEM_PROMPT_UNIVERSAL.md as first system message',
    },
    'copilot': {
        'name': 'GitHub Copilot',
        'snapshot_url_hint': 'github.com/copilot — paste snapshot in the chat; repo is already connected',
        'supports_projects': False,
        'memory_branch': True,      # Copilot has repo access
        'system_prompt_note': 'Repo access available — Mode A (git branch memory) applies',
    },
    'cursor': {
        'name': 'Cursor',
        'snapshot_url_hint': 'Cursor AI chat — project folder is already connected (Mode B)',
        'supports_projects': True,
        'memory_branch': False,
        'system_prompt_note': 'Local folder connected — Mode B (native) applies. Paste snapshot if starting new chat.',
    },
    'windsurf': {
        'name': 'Windsurf',
        'snapshot_url_hint': 'Windsurf chat — project folder is already connected (Mode B)',
        'supports_projects': True,
        'memory_branch': False,
        'system_prompt_note': 'Local folder connected — Mode B (native) applies.',
    },
    'generic': {
        'name': 'LLM',
        'snapshot_url_hint': 'Paste snapshot at the start of your next session in any LLM chat window',
        'supports_projects': False,
        'memory_branch': False,
        'system_prompt_note': 'Paste adapters/cloud-llm/SYSTEM_PROMPT_UNIVERSAL.md as system prompt',
    },
}


def detect_platform() -> str:
    for env_key, platform in _PLATFORM_HINTS.items():
        if os.environ.get(env_key):
            return platform
    # Heuristic: check process name or TERM_PROGRAM
    term = os.environ.get('TERM_PROGRAM', '').lower()
    if 'cursor' in term:
        return 'cursor'
    if 'windsurf' in term:
        return 'windsurf'
    # Default — most installs are Claude Code
    return 'claude'


def _read(path: str, max_chars: int = 800) -> str:
    try:
        with open(path, encoding='utf-8') as f:
            return f.read(max_chars)
    except Exception:
        return ''


def build_snapshot(proj: str, platform: str) -> dict:
    """Build a structured context snapshot dict."""
    ctx = os.path.join(proj, 'context')
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    overview   = _read(os.path.join(ctx, 'overview.md'), 600)
    current    = _read(os.path.join(ctx, 'current-task.md'), 400)
    handoff    = _read(os.path.join(ctx, 'handoff.md'), 400)
    constraints = _read(os.path.join(ctx, 'constraints.md'), 300)
    problems   = _read(os.path.join(ctx, 'known-problems.md'), 300)

    profile = _PLATFORM_PROFILES.get(platform, _PLATFORM_PROFILES['generic'])

    return {
        'platform': platform,
        'platform_name': profile['name'],
        'snapshot_at': ts,
        'project': os.path.basename(proj),
        'project_path': proj,
        'overview': overview,
        'current_task': current,
        'last_handoff': handoff,
        'constraints': constraints,
        'known_problems': problems,
        'continuation': {
            'url_hint': profile['snapshot_url_hint'],
            'system_prompt_note': profile['system_prompt_note'],
            'memory_branch': profile['memory_branch'],
        },
    }


def write_snapshot(proj: str, snapshot: dict, platform: str) -> str:
    """Write snapshot to context/compaction-<platform>.md and return the path."""
    ctx = os.path.join(proj, 'context')
    os.makedirs(ctx, exist_ok=True)

    profile = _PLATFORM_PROFILES.get(platform, _PLATFORM_PROFILES['generic'])
    path = os.path.join(ctx, f'compaction-{platform}.md')

    lines = [
        f'# Compaction Snapshot — {profile["name"]}',
        f'**Created:** {snapshot["snapshot_at"]}  ',
        f'**Project:** {snapshot["project"]}',
        '',
        '> This file was auto-generated when the session approached its context limit.',
        '> Paste it (or the text below) at the start of your next chat to restore context.',
        '',
        '---',
        '',
        '## How to Continue',
        '',
        f'**Platform:** {profile["name"]}',
        f'**Where:** {profile["snapshot_url_hint"]}',
        f'**System prompt:** {profile["system_prompt_note"]}',
        '',
    ]

    if profile['memory_branch']:
        lines += [
            '**Memory branch available:** Yes — the LLM can read `ci/memory/main` from your repo.',
            '',
        ]

    lines += [
        '---',
        '',
        '## Paste This Block Into Your Next Session',
        '',
        '```',
        '=== CI CONTEXT SNAPSHOT ===',
        f'Project: {snapshot["project"]}',
        f'Captured: {snapshot["snapshot_at"]}',
        f'Platform: {snapshot["platform_name"]}',
        '',
    ]

    if snapshot['current_task'].strip():
        lines.append('--- Current Task ---')
        lines.append(snapshot['current_task'].strip()[:400])
        lines.append('')

    if snapshot['last_handoff'].strip():
        lines.append('--- Last Handoff ---')
        lines.append(snapshot['last_handoff'].strip()[:400])
        lines.append('')

    if snapshot['overview'].strip():
        lines.append('--- Project Overview ---')
        lines.append(snapshot['overview'].strip()[:400])
        lines.append('')

    if snapshot['constraints'].strip():
        lines.append('--- Constraints ---')
        lines.append(snapshot['constraints'].strip()[:200])
        lines.append('')

    if snapshot['known_problems'].strip():
        lines.append('--- Known Problems ---')
        lines.append(snapshot['known_problems'].strip()[:200])
        lines.append('')

    lines += [
        '=== END CI CONTEXT SNAPSHOT ===',
        '```',
        '',
        '---',
        '',
        '## Raw Context Files',
        '',
        '### context/current-task.md',
        '```',
        snapshot['current_task'][:600] or '(empty)',
        '```',
        '',
        '### context/handoff.md',
        '```',
        snapshot['last_handoff'][:600] or '(empty)',
        '```',
    ]

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return path


def write_json_index(proj: str, platforms_written: list) -> None:
    """Write .ai/compaction-index.json so ci can quickly list all snapshots."""
    index_path = os.path.join(proj, '.ai', 'compaction-index.json')
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        existing = {}
        if os.path.exists(index_path):
            with open(index_path, encoding='utf-8') as f:
                existing = json.load(f)
    except Exception:
        existing = {}

    for p in platforms_written:
        existing[p] = {
            'platform': p,
            'file': f'context/compaction-{p}.md',
            'updated': ts,
        }

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2)


def _build_gist_content(proj: str) -> str:
    """Build a single self-contained document: system prompt + context snapshot.

    When an LLM reads this URL it gets everything — instructions AND current state.
    No separate paste required.
    """
    # Load system prompt from plugin dir
    plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(plugin_dir, 'adapters', 'cloud-llm', 'SYSTEM_PROMPT_UNIVERSAL.md')
    system_prompt = ''
    if os.path.exists(prompt_path):
        with open(prompt_path, encoding='utf-8') as f:
            # Strip the "paste this prompt" header — it's now auto-loaded
            raw = f.read()
            # Remove first 4 lines (title + paste instruction)
            lines = raw.splitlines()
            system_prompt = '\n'.join(lines[4:]).strip()

    # Load context snapshot
    generic_file = os.path.join(proj, 'context', 'compaction-generic.md')
    snapshot = ''
    if os.path.exists(generic_file):
        with open(generic_file, encoding='utf-8') as f:
            snapshot = f.read().strip()

    proj_name = os.path.basename(proj)
    import datetime
    ts = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    return f'''<!-- CI Intelligence Plugin — auto-generated context bundle -->
<!-- Fetching this URL loads both your instructions AND project context. -->
<!-- Project: {proj_name} | Updated: {ts} -->

{system_prompt}

---

## Current Project Context

{snapshot if snapshot else f'_No snapshot yet. Run `ci snapshots --generate` in {proj_name}._'}
'''


def _try_gist_push(proj: str, platform: str) -> str:
    """Push combined system-prompt+context to GitHub Gist. Returns URL or empty string on failure."""
    import urllib.request
    import urllib.error

    content = _build_gist_content(proj)

    gist_id_file = os.path.join(os.path.expanduser('~'), '.claude-intel', 'gist-id')
    gist_id = open(gist_id_file).read().strip() if os.path.exists(gist_id_file) else None

    proj_name = os.path.basename(proj)

    # Try gh CLI first (handles SSO/2FA/proxy transparently)
    try:
        import subprocess
        if gist_id:
            r = subprocess.run(
                ['gh', 'gist', 'edit', gist_id, '--filename', 'ci-context.md'],
                input=content, text=True, capture_output=True, timeout=10
            )
            if r.returncode == 0:
                return f'https://gist.github.com/{gist_id}'
        r = subprocess.run(
            ['gh', 'gist', 'create', '--secret',
             '--desc', f'CI context snapshot — {proj_name}',
             '--filename', 'ci-context.md'],
            input=content, text=True, capture_output=True, timeout=10
        )
        if r.returncode == 0:
            url = r.stdout.strip()
            new_id = url.split('/')[-1]
            os.makedirs(os.path.dirname(gist_id_file), exist_ok=True)
            open(gist_id_file, 'w').write(new_id)
            return url
    except Exception:
        pass

    # Fallback: GITHUB_TOKEN env var
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if not token:
        return ''

    payload = json.dumps({
        'description': f'CI context snapshot — {proj_name}',
        'public': False,
        'files': {'ci-context.md': {'content': content}},
    }).encode()
    headers = {
        'Authorization': f'token {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github+json',
    }
    try:
        if gist_id:
            req = urllib.request.Request(f'https://api.github.com/gists/{gist_id}',
                                         data=payload, headers=headers, method='PATCH')
        else:
            req = urllib.request.Request('https://api.github.com/gists',
                                         data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        url = data['html_url']
        os.makedirs(os.path.dirname(gist_id_file), exist_ok=True)
        open(gist_id_file, 'w').write(data['id'])
        return url
    except Exception:
        return ''


def main():
    try:
        proj = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        platform = detect_platform()

        snapshot = build_snapshot(proj, platform)

        platforms_written = [platform]
        write_snapshot(proj, snapshot, platform)

        if platform != 'generic':
            generic_snap = dict(snapshot)
            generic_snap['platform'] = 'generic'
            write_snapshot(proj, generic_snap, 'generic')
            platforms_written.append('generic')

        write_json_index(proj, platforms_written)

        print(f'\n[precompact] Snapshot saved — {_PLATFORM_PROFILES[platform]["name"]}')
        print(f'  → context/compaction-{platform}.md')
        print('  → context/compaction-generic.md')

        # Auto-push to Gist so Mode C LLMs can fetch it without manual paste
        gist_url = _try_gist_push(proj, platform)
        if gist_url:
            print(f'\n  ✓ Pushed to GitHub Gist: {gist_url}')
            print('  Paste this URL at the start of your next session — the LLM fetches it automatically.')
        else:
            print('\n  To enable auto-sync: install gh CLI → gh auth login')
            print('  Or set GITHUB_TOKEN and re-run: ci snapshots --push')

    except Exception as e:
        print(f'[precompact] warning: {e}', file=sys.stderr)
        sys.exit(0)


if __name__ == '__main__':
    main()
