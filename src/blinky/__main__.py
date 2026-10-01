"""Command line: argument parsing and wiring only."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import config, hook, install, phone, placement, skins, sound, watch
from .session.store import AGENTS, SessionError, Store

EXECUTABLE = Path(__file__).resolve().parents[2] / "bin" / "blinky"
EXPECTED = (config.ConfigError, SessionError, install.InstallError, phone.PhoneError, placement.PlacementError,
            sound.SoundError)


def _log_error(text: str) -> None:
    """Hooks run without a visible terminal, so errors also go to a file `blinky status` points at."""
    print(f"blinky: {text}", file=sys.stderr)
    log = config.state_dir() / "errors.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as out:
        out.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}\n")


def cmd_hook(args) -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as err:
        raise SessionError(f"hook input is not JSON: {err}") from err
    if not isinstance(payload, dict):
        raise SessionError("hook input is not a JSON object")
    pid, interactive = hook.agent_pid(args.agent)
    if not interactive:
        return 0
    push = hook.handle(Store(config.runtime_dir()), args.agent, payload, time.time(), pid)
    if not push or not phone.enabled() or not phone.priority(push):
        return 0
    settings = config.load_settings()
    if settings is None:
        raise config.ConfigError("phone pushes are on but blinky is not set up; run `blinky setup`")
    if not push.bundle:
        phone.send(settings, push)
    elif phone.queue(push):
        # The agent must not wait for the bundle, so the flush runs detached.
        subprocess.Popen([sys.executable, str(EXECUTABLE), "flush"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


def cmd_flush(_args) -> int:
    time.sleep(phone.BUNDLE_S)
    settings = config.load_settings()
    if settings is None:
        raise config.ConfigError("blinky is not set up; run `blinky setup`")
    phone.flush(settings)
    return 0


def cmd_watch(_args) -> int:
    watch.run(Store(config.runtime_dir()))
    return 0


def cmd_status(_args) -> int:
    print(json.dumps(watch.snapshot(Store(config.runtime_dir()), time.time()), indent=2, ensure_ascii=False))
    print(f"config: {config.config_file()}")
    print(f"errors: {config.state_dir() / 'errors.log'}")
    return 0


def cmd_phone(args) -> int:
    if args.switch == "toggle":
        phone.set_enabled(not phone.enabled())
    elif args.switch:
        phone.set_enabled(args.switch == "on")
    print("on" if phone.enabled() else "off")
    return 0


def _install_hooks(command: str | None) -> None:
    for agent in AGENTS:
        home = install.hook_file(agent).parent
        if not home.is_dir():
            print(f"{agent}: skipped, {home} does not exist")
            continue
        outcome = install.apply(agent, command)
        verb = "installed in" if command else "removed from"
        print(f"{agent}: hooks {verb} {install.hook_file(agent)} ({outcome})")


def cmd_setup(args) -> int:
    current = config.load_settings()
    topic = args.topic or (current.topic if current else config.new_topic())
    server = (args.server or (current.server if current else config.DEFAULT_SERVER)).rstrip("/")
    path = config.write_settings(config.Settings(server=server, topic=topic))
    print(f"config: {path}")
    _install_hooks(str(EXECUTABLE))
    link, outcome = install.link_command(EXECUTABLE)
    print(f"command: {link} {outcome}")
    print(f"\nPhone: install the ntfy app and subscribe to topic '{topic}' on {server}.")
    print("Then run `blinky test`. Pushes stay off until `blinky phone on` or the bar toggle.")
    print("Codex asks you to trust new hooks once: open codex and run /hooks.")
    return 0


def cmd_uninstall(_args) -> int:
    _install_hooks(None)
    return 0


def cmd_skins(args) -> int:
    path = skins.user_file()
    if args.action == "reset" and path.exists():
        kept = path.with_name(f"skins-{time.strftime('%Y-%m-%d-%H%M%S')}.json.bak")
        path.rename(kept)
        print(f"defaults restored, your looks were moved to {kept}")
        return 0
    looks = {"path": str(path), "shapes": skins.SHAPES, "eyes": skins.EYES, "maxName": skins.MAX_NAME,
             "skins": skins.load(), "defaults": skins.DEFAULTS}
    print(json.dumps(looks, ensure_ascii=False))
    return 0


def cmd_place(args) -> int:
    store = Store(config.runtime_dir())
    if args.action == "on":
        item = placement.Placement(slot=args.slot, pid=args.pid, address=args.address, on=True)
        placement.place(store, item, len(skins.load_or_defaults()[0]))
        # The projects running in that terminal get this blinky again in their next terminal.
        projects = [s.project for s in store.all() if args.pid in s.ancestors]
        if projects:
            placement.remember(projects, args.slot)
    elif args.action == "off":
        placement.unplace(store, args.slot)
        placement.forget(args.slot)
    else:
        placement.switch(store, args.slot, args.action == "wake")
    return 0


def cmd_loudness(args) -> int:
    if args.kind:
        if not args.level:
            raise config.ConfigError("give a level: off, quiet, normal or loud")
        phone.set_loudness(args.kind, args.level)
    print(json.dumps(phone.loudness()))
    return 0


def cmd_sound(args) -> int:
    if args.switch == "toggle":
        sound.set_enabled(not sound.enabled())
    elif args.switch:
        sound.set_enabled(args.switch == "on")
    print("on" if sound.enabled() else "off")
    return 0


def cmd_chime(args) -> int:
    sound.play(args.kind)
    return 0


def cmd_test(_args) -> int:
    settings = config.load_settings()
    if settings is None:
        raise config.ConfigError("not set up yet; run `blinky setup`")
    phone.send(settings, hook.Push("blinky", "Test push. If you read this on your phone, it works.", "tada", "test"))
    print(f"sent to {settings.server}/{settings.topic}")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="blinky", description="Blinkies for your Claude Code and Codex sessions.")
    sub = root.add_subparsers(dest="command", required=True)
    hook_cmd = sub.add_parser("hook", help="called by the agent's hooks, reads the event on stdin")
    hook_cmd.add_argument("agent", choices=AGENTS)
    hook_cmd.set_defaults(run=cmd_hook)
    sub.add_parser("watch", help="print a JSON line whenever a session changes").set_defaults(run=cmd_watch)
    sub.add_parser("status", help="show sessions, phone switch and file paths").set_defaults(run=cmd_status)
    phone_cmd = sub.add_parser("phone", help="show or switch phone pushes")
    phone_cmd.add_argument("switch", nargs="?", choices=("on", "off", "toggle"))
    phone_cmd.set_defaults(run=cmd_phone)
    setup_cmd = sub.add_parser("setup", help="write config, install hooks, link the command")
    setup_cmd.add_argument("--server", help=f"ntfy server (default {config.DEFAULT_SERVER})")
    setup_cmd.add_argument("--topic", help="ntfy topic (default: keep the current one or make a random one)")
    setup_cmd.set_defaults(run=cmd_setup)
    skins_cmd = sub.add_parser("skins", help="print the looks as JSON, or reset them to the defaults")
    skins_cmd.add_argument("action", nargs="?", choices=("reset",))
    skins_cmd.set_defaults(run=cmd_skins)
    place_cmd = sub.add_parser("place", help="put a blinky on a terminal window, take it off, wake it or let it sleep")
    place_cmd.add_argument("action", choices=("on", "off", "wake", "sleep"))
    place_cmd.add_argument("slot", type=int, help="blinky number, as in `blinky skins`")
    place_cmd.add_argument("--pid", type=int, default=0, help="terminal process (for on)")
    place_cmd.add_argument("--address", default="", help="window address (for on)")
    place_cmd.set_defaults(run=cmd_place)
    loud_cmd = sub.add_parser("loudness", help="show or set how loud each kind of phone push is")
    loud_cmd.add_argument("kind", nargs="?", choices=sorted(phone.DEFAULT_LOUDNESS))
    loud_cmd.add_argument("level", nargs="?", choices=list(phone.LEVELS))
    loud_cmd.set_defaults(run=cmd_loudness)
    sound_cmd = sub.add_parser("sound", help="show or switch the chimes on this PC")
    sound_cmd.add_argument("switch", nargs="?", choices=("on", "off", "toggle"))
    sound_cmd.set_defaults(run=cmd_sound)
    chime_cmd = sub.add_parser("chime", help="play a chime (used by the bar)")
    chime_cmd.add_argument("kind", choices=sorted(sound.CHIMES))
    chime_cmd.set_defaults(run=cmd_chime)
    sub.add_parser("flush", help="internal: send held-back quiet pushes after a pause").set_defaults(run=cmd_flush)
    sub.add_parser("uninstall", help="remove blinky's hooks").set_defaults(run=cmd_uninstall)
    sub.add_parser("test", help="send a test push, even when pushes are off").set_defaults(run=cmd_test)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.run(args)
    except EXPECTED as err:
        _log_error(str(err))
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
