pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

// A segmented choice in the board's theme: one option is active, `picked` reports a new one.
Row {
    id: choice

    required property var board
    property var options: [] // [{ value, label }]
    property string current: ""
    property string label: ""
    signal picked(string value)

    spacing: 2

    Repeater {
        model: choice.options

        AbstractButton {
            id: segment

            required property var modelData
            readonly property bool active: modelData.value === choice.current

            implicitWidth: text.implicitWidth + 20
            implicitHeight: 28
            hoverEnabled: true
            Accessible.role: Accessible.RadioButton
            Accessible.name: choice.label + ": " + modelData.label
            Accessible.checked: active
            onClicked: choice.picked(modelData.value)

            contentItem: Text {
                id: text
                text: segment.modelData.label
                color: segment.active ? choice.board.accentText : choice.board.fg
                font.family: choice.board.font
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                radius: choice.board.radius / 3
                color: segment.active ? choice.board.accent : segment.hovered || segment.visualFocus ? choice.board.hover : choice.board.raised
            }
        }
    }
}
