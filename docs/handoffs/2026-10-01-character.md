# 2026-10-01: character, project names, editable looks

## State
- States from hooks: idle, thinking, searching, working, waiting, question, done, error;
  `blinky watch` adds sleeping. Pushes on waiting, question, done, error.
- Project name per session from `.git/config` (origin URL, worktrees followed), else folder.
- Looks are slots resolved against `~/.config/blinky/skins.json`; `blinky skins [reset]`.
- QML: BlinkyFace with gradient, shine, cheeks, catchlights, badges, cursor gaze, poke and
  dizzy; HyprlandCursor over Hyprland's socket.
- ghostly-qshell: `Agents.qml` singleton (one watcher, one cursor poll), `AgentBlinkies.qml`
  with project labels (waiting/question/error brighter and bold), `BlinkySettings.qml` page.
- Checked: 20 unit tests, qmllint, offscreen sheet of 10 looks x 10 faces, offscreen
  Quickshell harness with a copy of ghostly-qshell (bar pill + settings page rendered,
  settings edit written to skins.json and reset to a backup).

## Not checked
- The live bar: needs `qs-switch main`, not done by the agent.
- Cursor following on the real bar (the harness had no Hyprland socket).

## Next step
Restart the shell, hover and poke a blinky, change a look in Settings → Blinkies.

## Later the same day: agents view
- Sessions store `ancestors` (pids above the agent); `blinky watch` exposes `pid` and `ancestors`.
- ghostly-qshell: left click on a blinky opens the island view "Agenten" (`AgentsView.qml`):
  phone switch, every session with state, tool and its terminal window (workspace + title,
  matched via Hyprland window pids); a click focuses that window via
  `hl.dsp.focus({ window = "address:0x…" })`. Right click pokes.
- Checked: offscreen render with live data matched this session to its termo window on
  workspace 7; the focus dispatch was tried on the already focused window (returns ok) and on a
  bogus address (window not found). Clicking a row in the live bar is not checked.
