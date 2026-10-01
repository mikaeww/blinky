# Docs

- [conventions.md](conventions.md): binding rules for this repo
- [verification/blinky.md](verification/blinky.md): claims, oracles and how they are checked
- [decisions/](decisions/): ADRs
  - [0000-template.md](decisions/0000-template.md)
  - [0001-ntfy-instead-of-whatsapp.md](decisions/0001-ntfy-instead-of-whatsapp.md)
  - [0002-blinkies-drawn-in-qml.md](decisions/0002-blinkies-drawn-in-qml.md)
  - [0003-own-character-editable-looks.md](decisions/0003-own-character-editable-looks.md)
  - [0004-only-terminals-with-a-blinky-are-watched.md](decisions/0004-only-terminals-with-a-blinky-are-watched.md)
- [handoffs/](handoffs/): dated session handoffs, newest last
  - [2026-10-01-start.md](handoffs/2026-10-01-start.md)
  - [2026-10-01-character.md](handoffs/2026-10-01-character.md)
  - [2026-10-01-board.md](handoffs/2026-10-01-board.md)
  - [2026-10-01-bubbles.md](handoffs/2026-10-01-bubbles.md)
  - [2026-10-01-public.md](handoffs/2026-10-01-public.md)

## How it fits together

```text
Claude Code / Codex hook ──stdin JSON──> blinky hook <agent>
                                           ├─ sessions/<agent>-<id>.json  ($XDG_RUNTIME_DIR/blinky)
                                           └─ ntfy push when entering waiting/question/done/error,
                                              its terminal has an awake blinky and phone is on
status bar ──runs── blinky watch ──JSON line per change──> BlinkySessions.qml ──> BlinkyFace.qml
```

| Module | Concept |
| --- | --- |
| `src/blinky/hook.py` | event to state, which transitions push |
| `src/blinky/session/store.py` | session files, locking |
| `src/blinky/session/project.py` | project name from `.git/config` or the folder |
| `src/blinky/session/process.py` | finding the agent process (Linux /proc) |
| `src/blinky/watch.py` | snapshot for bars, pruning dead sessions |
| `src/blinky/phone.py` | ntfy and the on/off switch |
| `src/blinky/install.py` | merging hooks into agent configs |
| `src/blinky/skins.py` | default looks, the user's skins.json |
| `src/blinky/placement.py` | which blinky sits on which terminal, awake or asleep; project memory |
| `src/blinky/sound.py` | synthesised chimes and their switch |
| `src/blinky/config.py` | file locations, config.toml |

| QML (`quickshell/Blinky`) | Concept |
| --- | --- |
| `BlinkySessions.qml` | runs `blinky watch`, phone switch |
| `BlinkyFace.qml` | one blinky: expression, gaze, motion, poke |
| `BlinkyEyes.qml`, `BlinkyBadge.qml` | eyes and status bubble (internal) |
| `BlinkyGeometry.js` | body outlines, deterministic noise |
| `HyprlandWindows.qml` | Hyprland cursor, visible windows, window under a point |
| `TerminalBlinkies.qml` | placed blinkies in their terminals' corners, speech bubbles, chimes |
| `BlinkyBubble.qml` | the speech bubble (internal) |
| `board/` | the blinky board: window, surface (card, drag and drop), tile, controls |
