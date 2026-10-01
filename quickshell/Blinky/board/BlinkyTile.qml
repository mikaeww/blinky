pragma ComponentBehavior: Bound

import QtQuick
import ".."

// One blinky on the board: its face, where it sits, wake/sleep and release. Pressing and
// moving drags it out; the board decides where it lands.
Rectangle {
    id: tile

    required property var board
    required property var modelData
    readonly property var placed: tile.board.sessions.placementOf(modelData.slot)
    readonly property var session: tile.board.sessions.sessionOf(modelData.slot)
    readonly property string remembers: Object.keys(tile.board.sessions.remembered).filter(project => tile.board.sessions.remembered[project] === tile.modelData.slot).join(", ")
    readonly property var window: {
        tile.board.windows.revision;
        return tile.placed ? tile.board.windows.byAddress(tile.placed.address) : null;
    }

    width: 134
    height: tile.placed ? 190 : 128
    radius: tile.board.radius / 2
    color: grip.containsMouse && !tile.board.dragging ? tile.board.hover : tile.board.raised
    opacity: tile.board.dragSlot === modelData.slot ? 0.35 : 1

    BlinkyFace {
        id: face

        anchors.horizontalCenter: parent.horizontalCenter
        y: 14
        width: 72
        height: 72
        color: tile.modelData.color
        shape: tile.modelData.shape
        eyes: tile.modelData.eyes
        blush: tile.modelData.blush
        name: tile.modelData.name
        mood: !tile.placed ? "idle" : !tile.placed.on ? "sleeping" : tile.session ? tile.session.state : "idle"
        reducedMotion: tile.board.reducedMotion
        hovered: grip.containsMouse
        watching: grip.containsMouse
        lookAt: Qt.point(grip.mouseX - face.x, grip.mouseY - face.y)
    }

    // Press and move to drag the blinky out; a short click does nothing.
    MouseArea {
        id: grip

        anchors.fill: parent
        anchors.bottomMargin: 48
        hoverEnabled: true
        cursorShape: tile.board.dragging ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        property point start
        onPressed: mouse => start = Qt.point(mouse.x, mouse.y)
        onPositionChanged: mouse => {
            if (!pressed)
                return;
            const at = grip.mapToItem(null, mouse.x, mouse.y);
            if (tile.board.dragSlot < 0 && Math.hypot(mouse.x - start.x, mouse.y - start.y) > 6)
                tile.board.dragSlot = tile.modelData.slot;
            if (tile.board.dragSlot === tile.modelData.slot)
                tile.board.track(at);
        }
        onReleased: if (tile.board.dragSlot === tile.modelData.slot)
            tile.board.drop()
    }

    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 12
        y: 94
        spacing: 3

        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: tile.modelData.name
            color: tile.board.fg
            font.family: tile.board.font
            font.pixelSize: 13
            font.weight: Font.DemiBold
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            text: !tile.placed ? (tile.remembers ? "merkt sich " + tile.remembers : "frei") : (tile.placed.on ? "" : "schläft · ") + (tile.session ? tile.session.project : "kein Agent")
            color: tile.board.muted
            font.family: tile.board.mono
            font.pixelSize: 11
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            visible: tile.placed !== null
            text: tile.board.windowLabel(tile.window, true)
            color: tile.board.muted
            font.family: tile.board.mono
            font.pixelSize: 10
        }
    }

    Row {
        visible: tile.placed !== null
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 12
        spacing: 8

        BoardSwitch {
            board: tile.board
            anchors.verticalCenter: parent.verticalCenter
            checked: tile.placed?.on ?? false
            label: tile.modelData.name + " wach"
            onSwitched: on => tile.board.sessions.wake(tile.modelData.slot, on)
        }
        BoardButton {
            board: tile.board
            implicitHeight: 26
            text: "Lösen"
            onClicked: tile.board.sessions.unplace(tile.modelData.slot)
        }
    }
}
