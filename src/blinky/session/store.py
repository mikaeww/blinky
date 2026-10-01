"""Session store: one JSON file per running agent session.

Not here: what hook events mean (hook.py) or which blinky covers it (placement.py).
Every read-modify-write runs under `Store.lock()` because several agents fire hooks at once.
"""

import fcntl
import json
import os
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

SESSION_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")
AGENTS = ("claude", "codex")


class SessionError(Exception):
    """A session id or agent name that must not become a file name."""


@dataclass
class Session:
    """One running agent instance."""

    agent: str
    id: str
    cwd: str
    project: str
    pid: int | None
    state: str
    detail: str
    started: float
    updated: float
    # Processes above the agent; a bar matches them against window pids to find the terminal.
    ancestors: list[int] = field(default_factory=list)
    # The agent's last answer (shortened) for the speech bubble; stays on this machine.
    message: str = ""
    # When the current state began, so a bar knows whether the user has looked since.
    since: float = 0.0


def _session(data: dict) -> Session:
    # Files written by an older blinky may carry fields that no longer exist.
    known = {f.name for f in fields(Session)}
    return Session(**{key: value for key, value in data.items() if key in known})


def _check(agent: str, session_id: str) -> None:
    if agent not in AGENTS:
        raise SessionError(f"unknown agent {agent!r}, expected one of {AGENTS}")
    if not SESSION_ID.fullmatch(session_id) or session_id.startswith("."):
        raise SessionError(f"refusing session id {session_id!r}")


class Store:
    """Session files under one directory."""

    def __init__(self, root: Path):
        self.root = root

    def _path(self, agent: str, session_id: str) -> Path:
        _check(agent, session_id)
        return self.root / "sessions" / f"{agent}-{session_id}.json"

    @contextmanager
    def lock(self):
        """Exclusive lock across processes for the duration of the block."""
        (self.root / "sessions").mkdir(parents=True, exist_ok=True, mode=0o700)
        with open(self.root / "lock", "w") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def get(self, agent: str, session_id: str) -> Session | None:
        """The stored session, or None if it is unknown."""
        try:
            return _session(json.loads(self._path(agent, session_id).read_text()))
        except FileNotFoundError:
            return None

    def put(self, session: Session) -> None:
        """Write atomically so a reader never sees half a file."""
        path = self._path(session.agent, session.id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(session)))
        os.replace(tmp, path)

    def remove(self, agent: str, session_id: str) -> None:
        """Forget a session; forgetting an unknown one is fine."""
        self._path(agent, session_id).unlink(missing_ok=True)

    def all(self) -> list[Session]:
        """Every stored session, oldest first."""
        found = []
        for path in (self.root / "sessions").glob("*.json"):
            try:
                found.append(_session(json.loads(path.read_text())))
            except FileNotFoundError:
                # Removed by a SessionEnd between glob and read.
                continue
            except (json.JSONDecodeError, TypeError) as err:
                raise SessionError(f"{path}: unreadable session file: {err}") from err
        return sorted(found, key=lambda s: (s.started, s.id))
