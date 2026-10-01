pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland

// The blinkies sitting in the bottom-right corner of the terminals they watch, on one screen.
// When an agent is done, waits or asks, a speech bubble opens to the left of its blinky with a
// chime, and stays until that terminal has had focus. Clicking a blinky shows its last answer,
// clicking the bubble brings the terminal to the front. Everything else is click-through.
PanelWindow {
    id: root

    required property var sessions
    required property var windows
    property bool reducedMotion: false
    property int blinkySize: 40
    property int inset: 12
    // {base, fg, muted, font, mono, radius} for the bubbles.
    property var theme: ({})
    // Bubble texts; %1 is the tool or the error.
    property var texts: ({
            done: "Done",
            waiting: "May I use %1?",
            question: "I have a question.",
            error: "Stopped: %1",
            empty: "No answer yet."
        })
    // Bubbles only chime for news that arrives after the shell started.
    readonly property real startedAt: Date.now() / 1000

    visible: root.sessions.placements.length > 0
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    anchors {
        top: true
        bottom: true
        left: true
        right: true
    }
    mask: Region {
        regions: {
            corners.count;
            const hits = [];
            for (let i = 0; i < corners.count; i++) {
                // itemAt() is typed as a plain Item; the corners do carry `hit`.
                const corner = corners.itemAt(i);
                if (corner?.visible)
                    hits.push(corner.hit); // qmllint disable missing-property
            }
            return hits;
        }
    }
    WlrLayershell.namespace: "quickshell:blinky-corners"
    WlrLayershell.layer: WlrLayer.Top

    Repeater {
        id: corners

        model: root.sessions.placements

        Item {
            id: corner

            required property var modelData
            readonly property var look: root.sessions.looks[modelData.slot] ?? {}
            readonly property var session: root.sessions.sessionOf(modelData.slot)
            readonly property var window: {
                root.windows.revision;
                return root.windows.byAddress(corner.modelData.address);
            }
            readonly property rect frame: {
                root.windows.revision;
                return corner.window ? root.windows.frame(corner.window) : Qt.rect(0, 0, 0, 0);
            }
            // Global position of the point the blinky sits on.
            readonly property point anchor: Qt.point(frame.x + frame.width - root.inset - root.blinkySize / 2, frame.y + frame.height - root.inset - root.blinkySize / 2)
            readonly property bool uncovered: {
                root.windows.revision;
                return corner.window !== null && root.windows.windowAt(anchor.x, anchor.y) === corner.window;
            }
            // Every screen has its own TerminalBlinkies; only the terminal's own screen draws and chimes.
            readonly property bool onThisScreen: root.screen !== null
                && anchor.x >= root.screen.x && anchor.x < root.screen.x + root.screen.width
                && anchor.y >= root.screen.y && anchor.y < root.screen.y + root.screen.height
            readonly property bool news: modelData.on && session !== null
                && ["done", "waiting", "question", "error"].includes(session.state)
                && !root.windows.seenSince(window, session.since)
            property bool peek: false
            readonly property bool talking: news || peek
            readonly property Region hit: Region { item: corner }
            // Hyprland reports the target geometry while the window is still dragged or animating
            // there, so the blinky hides until the frame has stopped changing.
            property rect lastFrame
            readonly property bool moving: settle.running

            onFrameChanged: {
                if (frame.x === lastFrame.x && frame.y === lastFrame.y && frame.width === lastFrame.width && frame.height === lastFrame.height)
                    return;
                const appeared = lastFrame.width === 0;
                lastFrame = frame;
                if (appeared)
                    return;
                settle.restart();
                root.windows.hurry();
            }

            Timer {
                id: settle

                interval: 450
            }

            onNewsChanged: {
                if (!news) {
                    corner.peek = false;
                    return;
                }
                if (corner.onThisScreen && root.sessions.sound && session.since > root.startedAt)
                    root.sessions.chime(session.state === "done" ? "done" : session.state === "error" ? "error" : "attention");
            }

            visible: uncovered && onThisScreen && !moving && !root.windows.dragging
            // The item spans the bubble and the blinky, so the mask covers exactly what can be clicked.
            width: root.blinkySize + (talking ? bubble.width + 8 : 0)
            height: Math.max(root.blinkySize, talking ? bubble.height : 0)
            x: anchor.x - (root.screen?.x ?? 0) + root.blinkySize / 2 - width
            y: anchor.y - (root.screen?.y ?? 0) + root.blinkySize / 2 - height

            BlinkyBubble {
                id: bubble

                visible: corner.talking
                anchors.right: face.left
                anchors.rightMargin: 8
                anchors.bottom: face.bottom
                theme: root.theme
                title: corner.session ? corner.session.project + " · " + (corner.look.name ?? "") : (corner.look.name ?? "")
                body: {
                    const session = corner.session;
                    if (!session)
                        return root.texts.empty;
                    if (corner.news && session.state === "waiting")
                        return root.texts.waiting.replace("%1", session.detail || "?");
                    if (corner.news && session.state === "question")
                        return root.texts.question;
                    if (corner.news && session.state === "error")
                        return root.texts.error.replace("%1", session.detail.replace(/_/g, " "));
                    return session.message || (corner.news ? root.texts.done : root.texts.empty);
                }
                onClicked: {
                    if (corner.window)
                        root.windows.focus(corner.window);
                    corner.peek = false;
                }
            }

            BlinkyFace {
                id: face

                anchors.right: parent.right
                anchors.bottom: parent.bottom
                width: root.blinkySize
                height: root.blinkySize
                color: corner.look.color ?? "#cccccc"
                shape: corner.look.shape ?? "circle"
                eyes: corner.look.eyes ?? "tall"
                blush: corner.look.blush ?? false
                name: corner.look.name ?? ""
                mood: !corner.modelData.on ? "sleeping" : corner.session ? corner.session.state : "idle"
                reducedMotion: root.reducedMotion
                hovered: pointer.hovered
                watching: root.windows.trackCursor
                lookAt: {
                    const at = face.mapToItem(null, 0, 0);
                    return Qt.point(root.windows.cursor.x - (root.screen?.x ?? 0) - at.x, root.windows.cursor.y - (root.screen?.y ?? 0) - at.y);
                }

                HoverHandler {
                    id: pointer
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    onTapped: corner.peek = !corner.peek
                }
            }
        }
    }
}
