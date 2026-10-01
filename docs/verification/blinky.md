# Verification: blinky

## Claims

| # | Claim | Oracle | Method | Where |
| --- | --- | --- | --- | --- |
| 1 | Payload fields blinky reads (`hook_event_name`, `session_id`, `cwd`, `tool_name`, `notification_type`, `message`) are what the agents send | Claude Code 2.1.280 real run; Codex hooks docs (learn.chatgpt.com/docs/hooks) | Captured real Claude payloads with `tee` hooks; Codex: docs only | handoff 2026-10-01 |
| 2 | One turn pushes at most once for "waiting" and once for "done"; repeats and idle notifications do not push | Event sequence from claim 1 | Example test | `tests/test_blinky.py` |
| 3 | Running sessions never share a look while fewer than ten run | Enumeration | Exhaustive for 10 sessions | `tests/test_blinky.py` |
| 4 | No session id can escape the sessions directory | Path grammar `[A-Za-z0-9._-]`, no leading dot | Example tests with traversal ids | `tests/test_blinky.py` |
| 5 | Pushes never contain agent output | Code path: `_push_for` only reads name, cwd, agent, detail | Example test with a secret in `last_assistant_message` | `tests/test_blinky.py` |
| 6 | Installing hooks keeps foreign hooks, is idempotent, uninstall restores the original | JSON equality | Example tests | `tests/test_blinky.py` |
| 7 | An unparsable hook file is never overwritten | File content before/after | Example test | `tests/test_blinky.py` |
| 8 | Scripted runs (`claude -p`) create no session | Real `claude -p` run | Real check: no session file afterwards | handoff 2026-10-01 |
| 9 | Interactive sessions are detected | This machine's interactive `claude` | Real check via `agent_process.find/is_interactive` | handoff 2026-10-01 |
| 10 | Every look and face renders distinguishably | Human eye | Offscreen screenshot sheet, 10 looks × 10 faces | handoff 2026-10-01-character |
| 11 | The project name is the origin repo name, else the repo folder, else the folder; worktrees resolve to their main repo | git's config format | Example tests incl. ssh/https/trailing-slash URLs and a worktree | `tests/test_project.py` |
| 12 | Tool calls map to thinking / searching / working / question; StopFailure to error | Claude hooks docs | Example tests | `tests/test_blinky.py` |
| 13 | A broken skins.json never breaks hooks; watch reports it and uses the defaults | Enumerated bad inputs | Example tests | `tests/test_blinky.py` |
| 14 | Settings edits reach skins.json and running blinkies; reset keeps a backup | Files on disk | Offscreen Quickshell harness | handoff 2026-10-01-character |
| 15 | Pushes only for agents whose terminal has an awake blinky | Event sequences | Example tests | `tests/test_blinky.py` |
| 16 | One blinky per window, one window per blinky; bad slot/pid/address refused | Enumerated cases | Example tests | `tests/test_blinky.py` |
| 17 | Placements on closed terminals disappear | /proc | Example test with an impossible pid | `tests/test_blinky.py` |
| 18 | A drop over a terminal places the blinky on that window | Live Hyprland window list | Scripted drag in an offscreen harness | handoff 2026-10-01-board |

## Known gaps

- Codex payloads are checked against documentation, not a captured run. Codex skips new hooks
  until trusted in `/hooks`, so a first run without trusting shows nothing.
- `agent_process` needs `/proc`. Elsewhere sessions expire after 12 h and scripted runs are not
  filtered.
- Claude `Notification` for `permission_prompt` was not triggered in a test; it follows the docs.
