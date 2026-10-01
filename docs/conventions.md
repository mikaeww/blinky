# Conventions

Derived from the clean-project rules; deviations need an ADR.

- **No dependencies.** Python standard library (3.11+) and Qt Quick / Quickshell only.
- **Limits:** 500 lines per file, 8 code files per directory (entry files and tests excluded),
  8 markdown files per docs directory, 60 lines and 5 parameters per function. Enforced by
  `tools/check.py`.
- **No dump modules:** no `utils`, `helpers`, `common` and friends.
- **Thin entry points:** `src/blinky/__main__.py` parses arguments and wires modules, nothing more.
  `bin/blinky` only puts `src/` on the path.
- **Platform code stays isolated:** `/proc` access lives in `session/process.py` and degrades to
  "unknown" elsewhere.
- **Hooks never block an agent:** they finish within the hook timeout, and on error they exit 1
  with a message (shown by the agent, appended to `errors.log`). Exit 2 is never used.
- **Fail loud:** unreadable config, unknown agent, hostile session id or a broken hook file
  raise a named error. A hook file blinky cannot parse is never overwritten.
- **Privacy:** pushes carry only the blinky name, project name, agent and the waiting tool or error kind.
- **Nothing machine-specific in the repo:** paths come from XDG variables, `CLAUDE_CONFIG_DIR`,
  `CODEX_HOME` and the location of `bin/blinky` at setup time.
- **QML:** `pragma ComponentBehavior: Bound`, no colours in the bar component beyond the skin
  colours and the eye ink; motion is a pure function of `FrameAnimation.elapsedTime` and stops
  under `reducedMotion`.
- **Language:** code, comments, docs and commits in English.
- **Check:** `tools/check.py` must pass before every commit.
