pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Shapes
import "BlinkyGeometry.js" as Geometry

// One blinky: a soft shaded body, two eyes, a status badge. It thinks, searches, works,
// watches the cursor, and reacts to being poked. Moods come from `blinky watch`:
// idle, thinking, searching, working, waiting, question, done, error, sleeping.
Item {
    id: root

    property string shape: "circle"
    property string eyes: "tall"
    property color color: "#f2a7a0"
    property color ink: "#1f1b1a"
    property bool blush: false
    property string mood: "idle"
    property string name: ""
    property bool reducedMotion: false
    // Where the cursor is, in this item's coordinates; set `watching` when it is known.
    property point lookAt: Qt.point(0, 0)
    property bool watching: false
    property bool hovered: false

    // Seconds on the animation clock; every motion below is a pure function of it.
    property real t: 0
    property real hopStart: -10
    property real pokeStart: -10
    property real dizzyUntil: -10
    property real lastLook: -10
    property var pokes: []

    readonly property real size: Math.min(width, height)
    readonly property real radius: size * 0.38
    readonly property real seed: Geometry.seedOf(root.name)
    readonly property bool dizzy: root.t < root.dizzyUntil
    readonly property bool annoyed: root.t - root.pokeStart < 0.7 && !root.dizzy
    readonly property string face: root.dizzy ? "dizzy" : root.annoyed ? "annoyed" : root.mood

    implicitWidth: 26
    implicitHeight: 26
    Accessible.role: Accessible.Graphic
    Accessible.name: root.name + ", " + root.mood

    // Three pokes within a second make it dizzy; one makes it squish and frown.
    function poke() {
        root.pokes = root.pokes.filter(at => root.t - at < 1).concat([root.t]);
        root.pokeStart = root.t;
        if (root.pokes.length >= 3) {
            root.dizzyUntil = root.t + 2.5;
            root.pokes = [];
        }
    }

    onMoodChanged: {
        if (["waiting", "question", "done"].includes(mood) && root.t - root.hopStart > 0.6)
            root.hopStart = root.t;
    }
    onLookAtChanged: root.lastLook = root.t

    // Eye shape per face: [width, height] in body radii, vertical shift, tilt in degrees
    // (negative droops the outer ends: sad; positive raises them: grumpy).
    readonly property var eyeBase: ({ "tall": [0.2, 0.42], "round": [0.27, 0.27], "wide": [0.34, 0.2] })[root.eyes] ?? [0.2, 0.42]
    readonly property var faceEyes: ({
            "thinking": [1, 0.85, -0.02, 0],
            "searching": [1.05, 0.9, 0.02, 0],
            "working": [1, 0.72, 0.04, 0],
            "waiting": [1.18, 1.22, -0.06, 0],
            "question": [1.12, 1.15, -0.04, 0],
            "error": [0.95, 0.55, 0.05, -18],
            "sleeping": [1.15, 0.1, 0.1, 0],
            "annoyed": [1.25, 0.16, 0.02, 14],
            "dizzy": [0.8, 0.8, 0, 0]
        })[root.face] ?? [1, 1, 0, 0]
    readonly property bool happy: root.face === "done"
    readonly property real grow: root.hovered ? 1.12 : 1

    property real eyeW: (root.happy ? 0.3 : root.eyeBase[0] * root.faceEyes[0] * root.grow) * root.radius
    property real eyeH: (root.happy ? 0.18 : root.eyeBase[1] * root.faceEyes[1] * root.grow) * root.radius
    property real eyeShift: (root.happy ? -0.04 : root.faceEyes[2]) * root.radius
    property real eyeTilt: root.faceEyes[3]
    property real arch: root.happy ? 1 : 0
    property real lean: root.face === "question" ? 9 : 0
    Behavior on eyeW { enabled: !root.reducedMotion; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Behavior on eyeH { enabled: !root.reducedMotion; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Behavior on eyeShift { enabled: !root.reducedMotion; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Behavior on eyeTilt { enabled: !root.reducedMotion; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Behavior on arch { enabled: !root.reducedMotion; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    Behavior on lean { enabled: !root.reducedMotion; SpringAnimation { spring: 4; damping: 0.35 } }

    // Where the eyes want to look, each axis in [-1, 1].
    function cursorDirection() {
        const dx = root.lookAt.x - root.width / 2, dy = root.lookAt.y - root.height / 2;
        const reach = Math.hypot(dx, dy) + root.size * 2;
        return [dx / reach * 2, dy / reach * 2];
    }
    function wander() {
        const step = Math.floor(root.t / 2.3 + root.seed * 7);
        return [Geometry.noise(step, root.seed) * 1.4 - 0.7, Geometry.noise(step, root.seed + 1) * 0.8 - 0.4];
    }
    readonly property var gazeTarget: {
        const watched = root.watching && (root.hovered || root.t - root.lastLook < 3);
        switch (root.face) {
        case "dizzy":
            return [Math.cos(9 * root.t) * 0.8, Math.sin(9 * root.t) * 0.8];
        case "thinking":
            return [0.55 + 0.15 * Math.sin(0.8 * root.t + root.seed * 6), -0.8];
        case "searching":
            return [Math.sin(2 * Math.PI * root.t / 1.6), 0.3];
        case "working":
            return [0.2 * Math.sin(2 * Math.PI * root.t / 3), 0.7];
        case "sleeping":
        case "done":
        case "annoyed":
            return [0, 0];
        case "waiting":
        case "question":
        case "error":
            return root.watching ? root.cursorDirection() : [0, 0];
        default:
            return watched ? root.cursorDirection() : root.wander();
        }
    }
    property real gazeX: root.gazeTarget[0] * 0.14 * root.radius
    property real gazeY: root.gazeTarget[1] * 0.1 * root.radius
    Behavior on gazeX { enabled: !root.reducedMotion; SpringAnimation { spring: 6; damping: 0.55 } }
    Behavior on gazeY { enabled: !root.reducedMotion; SpringAnimation { spring: 6; damping: 0.55 } }

    readonly property real breath: {
        const period = root.mood === "sleeping" ? 5 : root.mood === "working" ? 1.6 : 3.4;
        const amp = root.mood === "sleeping" ? 0.045 : 0.03;
        return amp * Math.sin(2 * Math.PI * ((root.t % period) / period + root.seed));
    }
    readonly property real blink: {
        if (["sleeping", "done", "annoyed", "dizzy"].includes(root.face) || root.t === 0)
            return 1;
        const p = (root.t + root.seed * 4.6) % 4.6;
        return p < 0.14 ? 1 - 0.9 * Math.sin(Math.PI * p / 0.14) : 1;
    }
    // sin² has zero velocity at take-off and landing.
    readonly property real hop: {
        const u = (root.t - root.hopStart) / 0.56;
        return u >= 0 && u < 1 ? -0.12 * root.size * Math.pow(Math.sin(Math.PI * u), 2) : 0;
    }
    // A poke squishes the body, then it wobbles back: a damped oscillation in time.
    readonly property real squish: {
        const s = root.t - root.pokeStart;
        return s >= 0 && s < 1 ? 0.16 * Math.exp(-6 * s) * Math.cos(18 * s) : 0;
    }
    readonly property real wobble: root.dizzy ? 7 * Math.sin(11 * root.t) : 0

    FrameAnimation {
        running: root.visible && !root.reducedMotion
        onTriggered: root.t = elapsedTime
    }

    Item {
        id: figure

        width: root.size
        height: root.size
        anchors.centerIn: parent
        rotation: root.lean + root.wobble
        transform: [
            Scale {
                origin.x: figure.width / 2
                origin.y: figure.height * 0.9
                xScale: 1 - root.breath * 0.5 + root.squish * 0.6
                yScale: 1 + root.breath - root.squish
            },
            Translate { y: root.hop }
        ]

        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer

            ShapePath {
                strokeWidth: -1
                fillGradient: LinearGradient {
                    x1: 0; y1: figure.height * 0.1
                    x2: 0; y2: figure.height * 0.9
                    GradientStop { position: 0; color: Qt.tint(root.color, Qt.rgba(1, 1, 1, 0.42)) }
                    GradientStop { position: 0.55; color: root.color }
                    GradientStop { position: 1; color: Qt.darker(root.color, 1.12) }
                }
                PathSvg { path: Geometry.bodyPath(root.shape, figure.width, root.radius) }
            }
        }

        // Soft shine on the upper left.
        Rectangle {
            width: root.radius * 0.5
            height: root.radius * 0.3
            radius: height / 2
            x: figure.width / 2 - root.radius * 0.62
            y: figure.height / 2 - root.radius * 0.72
            rotation: -24
            color: "white"
            opacity: 0.38
        }

        Repeater {
            model: root.blush ? 2 : 0

            Rectangle {
                required property int index

                width: root.radius * 0.36
                height: root.radius * 0.2
                radius: height / 2
                x: figure.width / 2 + (index === 0 ? -1 : 1) * root.radius * 0.58 - width / 2 + root.gazeX * 0.4
                y: figure.height / 2 + root.radius * 0.24
                color: "#ff7f9b"
                opacity: root.face === "error" ? 0.15 : 0.42
            }
        }

        BlinkyEyes {
            anchors.fill: parent
            anchors.topMargin: -root.radius * 0.1 + root.eyeShift * 2
            eyeWidth: root.eyeW
            eyeHeight: root.eyeH
            split: root.radius * 0.32
            tilt: root.eyeTilt
            gazeX: root.gazeX
            gazeY: root.gazeY
            blink: root.blink
            arch: root.arch
            ink: root.ink
        }
    }

    BlinkyBadge {
        readonly property var kinds: ["thinking", "searching", "waiting", "question", "done", "error", "sleeping"]
        kind: kinds.includes(root.mood) ? root.mood : ""
        width: root.size * 0.42
        height: width
        x: root.width / 2 + root.radius * 0.5
        y: root.height / 2 - root.radius * 1.25 + root.hop
        t: root.t
        still: root.reducedMotion
        fill: root.ink
        glyph: Qt.tint(root.color, Qt.rgba(1, 1, 1, 0.55))
    }
}
