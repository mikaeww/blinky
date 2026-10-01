import QtQuick
import Quickshell
import Quickshell.Io

// The live state from `blinky watch`: looks, where each blinky sits, the running sessions and the
// phone switch. Changes go through the blinky command line, one at a time. Draws nothing.
Scope {
    id: root

    // Command name or absolute path of bin/blinky.
    property string command: "blinky"
    property var looks: []
    property var placements: []
    property var sessions: []
    property bool phone: false
    property bool sound: true
    // How loud each kind of phone push is: {done, waiting, question, error: off|quiet|normal|loud}.
    property var loudness: ({})
    // {project: slot}: the blinky each project had last, put back on its next terminal.
    property var remembered: ({})
    // Optional HyprlandWindows: with it, remembered blinkies place themselves.
    property var windows: null
    property var placing: ({})
    property string error: ""
    property var queue: []

    readonly property var covered: root.sessions.filter(session => session.slot !== null && session.slot !== undefined)
    readonly property var uncovered: root.sessions.filter(session => session.slot === null || session.slot === undefined)

    function run(args) {
        root.queue = root.queue.concat([[root.command].concat(args)]);
        if (!runner.running)
            root.next();
    }
    function next() {
        if (root.queue.length === 0)
            return;
        runner.command = root.queue[0];
        root.queue = root.queue.slice(1);
        runner.running = true;
    }

    function setLoudness(kind, level) {
        root.run(["loudness", kind, level]);
    }
    function setSound(on) {
        root.run(["sound", on ? "on" : "off"]);
    }
    function chime(kind) {
        root.run(["chime", kind]);
    }
    // An agent without a blinky, in a project that had one: put that blinky on its terminal,
    // unless the blinky sits somewhere else right now.
    function autoPlace() {
        if (!root.windows)
            return;
        for (const session of root.uncovered) {
            const slot = root.remembered[session.project];
            if (slot === undefined || root.placementOf(slot) || root.placing[session.key])
                continue;
            const window = root.windows.byPids(session.ancestors);
            if (!window)
                continue;
            root.placing[session.key] = true;
            root.place(slot, root.windows.info(window).pid, window.address);
        }
    }

    function setPhone(on) {
        root.run(["phone", on ? "on" : "off"]);
    }
    function place(slot, pid, address) {
        root.run(["place", "on", String(slot), "--pid", String(pid), "--address", String(address)]);
    }
    function unplace(slot) {
        root.run(["place", "off", String(slot)]);
    }
    function wake(slot, on) {
        root.run(["place", on ? "wake" : "sleep", String(slot)]);
    }
    function placementOf(slot) {
        return root.placements.find(item => item.slot === slot) ?? null;
    }
    function sessionOf(slot) {
        return root.sessions.find(session => session.slot === slot) ?? null;
    }

    Process {
        id: watcher

        command: [root.command, "watch"]
        running: true
        onRunningChanged: {
            if (running)
                return;
            root.sessions = [];
            restart.start();
        }

        stdout: SplitParser {
            onRead: line => {
                try {
                    const snapshot = JSON.parse(line);
                    root.looks = snapshot.looks;
                    root.placements = snapshot.placements;
                    root.sessions = snapshot.sessions;
                    root.phone = snapshot.phone;
                    root.sound = snapshot.sound ?? true;
                    root.loudness = snapshot.loudness ?? {};
                    root.remembered = snapshot.remembered ?? {};
                    root.placing = {};
                    // Set when skins.json is broken; the blinkies then wear the default looks.
                    root.error = snapshot.error ?? "";
                } catch (err) {
                    root.error = "blinky watch sent unreadable output: " + err;
                }
            }
        }

        stderr: SplitParser {
            onRead: line => root.error = line
        }
    }

    onUncoveredChanged: root.autoPlace()

    Connections {
        target: root.windows
        function onRevisionChanged() {
            root.autoPlace();
        }
    }

    // `blinky watch` only exits on a crash or a missing command; retry without spinning.
    Timer {
        id: restart

        interval: 5000
        onTriggered: watcher.running = true
    }

    Process {
        id: runner

        onRunningChanged: if (!running)
            root.next()
        stderr: SplitParser {
            onRead: line => root.error = line
        }
    }
}
