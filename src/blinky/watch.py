"""What a status bar needs to draw the blinkies, as one JSON line per change.

Not here: drawing (quickshell/Blinky). Dead sessions and placements on closed terminals are
pruned here, because a crashed agent never sends SessionEnd and a closed window says nothing.
"""

import json
import sys
import time

from . import phone, placement, skins, sound
from .config import ConfigError
from .placement import Placement
from .session import process
from .session.store import Session, Store

POLL_S = 0.5
SLEEP_AFTER_S = 10 * 60
# Without a pid there is no liveness check, so very old sessions are assumed dead.
EXPIRE_WITHOUT_PID_S = 12 * 60 * 60


def _alive(session: Session, now: float) -> bool:
    if session.pid is not None:
        return process.is_alive(session.agent, session.pid)
    return now - session.updated < EXPIRE_WITHOUT_PID_S


def _shown_state(session: Session, now: float) -> str:
    if session.state in ("done", "idle") and now - session.updated > SLEEP_AFTER_S:
        return "sleeping"
    return session.state


def _live_sessions(store: Store, now: float) -> list[Session]:
    live = []
    for session in store.all():
        if _alive(session, now):
            live.append(session)
        else:
            store.remove(session.agent, session.id)
    return live


def _session_entry(session: Session, items: list[Placement], now: float) -> dict:
    cover = placement.covering(items, session.ancestors)
    return {
        "key": f"{session.agent}-{session.id}",
        "agent": session.agent,
        "project": session.project,
        "state": _shown_state(session, now),
        "detail": session.detail,
        "pid": session.pid,
        "ancestors": session.ancestors,
        "slot": cover.slot if cover else None,
        "message": session.message,
        "since": session.since,
    }


def _remembered() -> tuple[dict[str, int], str]:
    # A broken memory file only costs the auto-placing; it is reported, the rest still shows.
    try:
        return placement.remembered(), ""
    except placement.PlacementError as err:
        return {}, str(err)


def _loudness() -> tuple[dict[str, str], str]:
    try:
        return phone.loudness(), ""
    except ConfigError as err:
        return dict(phone.DEFAULT_LOUDNESS), str(err)


def snapshot(store: Store, now: float) -> dict:
    """Looks, where each blinky sits, and the live sessions with the blinky covering them."""
    looks, error = skins.load_or_defaults()
    memory, memory_error = _remembered()
    loudness, loudness_error = _loudness()
    with store.lock():
        sessions = _live_sessions(store, now)
        items = placement.prune(store, lambda p: process.is_running(p.pid) and p.slot < len(looks))
    return {
        "phone": phone.enabled(),
        "sound": sound.enabled(),
        "loudness": loudness,
        "error": error or memory_error or loudness_error,
        "remembered": memory,
        "looks": [dict(look, slot=i) for i, look in enumerate(looks)],
        "placements": [{"slot": p.slot, "pid": p.pid, "address": p.address, "on": p.on} for p in items],
        "sessions": [_session_entry(session, items, now) for session in sessions],
    }


def run(store: Store) -> None:
    """Print a snapshot whenever it changes, forever."""
    # ponytail: polls twice a second; inotify (ctypes) if the latency or wakeups ever matter.
    last = None
    while True:
        line = json.dumps(snapshot(store, time.time()), ensure_ascii=False)
        if line != last:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
            last = line
        time.sleep(POLL_S)
