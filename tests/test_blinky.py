import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from blinky import hook, install, phone, placement, skins, sound, watch  # noqa: E402
from blinky.config import ConfigError  # noqa: E402
from blinky.session.store import SessionError, Store  # noqa: E402


def event(name, session="s1", **extra):
    return {"hook_event_name": name, "session_id": session, "cwd": "/work/demo", **extra}


def put(store, slot, pid, address):
    placement.place(store, placement.Placement(slot=slot, pid=pid, address=address, on=True), len(skins.DEFAULTS))


class TempHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.saved = {var: os.environ.get(var) for var in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME")}
        for var in self.saved:
            os.environ[var] = str(self.root / var.lower())
        self.store = Store(self.root / "run")

    def tearDown(self):
        for var, value in self.saved.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
        self.tmp.cleanup()

    def run_events(self, agent, *events):
        # Our own process stands in for the agent, so our parent stands in for its terminal.
        return [hook.handle(self.store, agent, e, now=100.0 + i, pid=os.getpid()) for i, e in enumerate(events)]

    def cover(self, slot=0):
        put(self.store, slot, os.getppid(), "0xabc")

    def states(self, agent, *events):
        result = []
        for i, e in enumerate(events):
            hook.handle(self.store, agent, e, now=100.0 + i, pid=None)
            result.append(self.store.get(agent, e["session_id"]).state)
        return result


class HookTests(TempHome):
    def test_claude_turn_pushes_once_for_waiting_and_once_for_done(self):
        self.cover(slot=3)
        pushes = self.run_events(
            "claude",
            event("SessionStart"),
            event("UserPromptSubmit"),
            event("PreToolUse", tool_name="Bash", tool_input={"command": "make"}),
            event("Notification", notification_type="permission_prompt", message="Claude needs your permission"),
            event("Notification", notification_type="permission_prompt", message="again"),
            event("PostToolUse", tool_name="Bash"),
            event("Stop"),
            event("Notification", notification_type="idle_prompt", message="waiting for input"),
        )
        sent = [p for p in pushes if p]
        self.assertEqual([p.message for p in sent], ["Claude needs your OK: Bash", "Claude is done"])
        self.assertEqual(sent[0].title, "demo · " + skins.DEFAULTS[3]["name"])

    def test_states_follow_what_the_agent_does(self):
        got = self.states(
            "claude",
            event("UserPromptSubmit"),
            event("PreToolUse", tool_name="Grep"),
            event("PostToolUse", tool_name="Grep"),
            event("PreToolUse", tool_name="Bash", tool_input={"command": "rg -n foo src"}),
            event("PreToolUse", tool_name="Edit"),
            event("PreToolUse", tool_name="AskUserQuestion"),
            event("StopFailure", error_type="rate_limit"),
        )
        self.assertEqual(got, ["thinking", "searching", "thinking", "searching", "working", "question", "error"])

    def test_codex_shell_command_lists_count_as_searching(self):
        got = self.states("codex", event("PreToolUse", tool_name="shell", tool_input={"command": ["cat", "README.md"]}))
        self.assertEqual(got, ["searching"])

    def test_codex_permission_request_waits(self):
        self.cover()
        pushes = self.run_events("codex", event("PreToolUse", tool_name="shell"), event("PermissionRequest", tool_name="shell"))
        self.assertIsNone(pushes[0])
        self.assertEqual(pushes[1].message, "Codex needs your OK: shell")

    def test_question_and_error_push(self):
        self.cover()
        pushes = self.run_events("claude", event("PreToolUse", tool_name="AskUserQuestion"), event("StopFailure", error_type="rate_limit"))
        self.assertEqual([p.message for p in pushes], ["Claude has a question", "Claude stopped: rate limit"])

    def test_push_never_carries_agent_output_or_commands(self):
        self.cover()
        pushes = self.run_events(
            "codex",
            event("PermissionRequest", tool_name="shell", tool_input={"command": "export SECRET=hunter2"}),
            event("Stop", last_assistant_message="SECRET=hunter2"),
        )
        for push in pushes:
            self.assertNotIn("hunter2", push.title + push.message)

    def test_uncovered_or_sleeping_terminals_never_push(self):
        self.assertEqual(self.run_events("claude", event("Stop", session="a")), [None])
        self.cover()
        placement.switch(self.store, 0, False)
        self.assertEqual(self.run_events("claude", event("Stop", session="b")), [None])
        placement.switch(self.store, 0, True)
        self.assertIsNotNone(self.run_events("claude", event("Stop", session="c"))[0])

    def test_session_end_forgets_the_session(self):
        self.run_events("claude", event("SessionStart"), event("SessionEnd"))
        self.assertEqual(self.store.all(), [])

    def test_hostile_session_ids_are_refused(self):
        for bad in ("../../etc/passwd", "", ".hidden", "a/b", "x" * 200):
            with self.assertRaises(SessionError, msg=bad):
                hook.handle(self.store, "claude", event("Stop", session=bad), now=1.0, pid=None)

