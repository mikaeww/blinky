pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

// An on/off switch in the board's theme; `switched` reports the new state.
AbstractButton {
    id: toggle

    required property var board

    property string label: ""
    signal switched(bool on)

    width: 40
    height: 22
    checkable: true
    Accessible.name: toggle.label
    onClicked: toggle.switched(checked)
    background: Rectangle {
        radius: height / 2
        color: toggle.checked ? toggle.board.accent : Qt.alpha(toggle.board.fg, 0.16)

        Rectangle {
            x: toggle.checked ? parent.width - width - 2 : 2
            anchors.verticalCenter: parent.verticalCenter
            width: 18
            height: 18
            radius: 9
            color: toggle.checked ? toggle.board.accentText : toggle.board.fg
            Behavior on x { enabled: !toggle.board.reducedMotion; NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
    }
}
