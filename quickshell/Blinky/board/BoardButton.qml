pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

// A plain board button in the board's theme.
AbstractButton {
    id: button

    required property var board

    implicitWidth: label.implicitWidth + 28
    implicitHeight: 34
    hoverEnabled: true
    contentItem: Text {
        id: label
        text: button.text
        color: button.board.fg
        font.family: button.board.font
        font.pixelSize: 12
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: button.board.radius / 2.5
        color: button.hovered || button.visualFocus ? button.board.hover : button.board.raised
    }
}
