import QtQuick
import QtQuick.Controls

Button {
    id: control
    required property var colors
    property bool primary: false
    implicitHeight: 40
    implicitWidth: Math.max(86, contentItem.implicitWidth + 28)
    hoverEnabled: true
    Accessible.name: text
    contentItem: Text {
        text: control.text
        color: control.primary ? "#ffffff" : control.colors.ink
        font.family: "Segoe UI"
        font.pixelSize: 14
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: control.enabled ? 1 : 0.45
    }
    background: Rectangle {
        color: control.primary ? control.colors.primary : (control.hovered ? control.colors.heading : control.colors.surface)
        // Keep keyboard focus visible without leaving a ring after mouse clicks.
        border.color: control.visualFocus ? control.colors.focus : control.colors.border
        border.width: control.visualFocus ? 3 : 2
        opacity: control.enabled ? 1 : 0.55
        Rectangle {
            z: -1; x: control.down ? 1 : 3; y: control.down ? 1 : 3
            width: parent.width; height: parent.height; color: control.colors.shadow
        }
    }
}
