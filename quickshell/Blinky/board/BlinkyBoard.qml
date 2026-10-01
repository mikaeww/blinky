pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland

// The blinky board as an overlay on the focused screen. Only the card takes input, so the
// desktop around it stays usable; while a blinky is dragged the whole screen does.
PanelWindow {
    id: root

    required property var sessions
    required property var windows
    property bool open: false
    property bool reducedMotion: false
    // See BoardSurface.theme.
    property var theme: ({})
    signal closeRequested()
    signal editLooksRequested()

    visible: root.open
    screen: Quickshell.screens.find(screen => screen.name === Hyprland.focusedMonitor?.name) ?? Quickshell.screens[0]
    color: "transparent"
    exclusionMode: ExclusionMode.Ignore
    anchors {
        top: true
        bottom: true
        left: true
        right: true
    }
    mask: Region { item: surface.dragging ? surface : surface.card }
    WlrLayershell.namespace: "quickshell:blinky-board"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: root.open ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

    onOpenChanged: if (open)
        surface.center()

    BoardSurface {
        id: surface

        anchors.fill: parent
        sessions: root.sessions
        windows: root.windows
        reducedMotion: root.reducedMotion
        theme: root.theme
        origin: Qt.point(root.screen?.x ?? 0, root.screen?.y ?? 0)
        onCloseRequested: root.closeRequested()
        onEditLooksRequested: root.editLooksRequested()
    }
}
