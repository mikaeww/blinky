"""Find the agent process behind a hook call, via Linux /proc.

Not portable: on systems without /proc every lookup returns None and blinky falls back to
treating the session as interactive and expiring it by age.
"""

from pathlib import Path

# Flags that mean "scripted run, nobody is watching": no blinky, no push.
HEADLESS_ARGS = {"claude": {"-p", "--print"}, "codex": {"exec"}}
MAX_DEPTH = 16


def _parent(pid: int) -> int:
    stat = Path(f"/proc/{pid}/stat").read_text()
    # The command name in field 2 may contain spaces and parens, so split after the last ")".
    return int(stat.rsplit(")", 1)[1].split()[1])


def _comm(pid: int) -> str:
    return Path(f"/proc/{pid}/comm").read_text().strip()


def find(agent: str, start: int) -> int | None:
    """The nearest ancestor of `start` whose process name is `agent`."""
    pid = start
    for _ in range(MAX_DEPTH):
        try:
            if _comm(pid) == agent:
                return pid
            pid = _parent(pid)
        except (OSError, ValueError, IndexError):
            return None
        if pid <= 1:
            return None
    return None


def ancestors(pid: int) -> list[int]:
    """Parent, grandparent, ... of `pid`: one of them is the terminal window's process."""
    chain = []
    for _ in range(MAX_DEPTH):
        try:
            pid = _parent(pid)
        except (OSError, ValueError, IndexError):
            break
        if pid <= 1:
            break
        chain.append(pid)
    return chain


def is_interactive(agent: str, pid: int) -> bool:
    """True when a person drives this agent in a terminal."""
    try:
        args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        stdin = Path(f"/proc/{pid}/fd/0").readlink()
    except OSError:
        return True
    words = {arg.decode(errors="replace") for arg in args[1:]}
    if words & HEADLESS_ARGS.get(agent, set()):
        return False
    return str(stdin).startswith(("/dev/pts/", "/dev/tty"))


def is_alive(agent: str, pid: int) -> bool:
    """The process still exists and still is the agent (pids get reused)."""
    try:
        return _comm(pid) == agent
    except OSError:
        return False


def is_running(pid: int) -> bool:
    """The process exists (whatever it is now)."""
    return Path(f"/proc/{pid}").exists()
