import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

// What blinkies need from Hyprland: the global cursor, the windows on screen, which window is
// under a point, and where a window is. Optional: without Hyprland blinkies still work, they
// just cannot follow the mouse or sit on terminals.
Scope {
    id: root

    // Poll the cursor (for gazes) and the window list (for blinkies sitting on windows).
    property bool trackCursor: false
    property bool trackWindows: false
    property point cursor: Qt.point(0, 0)
    readonly property bool available: Quickshell.env("HYPRLAND_INSTANCE_SIGNATURE") !== ""
    // Bumped on every window refresh, so bindings that read window geometry re-evaluate.
    property int revision: 0
    readonly property string activeAddress: root.plain(Hyprland.activeToplevel?.address)
    // When each window last had focus (seconds, wall clock): {address: time}.
    property var focusedAt: ({})
    // Workspace ids some monitor shows right now (incl. special workspaces), read straight
    // from Hyprland: Quickshell's monitor objects do not always carry their active workspace.
    property var activeWorkspaces: []

    onActiveAddressChanged: {
        if (root.activeAddress === "")
            return;
        const seen = Object.assign({}, root.focusedAt);
        seen[root.activeAddress] = Date.now() / 1000;
        root.focusedAt = seen;
    }

    function plain(address) {
        return String(address ?? "").replace(/^0x/, "");
    }

    // Whether the window has had focus at or after `time` (seconds, wall clock).
    function seenSince(window, time) {
        const address = root.plain(window?.address);
        return address !== "" && (address === root.activeAddress || (root.focusedAt[address] ?? 0) >= time);
    }

    function info(window) {
        return window?.lastIpcObject ?? null;
    }

    // Mapped windows on a workspace that some monitor shows right now.
    function shown() {
        return Hyprland.toplevels.values.filter(window => {
            const ipc = root.info(window);
            return ipc && ipc.mapped && !ipc.hidden && (ipc.pinned || root.activeWorkspaces.includes(ipc.workspace?.id));
        });
    }

    function frame(window) {
        const ipc = root.info(window);
        return ipc ? Qt.rect(ipc.at[0], ipc.at[1], ipc.size[0], ipc.size[1]) : Qt.rect(0, 0, 0, 0);
    }

    // Topmost window under a global point: floating above tiled, then most recently focused.
    function windowAt(x, y) {
        const hits = root.shown().filter(window => {
            const r = root.frame(window);
            return x >= r.x && x < r.x + r.width && y >= r.y && y < r.y + r.height;
        });
        hits.sort((a, b) => (root.info(b).floating - root.info(a).floating) || (root.info(a).focusHistoryID - root.info(b).focusHistoryID));
        return hits[0] ?? null;
    }

    function byAddress(address) {
        const wanted = root.plain(address);
        return Hyprland.toplevels.values.find(window => root.plain(window.address) === wanted) ?? null;
    }

    // The terminal of an agent: the first of its ancestor processes that owns a window.
    function byPids(pids) {
        const windows = Hyprland.toplevels.values;
        for (const pid of pids ?? []) {
            const match = windows.find(window => root.info(window)?.pid === pid);
            if (match)
                return match;
        }
        return null;
    }

    function focus(window) {
        const address = root.plain(window.address);
        Hyprland.dispatch("hl.dsp.focus({ window = \"address:0x" + address + "\" })");
    }

    // A watched window moved: poll fast until it has stayed put for a while.
    function hurry() {
        fastPoll.restart();
    }

    function refresh() {
        Hyprland.refreshToplevels();
        if (!monitorSocket.connected)
            monitorSocket.connected = true;
        root.revision++;
    }

    Connections {
        target: Hyprland
        enabled: root.trackWindows

        function onRawEvent(event) {
            if (["openwindow", "closewindow", "movewindowv2", "changefloatingmode", "fullscreen", "workspacev2", "focusedmonv2"].includes(event.name))
                root.refresh();
        }
    }

    // ponytail: Hyprland sends no event when a window is resized or dragged, so window
    // geometry is also polled; a few requests per second over the socket while blinkies sit on windows.
    Timer {
        id: fastPoll

        interval: 1000
    }

    Timer {
        interval: fastPoll.running ? 50 : 300
        repeat: true
        running: root.trackWindows && root.available
        triggeredOnStart: true
        onTriggered: root.refresh()
    }

    Socket {
        id: socket

        path: Quickshell.env("XDG_RUNTIME_DIR") + "/hypr/" + Quickshell.env("HYPRLAND_INSTANCE_SIGNATURE") + "/.socket.sock"
        onConnectedChanged: {
            if (!connected)
                return;
            write("cursorpos");
            flush();
        }
        // Hyprland answers "x, y" and closes the connection; one request per connection.
        // Closing it ourselves first avoids a PeerClosedError warning per poll in the log.
        parser: SplitParser {
            splitMarker: ""
            onRead: data => {
                socket.connected = false;
                const parts = data.split(",");
                const x = Number(parts[0]), y = Number(parts[1]);
                if (parts.length === 2 && isFinite(x) && isFinite(y) && (x !== root.cursor.x || y !== root.cursor.y))
                    root.cursor = Qt.point(x, y);
            }
        }
    }

    Socket {
        id: monitorSocket

        property string buffer: ""

        path: socket.path
        onConnectedChanged: {
            if (!connected)
                return;
            buffer = "";
            write("j/monitors");
            flush();
        }
        // The answer can arrive in pieces; it is complete once it parses.
        parser: SplitParser {
            splitMarker: ""
            onRead: data => {
                monitorSocket.buffer += data;
                let monitors;
                try {
                    monitors = JSON.parse(monitorSocket.buffer);
                } catch (incomplete) {
                    return;
                }
                monitorSocket.connected = false;
                root.activeWorkspaces = monitors.reduce((ids, monitor) => ids.concat([monitor.activeWorkspace?.id, monitor.specialWorkspace?.id]), []).filter(id => id);
                root.revision++;
            }
        }
    }

    Timer {
        interval: 70
        repeat: true
        running: root.trackCursor && root.available
        onTriggered: socket.connected = true
    }
}
