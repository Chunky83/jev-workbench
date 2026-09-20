import QtQuick
import QtQuick.Controls

MenuItem {
    id: control
    required property var colors
    hoverEnabled: true
    implicitHeight: 42
    property bool emphasized: hovered || highlighted || activeFocus
    contentItem: Text {
        text: control.text
        color: control.emphasized ? "#ffffff" : control.colors.ink
        font: control.font
        verticalAlignment: Text.AlignVCenter
        leftPadding: 10
        rightPadding: 10
    }
    background: Rectangle {
        color: control.emphasized ? control.colors.primary : control.colors.surface
    }
}
