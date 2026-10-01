pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes

// The little status bubble at a blinky's shoulder: … thinking, lens searching, ! waiting,
// ? question, check done, × error, z sleeping. Glyphs are drawn on a 12×12 grid.
Item {
    id: root

    property string kind: ""
    property color fill: "#1f1b1a"
    property color glyph: "#ffffff"
    property real t: 0
    property bool still: false
    property real popStart: -10

    readonly property var paths: ({
            "searching": "M 7.6 7.6 L 9.4 9.4 M 2.6 5.2 A 2.6 2.6 0 1 1 7.8 5.2 A 2.6 2.6 0 1 1 2.6 5.2",
            "waiting": "M 6 2.8 L 6 6.4",
            "question": "M 4.2 4.4 Q 4.4 2.5 6.1 2.5 Q 7.9 2.6 7.8 4.3 Q 7.6 5.6 6.1 6 L 6.1 6.7",
            "done": "M 3.4 6.2 L 5.3 8.1 L 8.8 4.1",
            "error": "M 4 4 L 8 8 M 8 4 L 4 8",
            "sleeping": "M 4.2 3.8 L 7.8 3.8 L 4.2 8.2 L 7.8 8.2"
        })
    readonly property bool dotted: kind === "waiting" || kind === "question"

    visible: kind !== ""
    onKindChanged: root.popStart = root.t

    // Overshooting pop (ease-out-back), a pure function of time since the kind changed.
    readonly property real pop: {
        if (root.still)
            return 1;
        const u = Math.min(1, Math.max(0, (root.t - root.popStart) / 0.32));
        return 1 + 2.7 * Math.pow(u - 1, 3) + 1.7 * Math.pow(u - 1, 2);
    }
    // The z of a sleeping blinky drifts up and fades, again and again.
    readonly property real drift: root.kind === "sleeping" ? (root.t % 2.4) / 2.4 : 0

    Rectangle {
        id: bubble

        anchors.fill: parent
        radius: width / 2
        color: root.fill
        scale: root.pop
        antialiasing: true

        Item {
            width: 12
            height: 12
            transformOrigin: Item.TopLeft
            scale: bubble.width / 12
            y: -root.drift * 2 * bubble.width / 12
            opacity: 1 - root.drift * 0.7

            Shape {
                anchors.fill: parent
                visible: root.kind in root.paths
                preferredRendererType: Shape.CurveRenderer

                ShapePath {
                    fillColor: "transparent"
                    strokeColor: root.glyph
                    strokeWidth: 1.5
                    capStyle: ShapePath.RoundCap
                    joinStyle: ShapePath.RoundJoin
                    PathSvg { path: root.paths[root.kind] ?? "" }
                }
            }

            Rectangle {
                visible: root.dotted
                x: (root.kind === "question" ? 6.1 : 6) - 0.9
                y: 8.1
                width: 1.8
                height: 1.8
                radius: 0.9
                color: root.glyph
            }

            Repeater {
                model: root.kind === "thinking" ? 3 : 0

                Rectangle {
                    required property int index

                    x: 2.6 + index * 2.6
                    y: 5.1
                    width: 1.8
                    height: 1.8
                    radius: 0.9
                    color: root.glyph
                    // The dots light up one after another.
                    opacity: 0.35 + 0.65 * Math.max(0, Math.sin(2 * Math.PI * (root.t / 1.2 - index / 3)))
                }
            }
        }
    }
}
