pragma ComponentBehavior: Bound

import QtQuick
import ".."

// The blinky board's content, filling its window: the card with every blinky and where it sits,
// the agents no blinky watches yet, the phone switch; plus the dragged blinky and the window it
// would land on. Drag a blinky onto a terminal window or an unwatched agent's row to watch that
// terminal, back onto the card to free it. The card moves by its header.
Item {
    id: root

    required property var sessions
    required property var windows
    property bool reducedMotion: false
    // Global (compositor) position of this item's top-left corner.
    property point origin: Qt.point(0, 0)
    // Colours and fonts as {fg, muted, base, raised, hover, accent, accentText, font, mono, radius}.
    property var theme: ({})
    readonly property color fg: theme.fg ?? "#ececec"
    readonly property color muted: theme.muted ?? "#9b9b9b"
    readonly property color base: theme.base ?? "#161616"
    readonly property color raised: theme.raised ?? "#222222"
    readonly property color hover: theme.hover ?? "#2c2c2c"
    readonly property color accent: theme.accent ?? "#ececec"
    readonly property color accentText: theme.accentText ?? "#161616"
    readonly property string font: theme.font ?? ""
    readonly property string mono: theme.mono ?? "monospace"
    readonly property int radius: theme.radius ?? 22
    signal closeRequested()
    signal editLooksRequested()

    // Where a drag would land: "window", "row", "board" or "".
    property int dragSlot: -1
    property point dragAt: Qt.point(0, 0)
    property string dropKind: ""
    property var dropWindow: null
    // The card stays centred (also while it grows) until the header is dragged.
    property bool moved: false
    property real cardX: 0
    property real cardY: 0
    readonly property bool dragging: root.dragSlot >= 0
    readonly property alias card: card

    // Back to the middle each time the board opens.
    function center() {
        root.moved = false;
    }

    function globalOf(point) {
        return Qt.point(point.x + (root.origin.x), point.y + (root.origin.y));
    }
    function windowLabel(window, short) {
        if (!window)
            return "Fenster nicht gefunden";
        const ipc = root.windows.info(window);
        if (short)
            return (ipc?.class ?? "Fenster") + " · WS " + (ipc?.workspace?.name ?? "?");
        return "Workspace " + (ipc?.workspace?.name ?? "?") + " · " + window.title;
    }
    function rowAt(point) {
        for (let i = 0; i < uncoveredRows.count; i++) {
            const row = uncoveredRows.itemAt(i);
            const local = row.mapFromItem(null, point.x, point.y);
            // itemAt() is typed as a plain Item; the rows do carry `window`.
            if (row.contains(local) && row.window) // qmllint disable missing-property
                return row;
        }
        return null;
    }
    function track(point) {
        root.dragAt = point;
        const row = root.rowAt(point);
        if (row) {
            root.dropKind = "row";
            root.dropWindow = row.window; // qmllint disable missing-property
        } else if (card.contains(card.mapFromItem(null, point.x, point.y))) {
            root.dropKind = "board";
            root.dropWindow = null;
        } else {
            const at = root.globalOf(point);
            root.dropWindow = root.windows.windowAt(at.x, at.y);
            root.dropKind = root.dropWindow ? "window" : "";
        }
    }
    function drop() {
        const slot = root.dragSlot;
        if (root.dropKind === "board")
            root.sessions.unplace(slot);
        else if (root.dropWindow)
            root.sessions.place(slot, root.windows.info(root.dropWindow).pid, root.dropWindow.address);
        root.dragSlot = -1;
        root.dropKind = "";
        root.dropWindow = null;
    }

    // The terminal a drop would land on.
    Rectangle {
        readonly property rect frame: root.dropKind === "window" ? root.windows.frame(root.dropWindow) : Qt.rect(0, 0, 0, 0)
        visible: root.dragging && root.dropKind === "window"
        x: frame.x - (root.origin.x)
        y: frame.y - (root.origin.y)
        width: frame.width
        height: frame.height
        radius: root.radius / 2
        color: Qt.alpha(root.accent, 0.12)
        border.width: 2
        border.color: Qt.alpha(root.accent, 0.6)
    }

    Rectangle {
        id: card

        x: root.moved ? root.cardX : (root.width - width) / 2
        y: root.moved ? root.cardY : (root.height - height) / 2
        width: Math.min(760, root.width - 48)
        height: Math.min(content.implicitHeight + 48, root.height - 48)
        radius: root.radius
        color: root.base
        focus: root.visible
        Keys.onEscapePressed: root.closeRequested()

        Flickable {
            anchors.fill: parent
            anchors.margins: 24
            contentHeight: content.implicitHeight
            clip: true
            interactive: !root.dragging && contentHeight > height

            Column {
                id: content

                width: parent.width
                spacing: 18

                Item {
                    width: content.width
                    height: 44

                    // Drag the header to move the card.
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                        property point grab
                        onPressed: mouse => {
                            grab = Qt.point(mouse.x, mouse.y);
                            root.cardX = card.x;
                            root.cardY = card.y;
                            root.moved = true;
                        }
                        onPositionChanged: mouse => {
                            root.cardX = Math.max(0, Math.min(root.width - card.width, root.cardX + mouse.x - grab.x));
                            root.cardY = Math.max(0, Math.min(root.height - card.height, root.cardY + mouse.y - grab.y));
                        }
                    }

                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 4

                        Text {
                            text: "Blinkies"
                            color: root.fg
                            font.family: root.font
                            font.pixelSize: 20
                            font.weight: Font.DemiBold
                        }
                        Text {
                            text: "Zieh einen Blinky auf ein Terminal. Nur Terminals mit Blinky werden überwacht."
                            color: root.muted
                            font.family: root.font
                            font.pixelSize: 12
                        }
                    }

                    BoardButton {
                        board: root
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Schließen"
                        onClicked: root.closeRequested()
                    }
                }

                Rectangle {
                    width: content.width
                    height: 56
                    radius: root.radius / 2
                    color: root.raised

                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        Text {
                            text: "Handy-Push"
                            color: root.fg
                            font.family: root.font
                            font.pixelSize: 13
                        }
                        Text {
                            text: root.sessions.phone ? "An: ein wacher Blinky meldet, wenn sein Agent wartet, fragt oder fertig ist" : "Aus: keine Pushes, auch nicht von wachen Blinkies"
                            color: root.muted
                            font.family: root.font
                            font.pixelSize: 11
                        }
                    }

                    BoardSwitch {

                        board: root
                        anchors.right: parent.right
                        anchors.rightMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        checked: root.sessions.phone
                        label: "Handy-Push"
                        onSwitched: on => root.sessions.setPhone(on)
                    }
                }

                Rectangle {
                    width: content.width
                    height: 56
                    radius: root.radius / 2
                    color: root.raised

                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        Text {
                            text: "Töne am PC"
                            color: root.fg
                            font.family: root.font
                            font.pixelSize: 13
                        }
                        Text {
                            text: root.sessions.sound ? "An: Sprechblase mit Ton, wenn ein Agent fertig ist, wartet oder fragt" : "Aus: nur die Sprechblase"
                            color: root.muted
                            font.family: root.font
                            font.pixelSize: 11
                        }
                    }

                    BoardSwitch {

                        board: root
                        anchors.right: parent.right
                        anchors.rightMargin: 16
                        anchors.verticalCenter: parent.verticalCenter
                        checked: root.sessions.sound
                        label: "Töne am PC"
                        onSwitched: on => root.sessions.setSound(on)
                    }
                }

                SectionLabel { text: "Handy-Lautstärke" }

                Rectangle {
                    width: content.width
                    height: loudnessRows.implicitHeight + 16
                    radius: root.radius / 2
                    color: root.raised

                    Column {
                        id: loudnessRows

                        x: 16
                        y: 8
                        width: parent.width - 32

                        Repeater {
                            model: [
                                { kind: "waiting", label: "Wartet auf dich" },
                                { kind: "question", label: "Hat eine Frage" },
                                { kind: "error", label: "Fehler" },
                                { kind: "done", label: "Fertig (gesammelt)" }
                            ]

                            Item {
                                id: loudnessRow

                                required property var modelData

                                width: loudnessRows.width
                                height: 40

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: loudnessRow.modelData.label
                                    color: root.fg
                                    font.family: root.font
                                    font.pixelSize: 13
                                }
                                BoardChoice {
                                    board: root
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    label: loudnessRow.modelData.label
                                    options: [
                                        { value: "off", label: "aus" },
                                        { value: "quiet", label: "leise" },
                                        { value: "normal", label: "normal" },
                                        { value: "loud", label: "laut" }
                                    ]
                                    current: root.sessions.loudness[loudnessRow.modelData.kind] ?? ""
                                    onPicked: value => root.sessions.setLoudness(loudnessRow.modelData.kind, value)
                                }
                            }
                        }
                    }
                }

                SectionLabel {
                    visible: root.sessions.uncovered.length > 0
                    text: "Nicht abgedeckt"
                }

                Repeater {
                    id: uncoveredRows

                    model: root.sessions.uncovered

                    Rectangle {
                        id: row

                        required property var modelData
                        readonly property var window: {
                            root.windows.revision;
                            return root.windows.byPids(row.modelData.ancestors);
                        }
                        readonly property bool targeted: root.dragging && root.dropKind === "row" && root.dropWindow === window

                        width: content.width
                        height: 56
                        radius: root.radius / 2
                        color: targeted ? Qt.alpha(root.accent, 0.16) : root.raised
                        border.width: root.dragging && window ? 1 : 0
                        border.color: Qt.alpha(root.accent, targeted ? 0.7 : 0.25)

                        Column {
                            anchors.left: parent.left
                            anchors.leftMargin: 16
                            anchors.right: hint.left
                            anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 3

                            Text {
                                width: parent.width
                                elide: Text.ElideRight
                                text: row.modelData.project + " · " + (row.modelData.agent === "codex" ? "Codex" : "Claude")
                                color: root.fg
                                font.family: root.mono
                                font.pixelSize: 12
                            }
                            Text {
                                width: parent.width
                                elide: Text.ElideRight
                                text: root.windowLabel(row.window, false)
                                color: root.muted
                                font.family: root.mono
                                font.pixelSize: 11
                            }
                        }

                        Text {
                            id: hint
                            anchors.right: parent.right
                            anchors.rightMargin: 16
                            anchors.verticalCenter: parent.verticalCenter
                            text: row.window ? "Blinky hierher ziehen" : "kein Fenster (tmux?)"
                            color: root.muted
                            font.family: root.font
                            font.pixelSize: 11
                        }
                    }
                }

                SectionLabel { text: "Blinkies" }

                Flow {
                    id: tiles

                    width: content.width
                    spacing: 10

                    Repeater {
                        model: root.sessions.looks

                        BlinkyTile { board: root
 }
                    }
                }

                Row {
                    spacing: 10

                    BoardButton {
                        board: root
                        text: "Looks bearbeiten"
                        onClicked: root.editLooksRequested()
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Schließt ein Terminal, kommt sein Blinky zurück auf das Board."
                        color: root.muted
                        font.family: root.font
                        font.pixelSize: 11
                    }
                }
            }
        }
    }

    // The blinky under the pointer while dragging.
    BlinkyFace {
        readonly property var look: root.sessions.looks[root.dragSlot] ?? {}
        visible: root.dragging
        width: 72
        height: 72
        x: root.dragAt.x - width / 2
        y: root.dragAt.y - height / 2
        color: look.color ?? "#cccccc"
        shape: look.shape ?? "circle"
        eyes: look.eyes ?? "tall"
        blush: look.blush ?? false
        name: look.name ?? ""
        mood: root.dropKind === "window" || root.dropKind === "row" ? "waiting" : "idle"
        hovered: true
        reducedMotion: root.reducedMotion
    }

    component SectionLabel: Text {
        color: Qt.alpha(root.muted, 0.8)
        font.family: root.mono
        font.pixelSize: 11
        font.weight: Font.DemiBold
        font.letterSpacing: 1.4
        font.capitalization: Font.AllUppercase
    }

}
