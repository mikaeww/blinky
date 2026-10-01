"""Where blinky keeps its files and what the user configured.

Not here: session state (sessions.py) or sending pushes (phone.py).
"""

import json
import os
import re
import secrets
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SERVER = "https://ntfy.sh"
TOPIC = re.compile(r"[A-Za-z0-9_-]{1,64}")


class ConfigError(Exception):
    """The config file exists but cannot be used as written."""


@dataclass(frozen=True)
class Settings:
    """Where phone pushes go."""

    server: str
    topic: str


def _xdg(var: str, fallback: str) -> Path:
    return Path(os.environ.get(var) or Path.home() / fallback)


def runtime_dir() -> Path:
    """Live session files. tmpfs on most systems, so a reboot clears dead sessions."""
    base = os.environ.get("XDG_RUNTIME_DIR") or Path(tempfile.gettempdir()) / f"blinky-{os.getuid()}"
    return Path(base) / "blinky"


def state_dir() -> Path:
    """State that should survive a reboot: the phone switch and the error log."""
    return _xdg("XDG_STATE_HOME", ".local/state") / "blinky"


def config_file() -> Path:
    """The user's config.toml."""
    return _xdg("XDG_CONFIG_HOME", ".config") / "blinky" / "config.toml"


def load_settings() -> Settings | None:
    """Read config.toml; None when blinky has not been set up yet."""
    path = config_file()
    try:
        data = tomllib.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, tomllib.TOMLDecodeError) as err:
        raise ConfigError(f"{path}: {err}") from err
    ntfy = data.get("ntfy", {})
    settings = Settings(server=str(ntfy.get("server", DEFAULT_SERVER)).rstrip("/"), topic=str(ntfy.get("topic", "")))
    validate(settings, path)
    return settings


def validate(settings: Settings, where: Path | str) -> None:
    """Reject settings that would send pushes somewhere unintended."""
    if not TOPIC.fullmatch(settings.topic):
        raise ConfigError(f"{where}: ntfy topic must be 1-64 of A-Z a-z 0-9 _ -, got {settings.topic!r}")
    if not settings.server.startswith(("https://", "http://")):
        raise ConfigError(f"{where}: ntfy server must be an http(s) URL, got {settings.server!r}")


def new_topic() -> str:
    """A topic nobody can guess: ntfy topics are readable by anyone who knows the name."""
    return "blinky-" + secrets.token_urlsafe(15)


def write_settings(settings: Settings) -> Path:
    """Write config.toml, readable only by the user since the topic is the secret."""
    validate(settings, "settings")
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    # JSON string escaping is valid TOML basic-string escaping for these values.
    body = f"[ntfy]\nserver = {json.dumps(settings.server)}\ntopic = {json.dumps(settings.topic)}\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(body)
    return path
