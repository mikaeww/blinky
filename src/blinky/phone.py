"""Phone pushes through ntfy, and the switch that turns them on and off.

Not here: deciding when something is worth a push (hook.py).
"""

import fcntl
import json
import os
import urllib.error
import urllib.request
from contextlib import contextmanager

from .config import ConfigError, Settings, config_file, state_dir
from .hook import Push

TIMEOUT_S = 5
# How long "done" pushes wait for company before they go out as one.
BUNDLE_S = 45
# ntfy priorities: 2 low (no sound on Android), 3 default, 5 max; "off" sends nothing.
LEVELS = {"off": 0, "quiet": 2, "normal": 3, "loud": 5}
DEFAULT_LOUDNESS = {"done": "quiet", "waiting": "loud", "question": "loud", "error": "loud"}


class PhoneError(Exception):
    """The push did not reach the ntfy server."""


def _switch():
    return state_dir() / "phone"


def enabled() -> bool:
    """Pushes are off until switched on, so setting up never buzzes the phone by surprise."""
    try:
        return _switch().read_text().strip() == "on"
    except FileNotFoundError:
        return False


def set_enabled(on: bool) -> None:
    """Flip the switch; atomic so `blinky watch` never reads an empty file."""
    path = _switch()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("on\n" if on else "off\n")
    os.replace(tmp, path)


def _loudness_path():
    return config_file().parent / "loudness.json"


def loudness() -> dict[str, str]:
    """How loud each kind of push is: {kind: off|quiet|normal|loud}, defaults filled in."""
    path = _loudness_path()
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return dict(DEFAULT_LOUDNESS)
    except (OSError, json.JSONDecodeError) as err:
        raise ConfigError(f"{path}: {err}") from err
    if not isinstance(data, dict) or any(k not in DEFAULT_LOUDNESS or v not in LEVELS for k, v in data.items()):
        raise ConfigError(f"{path}: expected {{kind: level}} with kinds {list(DEFAULT_LOUDNESS)} and levels {list(LEVELS)}")
    return DEFAULT_LOUDNESS | data


def set_loudness(kind: str, level: str) -> None:
    """Change one kind; the rest stays."""
    if kind not in DEFAULT_LOUDNESS or level not in LEVELS:
        raise ConfigError(f"unknown kind {kind!r} or level {level!r}")
    path = _loudness_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(loudness() | {kind: level}))
    os.replace(tmp, path)


def priority(push: Push) -> int:
    """The ntfy priority for this push; 0 means the user wants none of this kind."""
    return LEVELS[loudness().get(push.kind, "normal")]


def send(settings: Settings, push: Push) -> None:
    """Publish via ntfy's JSON API, which takes UTF-8 titles that HTTP headers would mangle."""
    body = {
        "topic": settings.topic,
        "title": push.title,
        "message": push.message,
        "tags": [push.tags],
        "priority": priority(push) or LEVELS["normal"],
    }
    request = urllib.request.Request(
        settings.server + "/",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise PhoneError(f"ntfy {settings.server}: {err}") from err


@contextmanager
def _pending_lock():
    state_dir().mkdir(parents=True, exist_ok=True)
    with open(state_dir() / "pending.lock", "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def _pending_path():
    return state_dir() / "pending.json"


def _read_pending() -> dict:
    try:
        return json.loads(_pending_path().read_text())
    except FileNotFoundError:
        return {"flushing": False, "items": []}


def queue(push: Push) -> bool:
    """Hold a quiet push back; True when no flush is scheduled, so the caller starts one."""
    with _pending_lock():
        pending = _read_pending()
        pending["items"].append({"title": push.title, "message": push.message})
        start = not pending["flushing"]
        pending["flushing"] = True
        _pending_path().write_text(json.dumps(pending))
    return start


def bundled(items: list[dict]) -> Push | None:
    """One quiet push for everything that piled up."""
    if not items:
        return None
    if len(items) == 1:
        return Push(items[0]["title"], items[0]["message"], "white_check_mark", "done")
    projects = ", ".join(item["title"].split(" · ")[0] for item in items)
    return Push(f"{len(items)} agents are done", projects, "white_check_mark", "done")


def flush(settings: Settings) -> None:
    """Send what is pending as one push. On failure the items stay and the next push retries."""
    with _pending_lock():
        pending = _read_pending()
        pending["flushing"] = False
        _pending_path().write_text(json.dumps(pending))
    push = bundled(pending["items"])
    if push is None:
        return
    # Switched to "off" while the bundle waited: drop it instead of sending.
    if priority(push):
        send(settings, push)
    with _pending_lock():
        left = _read_pending()
        left["items"] = left["items"][len(pending["items"]):]
        _pending_path().write_text(json.dumps(left))
