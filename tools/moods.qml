// Renders assets/moods.png: QT_QPA_PLATFORM=offscreen /usr/lib/qt6/bin/qml -I quickshell tools/moods.qml -- assets/moods.png
import QtQuick
import QtQuick.Window
import Blinky

Window {
    id: win
    width: row.width + phone.width + 72; height: 200; visible: true; color: "#1b1b1b"
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
        x: 24; anchors.verticalCenter: parent.verticalCenter
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
    // The phone runs past the bottom edge on purpose: only its lock screen top with the push matters.
    Rectangle {
        id: phone
        x: row.x + row.width + 24; y: 24; width: 192; height: 240
        color: "#262626"; radius: 32
        Rectangle {
            anchors.fill: parent; anchors.margins: 8
            color: "#313131"; radius: 24
            Text { x: 16; y: 16; text: "15:42"; color: "#b0b0b0"; font.pixelSize: 13; font.family: "IBM Plex Sans"; font.weight: Font.DemiBold }
            Rectangle {
                x: 8; y: 48; width: parent.width - 16; height: push.height + 24
                color: "#3d3d3d"; radius: 16
                Column {
                    id: push
                    x: 12; y: 12; width: parent.width - 24
                    spacing: 4
                    Text { text: "ntfy · now"; color: "#9a9a9a"; font.pixelSize: 11; font.family: "IBM Plex Sans" }
                    Text { text: "blinky · Miso"; color: "#ececec"; font.pixelSize: 13; font.family: "IBM Plex Sans"; font.weight: Font.DemiBold }
                    Text { text: "Claude is done"; color: "#b0b0b0"; font.pixelSize: 13; font.family: "IBM Plex Sans" }
                }
            }
        }
    }
    Timer { interval: 1500; running: true; onTriggered: win.contentItem.grabToImage(r => { r.saveToFile(Qt.application.arguments[Qt.application.arguments.length - 1]); Qt.quit() }) }
}
