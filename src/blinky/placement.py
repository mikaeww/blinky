"""Which blinky sits on which terminal window, and whether it is switched on.

Only terminals with a blinky are watched: their agents get a blinky in the bar and phone pushes.
Written through `blinky place / unplace / switch`, read by hooks and `blinky watch`.
Not here: finding windows on screen (the bar does that, it knows the compositor).
"""

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import state_dir
from .session.store import Store

# Hyprland window addresses, with or without the 0x prefix.
ADDRESS = re.compile(r"(0x)?[0-9a-fA-F]{1,16}")


class PlacementError(Exception):
    """A placement request or file blinky cannot use."""


@dataclass
class Placement:
    """Blinky `slot` sits on the window `address`, owned by terminal process `pid`."""

    slot: int
    pid: int
    address: str
    on: bool


def _path(store: Store) -> Path:
    return store.root / "placements.json"


def load(store: Store) -> list[Placement]:
    """All placements; none when nothing was placed yet."""
    path = _path(store)
    try:
        data = json.loads(path.read_text())
        return [Placement(**item) for item in data]
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError, TypeError) as err:
        raise PlacementError(f"{path}: unreadable placements: {err}") from err


def _save(store: Store, items: list[Placement]) -> None:
    path = _path(store)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps([asdict(item) for item in items]))
    os.replace(tmp, path)


def _validated(slot: int, pid: int, address: str, slots: int) -> str:
    if not 0 <= slot < slots:
        raise PlacementError(f"blinky {slot} does not exist, there are {slots}")
    if pid <= 1:
        raise PlacementError(f"refusing terminal pid {pid}")
    if not ADDRESS.fullmatch(address):
        raise PlacementError(f"refusing window address {address!r}")
    return address.lower().removeprefix("0x")


def place(store: Store, item: Placement, slots: int) -> None:
    """Put a blinky on a window; a blinky already there goes back into the box."""
    address = _validated(item.slot, item.pid, item.address, slots)
    with store.lock():
        kept = [p for p in load(store) if p.slot != item.slot and p.address != address]
        _save(store, kept + [Placement(slot=item.slot, pid=item.pid, address=address, on=item.on)])


def unplace(store: Store, slot: int) -> None:
    """Take a blinky back into the box; taking an unplaced one is fine."""
    with store.lock():
        _save(store, [p for p in load(store) if p.slot != slot])


def switch(store: Store, slot: int, on: bool) -> None:
    """Wake a placed blinky (pushes) or let it sleep (no pushes)."""
    with store.lock():
        items = load(store)
        if not any(p.slot == slot for p in items):
            raise PlacementError(f"blinky {slot} is not on a terminal")
        _save(store, [Placement(p.slot, p.pid, p.address, on if p.slot == slot else p.on) for p in items])


def prune(store: Store, keep) -> list[Placement]:
    """Drop the placements `keep` rejects (closed terminals); the caller holds the lock."""
    items = load(store)
    kept = [p for p in items if keep(p)]
    if len(kept) != len(items):
        _save(store, kept)
    return kept


def covering(items: list[Placement], ancestors: list[int]) -> Placement | None:
    """The blinky on the terminal an agent runs in: the first placed pid among its ancestors."""
    # ponytail: matched by process, so a terminal that owns several windows (kitty single-instance)
    # counts as one; per-window needs a tty-to-window mapping from the terminal.
    by_pid = {p.pid: p for p in items}
    return next((by_pid[pid] for pid in ancestors if pid in by_pid), None)


def _memory_path() -> Path:
    # Survives reboots, unlike placements: the point is to find the project again later.
    return state_dir() / "remembered.json"


def remembered() -> dict[str, int]:
    """Which blinky each project had last: {project name: slot}."""
    try:
        data = json.loads(_memory_path().read_text())
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as err:
        raise PlacementError(f"{_memory_path()}: {err}") from err
    return {str(k): int(v) for k, v in data.items()}


def _save_memory(memory: dict[str, int]) -> None:
    path = _memory_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(memory))
    os.replace(tmp, path)


def remember(projects: list[str], slot: int) -> None:
    """These projects get blinky `slot` again when their agent starts in a new terminal."""
    memory = {project: s for project, s in remembered().items() if s != slot and project not in projects}
    _save_memory(memory | {project: slot for project in projects})


def forget(slot: int) -> None:
    """Released by hand: the blinky no longer comes back to its projects."""
    _save_memory({project: s for project, s in remembered().items() if s != slot})
