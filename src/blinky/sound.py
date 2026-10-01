"""Short chimes for the PC side, synthesised once and played with whatever player exists.

No sound files in the repository: each chime is a few sine notes written to the cache on
first use. Not here: deciding when to chime (the bar does that).
"""

import math
import os
import shutil
import struct
import subprocess
import wave
from pathlib import Path

from .config import state_dir

RATE = 44100
# Notes per chime as (frequency in Hz, seconds).
CHIMES = {
    "done": [(1046.5, 0.11), (1318.5, 0.22)],
    "attention": [(880.0, 0.08), (880.0, 0.08), (1318.5, 0.2)],
    "error": [(659.3, 0.14), (523.3, 0.26)],
}
PLAYERS = (("pw-play", []), ("paplay", []), ("aplay", ["-q"]))
VOLUME = 0.22


class SoundError(Exception):
    """A chime that cannot be played, with the reason."""


def _switch() -> Path:
    return state_dir() / "sound"


def enabled() -> bool:
    """Chimes are on unless switched off."""
    try:
        return _switch().read_text().strip() != "off"
    except FileNotFoundError:
        return True


def set_enabled(on: bool) -> None:
    """Flip the switch; atomic so `blinky watch` never reads an empty file."""
    path = _switch()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("on\n" if on else "off\n")
    os.replace(tmp, path)


def samples(kind: str) -> bytes:
    """16-bit mono PCM: each note fades in over 5 ms and decays, so nothing clicks."""
    frames = bytearray()
    for frequency, seconds in CHIMES[kind]:
        count = int(RATE * seconds)
        for i in range(count):
            t = i / RATE
            envelope = min(1.0, t / 0.005) * math.exp(-5 * t / seconds)
            value = VOLUME * envelope * math.sin(2 * math.pi * frequency * t)
            frames += struct.pack("<h", int(value * 32767))
    return bytes(frames)


def _file(kind: str) -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "blinky"
    path = cache / f"chime-{kind}.wav"
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(RATE)
            out.writeframes(samples(kind))
    return path


def play(kind: str) -> None:
    """Play a chime with the first player found; does nothing while sounds are off."""
    if kind not in CHIMES:
        raise SoundError(f"unknown chime {kind!r}, expected one of {sorted(CHIMES)}")
    if not enabled():
        return
    for player, flags in PLAYERS:
        if shutil.which(player):
            result = subprocess.run([player, *flags, str(_file(kind))], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise SoundError(f"{player} failed: {result.stderr.strip() or result.returncode}")
            return
    raise SoundError("no audio player found (pw-play, paplay or aplay)")