    def test_dead_and_expired_sessions_are_pruned(self):
        hook.handle(self.store, "claude", event("SessionStart", session="dead"), now=1.0, pid=2**22 + 7)
        hook.handle(self.store, "claude", event("SessionStart", session="old"), now=1.0, pid=None)
        hook.handle(self.store, "claude", event("Stop", session="fresh"), now=watch.EXPIRE_WITHOUT_PID_S, pid=None)
        shown = watch.snapshot(self.store, now=watch.EXPIRE_WITHOUT_PID_S + 10)["sessions"]
        self.assertEqual([s["key"] for s in shown], ["claude-fresh"])


class TerminalTests(TempHome):
    def test_session_remembers_the_processes_above_the_agent(self):
        hook.handle(self.store, "claude", event("SessionStart"), now=1.0, pid=os.getpid())
        self.assertEqual(self.store.get("claude", "s1").ancestors[0], os.getppid())

    def test_late_pid_fills_in_the_ancestors(self):
        hook.handle(self.store, "claude", event("SessionStart"), now=1.0, pid=None)
        hook.handle(self.store, "claude", event("Stop"), now=2.0, pid=os.getpid())
        self.assertEqual(self.store.get("claude", "s1").ancestors[0], os.getppid())


class QuietTests(TempHome):
    def test_done_is_quiet_and_bundled_attention_is_loud(self):
        self.cover()
        pushes = self.run_events("claude", event("PreToolUse", tool_name="AskUserQuestion"), event("Stop"))
        self.assertEqual([(phone.priority(p), p.bundle) for p in pushes], [(5, False), (2, True)])

    def test_loudness_is_set_per_kind_and_off_means_no_push(self):
        phone.set_loudness("done", "off")
        phone.set_loudness("waiting", "normal")
        self.assertEqual(phone.loudness(), {"done": "off", "waiting": "normal", "question": "loud", "error": "loud"})
        done = hook.Push("t", "m", "x", "done", bundle=True)
        self.assertEqual((phone.priority(done), phone.priority(hook.Push("t", "m", "x", "waiting"))), (0, 3))
        self.assertEqual(phone.priority(hook.Push("t", "m", "x", "test")), 3)
        with self.assertRaises(ConfigError):
            phone.set_loudness("done", "deafening")

    def test_broken_loudness_file_fails_loud_and_watch_falls_back(self):
        path = Path(os.environ["XDG_CONFIG_HOME"]) / "blinky" / "loudness.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"done": "whisper"}')
        with self.assertRaises(ConfigError):
            phone.loudness()
        shown = watch.snapshot(self.store, now=1.0)
        self.assertEqual((shown["loudness"], bool(shown["error"])), (phone.DEFAULT_LOUDNESS, True))

    def test_pending_pushes_go_out_as_one_and_survive_a_failed_send(self):
        done = [hook.Push(f"{name} · Pip", "Claude is done", "white_check_mark", "done", bundle=True) for name in ("rewa", "filyy")]
        self.assertTrue(phone.queue(done[0]))
        self.assertFalse(phone.queue(done[1]))
        sent, original = [], phone.send

        def failing(settings, push):
            raise phone.PhoneError("offline")
        phone.send = failing
        try:
            with self.assertRaises(phone.PhoneError):
                phone.flush(None)
            self.assertTrue(phone.queue(done[0]), "after a failed send the next push must start a flush")
            phone.send = lambda settings, push: sent.append(push)
            phone.flush(None)
        finally:
            phone.send = original
        self.assertEqual([(p.title, p.message) for p in sent], [("3 agents are done", "rewa, filyy, rewa")])
        phone.flush(None)
        self.assertEqual(len(sent), 1, "nothing left to send")

    def test_last_answer_and_state_start_are_kept(self):
        self.run_events("claude", event("UserPromptSubmit"), event("PreToolUse", tool_name="Read"), event("Stop", last_assistant_message="x" * 900))
        session = self.store.get("claude", "s1")
        self.assertEqual((len(session.message), session.since), (hook.MESSAGE_CHARS, 102.0))

    def test_chimes_are_short_and_never_clip(self):
        for kind in sound.CHIMES:
            pcm = sound.samples(kind)
            peak = max(abs(int.from_bytes(pcm[i:i + 2], "little", signed=True)) for i in range(0, len(pcm), 2))
            self.assertLess(len(pcm) / 2 / sound.RATE, 0.6, kind)
            self.assertLessEqual(peak, 32767 * sound.VOLUME + 1, kind)


class PlacementTests(TempHome):
    def test_projects_are_remembered_until_released_by_hand(self):
        placement.remember(["rewa", "filyy"], 3)
        placement.remember(["rewa"], 5)
        self.assertEqual(placement.remembered(), {"filyy": 3, "rewa": 5})
        placement.forget(3)
        self.assertEqual(placement.remembered(), {"rewa": 5})

