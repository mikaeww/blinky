"""Add and remove blinky's hooks in Claude Code and Codex, and put `blinky` on PATH.

Edits are merges: other hooks stay untouched, a timestamped backup is written before any
change, and an unparsable file is never overwritten.
Not here: the config file (config.py).
"""

import json
import os
import shlex
import shutil
import time
from pathlib import Path

EVENTS = {
    "claude": ("SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure",
               "Notification", "Stop", "StopFailure"),
    "codex": ("SessionStart", "SessionEnd", "UserPromptSubmit", "PreToolUse", "PostToolUse", "PermissionRequest", "Stop"),
}
HOOK_TIMEOUT_S = 10


class InstallError(Exception):
    """A hook file blinky will not touch, with the reason."""


def hook_file(agent: str) -> Path:
    """Where each agent reads user hooks from."""
    if agent == "claude":
        return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "settings.json"
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "hooks.json"


def _is_ours(hook: dict, agent: str) -> bool:
    try:
        words = shlex.split(str(hook.get("command", "")))
    except ValueError:
        return False
    return len(words) >= 3 and Path(words[0]).name == "blinky" and words[-2:] == ["hook", agent]


def _without_ours(hooks: dict, agent: str) -> dict:
    cleaned = {}
    for event, groups in hooks.items():
        kept = []
        for group in groups:
            inner = [h for h in group.get("hooks", []) if not _is_ours(h, agent)]
            if inner:
                kept.append({**group, "hooks": inner})
            elif not group.get("hooks"):
                kept.append(group)
        if kept:
            cleaned[event] = kept
    return cleaned


def merged(document: dict, agent: str, command: str | None) -> dict:
    """`document` with blinky's hooks for `agent` replaced; command None removes them."""
    hooks = document.get("hooks", {})
    if not isinstance(hooks, dict):
        raise InstallError("'hooks' is not an object")
    hooks = _without_ours(hooks, agent)
    if command:
        entry = {"type": "command", "command": f"{shlex.quote(command)} hook {agent}", "timeout": HOOK_TIMEOUT_S}
        for event in EVENTS[agent]:
            hooks.setdefault(event, []).append({"hooks": [entry]})
    result = {**document, "hooks": hooks}
    if not hooks:
        del result["hooks"]
    return result


def _read(path: Path) -> dict:
    try:
        document = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as err:
        raise InstallError(f"{path} is not valid JSON ({err}); fix it by hand, blinky will not overwrite it") from err
    if not isinstance(document, dict):
        raise InstallError(f"{path} does not hold a JSON object")
    return document


def apply(agent: str, command: str | None) -> str:
    """Install (command set) or remove (None) the hooks; returns what happened to the file."""
    path = hook_file(agent)
    document = _read(path)
    try:
        updated = merged(document, agent, command)
    except InstallError as err:
        raise InstallError(f"{path}: {err}") from err
    if updated == document:
        return "no change needed"
    outcome = "created"
    if path.exists():
        backup = path.with_name(f"{path.name}.blinky-backup-{time.strftime('%Y-%m-%d-%H%M%S')}")
        shutil.copy2(path, backup)
        outcome = f"backup: {backup}"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".blinky-tmp")
    tmp.write_text(json.dumps(updated, indent=2) + "\n")
    os.replace(tmp, path)
    return outcome


def link_command(target: Path) -> tuple[Path, str]:
    """Symlink ~/.local/bin/blinky to `target`; returns (link, what happened)."""
    link = Path.home() / ".local" / "bin" / "blinky"
    if link.is_symlink() and link.resolve() == target.resolve():
        return link, "already linked"
    if link.exists() or link.is_symlink():
        return link, "left alone: something else is already there"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)
    return link, "linked"
