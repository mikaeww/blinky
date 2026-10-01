import QtQuick

// A speech bubble with a tail on its right edge, pointing at the blinky that speaks.
// Shows a title line and up to four lines of text; a click is reported, not handled.
Item {
    id: root

    property string title: ""
    property string body: ""
    // {base, fg, muted, font, mono, radius}
    property var theme: ({})
    signal clicked()

    readonly property int maxWidth: 320
    readonly property int padding: 12

    width: Math.min(root.maxWidth, Math.max(titleLabel.implicitWidth, bodyLabel.implicitWidth) + 2 * root.padding)
    height: column.implicitHeight + 2 * root.padding
    opacity: visible ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

    Rectangle {
        anchors.fill: parent
        radius: root.theme.radius ? root.theme.radius / 2 : 12
        color: root.theme.base ?? "#1b1b1b"
    }

    // The tail: a small square turned 45 degrees, half of it outside the bubble.
    Rectangle {
        width: 10
        height: 10
        rotation: 45
        x: parent.width - width / 2 - 1
        y: parent.height - 20
        color: root.theme.base ?? "#1b1b1b"
    }

    Column {
        id: column

        x: root.padding
        y: root.padding
        width: root.width - 2 * root.padding
        spacing: 4

        Text {
            id: titleLabel

            width: parent.width
            elide: Text.ElideRight
            text: root.title
            color: root.theme.muted ?? "#9b9b9b"
            font.family: root.theme.mono ?? "monospace"
            font.pixelSize: 10
        }
        Text {
            id: bodyLabel

            width: parent.width
            wrapMode: Text.Wrap
            maximumLineCount: 4
            elide: Text.ElideRight
            // Markdown marks read as noise in a bubble.
            text: root.body.replace(/[`*_#>]/g, "").replace(/\s+/g, " ").trim()
            color: root.theme.fg ?? "#ececec"
            font.family: root.theme.font ?? ""
            font.pixelSize: 12
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