    def test_one_blinky_per_window_and_one_window_per_blinky(self):
        put(self.store, 0, 100, "0xaa")
        put(self.store, 1, 200, "0xbb")
        put(self.store, 2, 100, "aa")
        put(self.store, 1, 300, "0xcc")
        got = sorted((p.slot, p.address) for p in placement.load(self.store))
        self.assertEqual(got, [(1, "cc"), (2, "aa")])
        placement.unplace(self.store, 2)
        self.assertEqual([p.slot for p in placement.load(self.store)], [1])

    def test_bad_requests_are_refused(self):
        for slot, pid, address in ((99, 100, "aa"), (-1, 100, "aa"), (0, 1, "aa"), (0, 100, "zz; rm"), (0, 100, "")):
            with self.assertRaises(placement.PlacementError, msg=(slot, pid, address)):
                put(self.store, slot, pid, address)
        with self.assertRaises(placement.PlacementError):
            placement.switch(self.store, 0, False)

    def test_watch_shows_cover_and_drops_closed_terminals(self):
        self.cover(slot=4)
        put(self.store, 5, 2**22 + 9, "0xdead")
        # Without a pid the session survives the liveness check; its terminal is our parent.
        hook.handle(self.store, "claude", event("SessionStart"), now=100.0, pid=None)
        session = self.store.get("claude", "s1")
        session.ancestors = [os.getppid()]
        self.store.put(session)
        shown = watch.snapshot(self.store, now=101.0)
        self.assertEqual([p["slot"] for p in shown["placements"]], [4])
        self.assertEqual(shown["sessions"][0]["slot"], 4)
        self.assertEqual(len(shown["looks"]), len(skins.DEFAULTS))


class SkinTests(TempHome):
    def write_skins(self, data):
        path = skins.user_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def test_edited_look_is_served_at_once(self):
        self.write_skins([{"name": "Bob", "color": "#123456", "shape": "cloud", "eyes": "wide"}])
        shown = watch.snapshot(self.store, now=101.0)
        self.assertEqual((shown["looks"][0]["name"], shown["error"]), ("Bob", ""))

    def test_invalid_skins_fail_loud_and_watch_falls_back(self):
        for bad in ([], [{"name": "", "color": "#123456", "shape": "cloud", "eyes": "wide"}],
                    [{"name": "A", "color": "red", "shape": "cloud", "eyes": "wide"}],
                    [{"name": "A", "color": "#123456", "shape": "star", "eyes": "wide"}], {"name": "A"}):
            self.write_skins(bad)
            with self.assertRaises(ConfigError, msg=bad):
                skins.load()
        shown = watch.snapshot(self.store, now=101.0)
        self.assertTrue(shown["error"])
        self.assertEqual([look["name"] for look in shown["looks"]], [s["name"] for s in skins.DEFAULTS])


class InstallTests(unittest.TestCase):
    def test_merge_keeps_foreign_hooks_and_is_idempotent(self):
        foreign = {"type": "command", "command": "node other.js"}
        doc = {"model": "x", "hooks": {"Stop": [{"hooks": [foreign]}]}}
        once = install.merged(doc, "claude", "/opt/blinky/bin/blinky")
        twice = install.merged(once, "claude", "/opt/blinky/bin/blinky")
        self.assertEqual(once, twice)
        self.assertEqual(once["model"], "x")
        self.assertIn(foreign, [h for g in once["hooks"]["Stop"] for h in g["hooks"]])
        self.assertEqual(set(once["hooks"]), set(install.EVENTS["claude"]))
        self.assertEqual(install.merged(once, "claude", None), doc)

    def test_broken_hook_file_is_left_alone(self):
        with tempfile.TemporaryDirectory() as home:
            settings = Path(home) / "settings.json"
            settings.write_text("{ not json")
            os.environ["CLAUDE_CONFIG_DIR"] = home
            try:
                with self.assertRaises(install.InstallError):
                    install.apply("claude", "/opt/blinky/bin/blinky")
            finally:
                del os.environ["CLAUDE_CONFIG_DIR"]
            self.assertEqual(settings.read_text(), "{ not json")


class CommandTests(unittest.TestCase):
    def test_hook_command_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "XDG_RUNTIME_DIR": tmp, "XDG_STATE_HOME": tmp, "XDG_CONFIG_HOME": tmp}
            blinky = [sys.executable, str(ROOT / "bin" / "blinky")]
            done = subprocess.run([*blinky, "hook", "claude"], input=json.dumps(event("Stop")), env=env, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            status = subprocess.run([*blinky, "status"], env=env, capture_output=True, text=True)
            self.assertIn('"state": "done"', status.stdout)
            broken = subprocess.run([*blinky, "hook", "claude"], input="nope", env=env, capture_output=True, text=True)
            self.assertEqual(broken.returncode, 1)
            self.assertIn("not JSON", (Path(tmp) / "blinky" / "errors.log").read_text())


if __name__ == "__main__":
    unittest.main()
