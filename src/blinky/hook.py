"""Turn one agent hook event into a session update and, on the right transitions, a push.

Claude Code and Codex share event names and payload fields, so one table serves both.
Not here: how the push is delivered (phone.py) or where sessions live (session/store.py).
"""

import os
import shlex
from dataclasses import dataclass

from . import placement, skins
from .session import process, project
from .session.store import Session, Store

# Tools that only look at things; everything else counts as working.
LOOKING_TOOLS = {"Read", "Grep", "Glob", "LS", "WebSearch", "WebFetch", "ToolSearch", "web_search", "view_image"}
LOOKING_COMMANDS = {"rg", "grep", "cat", "ls", "find", "fd", "head", "tail", "tree", "wc", "stat", "less"}
QUESTION_TOOLS = {"AskUserQuestion", "request_user_input"}
# Claude reports "waiting for you" as a Notification, Codex as a PermissionRequest.
NOTIFICATION_STATES = {"permission_prompt": "waiting", "elicitation_dialog": "question"}
PUSH_STATES = {"waiting", "question", "done", "error"}
MESSAGE_CHARS = 600


@dataclass(frozen=True)
class Push:
    """A phone message. Only names, tool names and error kinds, never agent output or commands."""

    title: str
    message: str
    tags: str
    # done, waiting, question or error: picks the loudness the user set for it.
    kind: str
    # "Done" is not urgent: such pushes wait a little and go out together.
    bundle: bool = False


def _first_command_word(tool_input: object) -> str:
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if isinstance(command, list):
        command = " ".join(str(part) for part in command)
    try:
        words = shlex.split(command) if isinstance(command, str) else []
    except ValueError:
        words = command.split()
    return os.path.basename(words[0]) if words else ""


def _tool_state(payload: dict) -> str:
    tool = str(payload.get("tool_name", ""))
    if tool in QUESTION_TOOLS:
        return "question"
    if tool in LOOKING_TOOLS or _first_command_word(payload.get("tool_input")) in LOOKING_COMMANDS:
        return "searching"
    return "working"


def _next_state(payload: dict) -> tuple[str, str | None] | None:
    """(state, detail) for this event, or None when the event changes nothing.

    A detail of None keeps the previous one: Claude's permission Notification names no tool,
    the PreToolUse right before it did.
    """
    event = payload.get("hook_event_name", "")
    tool = str(payload.get("tool_name", ""))
    if event == "SessionStart":
        return "idle", ""
    if event == "UserPromptSubmit" or event in ("PostToolUse", "PostToolUseFailure"):
        return "thinking", ""
    if event == "PreToolUse":
        return _tool_state(payload), tool
    if event == "PermissionRequest":
        return "waiting", tool
    if event == "Notification" and payload.get("notification_type") in NOTIFICATION_STATES:
        return NOTIFICATION_STATES[payload["notification_type"]], None
    if event == "Stop":
        return "done", ""
    if event == "StopFailure":
        return "error", str(payload.get("error_type", "unknown"))
    return None


def _push_for(session: Session, slot: int) -> Push:
    # A broken skins.json must not break the agent's hooks; `blinky watch` reports it in the bar.
    looks = skins.load_or_defaults()[0]
    title = f"{session.project} · {looks[slot % len(looks)]['name']}"
    agent = session.agent.capitalize()
    if session.state == "waiting":
        return Push(title, f"{agent} needs your OK: {session.detail or 'a tool'}", "raised_hand", "waiting")
    if session.state == "question":
        return Push(title, f"{agent} has a question", "grey_question", "question")
    if session.state == "error":
        return Push(title, f"{agent} stopped: {session.detail.replace('_', ' ')}", "warning", "error")
    return Push(title, f"{agent} is done", "white_check_mark", "done", bundle=True)


def _new_session(agent: str, payload: dict, pid: int | None, now: float) -> Session:
    cwd = str(payload.get("cwd") or "")
    return Session(
        agent=agent,
        id=payload["session_id"],
        cwd=cwd,
        project=project.name_for(cwd) if cwd else agent,
        pid=pid,
        state="idle",
        detail="",
        started=now,
        updated=now,
        ancestors=process.ancestors(pid) if pid else [],
    )


def handle(store: Store, agent: str, payload: dict, now: float, pid: int | None) -> Push | None:
    """Apply one event; return the push to send when a watched session newly needs attention."""
    session_id = str(payload.get("session_id", ""))
    if payload.get("hook_event_name") == "SessionEnd":
        with store.lock():
            store.remove(agent, session_id)
        return None
    change = _next_state(payload)
    if change is None:
        return None
    with store.lock():
        existing = store.get(agent, session_id)
        session = existing or _new_session(agent, payload, pid, now)
        before = existing.state if existing else None
        cwd = str(payload.get("cwd") or "")
        if cwd and cwd != session.cwd:
            session.cwd, session.project = cwd, project.name_for(cwd)
        if before != change[0]:
            session.since = now
        session.state, session.updated = change[0], now
        if payload.get("hook_event_name") == "Stop":
            session.message = str(payload.get("last_assistant_message") or "")[:MESSAGE_CHARS]
        session.detail = session.detail if change[1] is None else change[1]
        session.pid = session.pid or pid
        if session.pid and not session.ancestors:
            session.ancestors = process.ancestors(session.pid)
        store.put(session)
        if session.state not in PUSH_STATES or before == session.state:
            return None
        # Only terminals with a blinky that is switched on are watched.
        cover = placement.covering(placement.load(store), session.ancestors)
    return _push_for(session, cover.slot) if cover and cover.on else None


def agent_pid(agent: str) -> tuple[int | None, bool]:
    """(pid of the agent that called us, whether a person is driving it)."""
    pid = process.find(agent, os.getppid())
    if pid is None:
        return None, True
    return pid, process.is_interactive(agent, pid)
