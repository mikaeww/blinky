pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes

// The pair of eyes. Forms: capsule (open), arch (happy ^^), line (closed or annoyed).
// Sizes are pixels; a negative `tilt` turns the outer ends down.
Item {
    id: root

    property real eyeWidth: 4
    property real eyeHeight: 8
    property real split: 6
    property real tilt: 0
    property real gazeX: 0
    property real gazeY: 0
    property real blink: 1
    property real arch: 0
    property color ink: "#1f1b1a"
    property bool sparkle: true

    Repeater {
        model: 2

        Item {
            id: eye

            required property int index
            readonly property real side: index === 0 ? -1 : 1

            width: root.eyeWidth
            height: Math.max(1, root.eyeHeight * root.blink)
            x: root.width / 2 + side * root.split - width / 2 + root.gazeX
            y: root.height / 2 - height / 2 + root.gazeY
            rotation: -side * root.tilt

            Rectangle {
                anchors.fill: parent
                radius: Math.min(width, height) / 2
                color: root.ink
                opacity: 1 - root.arch
                antialiasing: true

                // Catchlight: only once the eye is big enough for it to read as one.
                Rectangle {
                    visible: root.sparkle && eye.width >= 4 && eye.height >= 5
                    width: eye.width * 0.38
                    height: width
                    radius: width / 2
                    x: eye.width * 0.52
                    y: eye.height * 0.14
                    color: "white"
                    opacity: 0.9
                }
            }

            Shape {
                anchors.fill: parent
                visible: root.arch > 0
                opacity: root.arch
                preferredRendererType: Shape.CurveRenderer

                ShapePath {
                    fillColor: "transparent"
                    strokeColor: root.ink
                    strokeWidth: Math.max(1, root.eyeWidth * 0.36)
                    capStyle: ShapePath.RoundCap
                    startX: 0
                    startY: eye.height
                    PathQuad { x: eye.width; y: eye.height; controlX: eye.width / 2; controlY: -eye.height }
                }
            }
        }
    }
}
