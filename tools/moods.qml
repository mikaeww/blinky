// Renders assets/moods.png: QT_QPA_PLATFORM=offscreen /usr/lib/qt6/bin/qml -I quickshell tools/moods.qml -- assets/moods.png
import QtQuick
import QtQuick.Window
import Blinky

Window {
    id: win
    width: row.width + 48; height: 150; visible: true; color: "#1b1b1b"
    property var items: [
        ["Pip", "#f2a7a0", "circle", "tall", true, "idle"],
        ["Nori", "#9fd4b0", "squircle", "round", false, "thinking"],
        ["Yuzu", "#f3d27a", "pebble", "tall", true, "working"],
        ["Boba", "#b9a4e8", "cloud", "wide", true, "waiting"],
        ["Kiwi", "#c4dc7e", "capsule", "round", false, "question"],
        ["Miso", "#e8b48a", "pebble", "wide", true, "done"],
        ["Sumi", "#a9c8ef", "circle", "round", false, "error"],
        ["Ume", "#ee9cc6", "squircle", "tall", true, "sleeping"]]
    Row {
        id: row
        anchors.centerIn: parent
        spacing: 24
        Repeater {
            model: win.items
            Column {
                required property var modelData
                spacing: 8
                BlinkyFace {
                    width: 88; height: 88
                    name: modelData[0]; color: modelData[1]; shape: modelData[2]; eyes: modelData[3]
                    blush: modelData[4]; mood: modelData[5]; reducedMotion: true
                }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData[5]; color: "#9a9a9a"; font.pixelSize: 13; font.family: "IBM Plex Sans" }
            }
        }
    }
    Timer { interval: 1500; running: true; onTriggered: win.contentItem.grabToImage(r => { r.saveToFile(Qt.application.arguments[Qt.application.arguments.length - 1]); Qt.quit() }) }
}
