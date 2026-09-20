import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    required property var colors
    hoverEnabled: true
    implicitHeight: 40
    implicitWidth: 140
    leftPadding: 12
    rightPadding: 30

    // Keep the closed control readable while its popup is pressed/open.
    contentItem: Text {
        text: control.displayText
        color: control.colors.ink
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        opacity: control.enabled ? 1 : 0.5
    }
    background: Rectangle {
        color: control.down || control.hovered ? control.colors.heading : control.colors.surface
        // Keep keyboard focus visible without leaving a ring after mouse clicks.
        border.color: control.visualFocus ? control.colors.focus : control.colors.border
        border.width: control.visualFocus ? 3 : 2
    }
    indicator: Text {
        text: control.popup.visible ? "▴" : "▾"
        color: control.colors.ink
        font.pixelSize: 18
        x: control.width - width - 10
        anchors.verticalCenter: parent.verticalCenter
    }
    delegate: ItemDelegate {
        id: option
        required property int index
        required property var modelData
        width: control.width
        height: 40
        text: modelData
        highlighted: control.highlightedIndex === index
        hoverEnabled: true
        contentItem: Text {
            text: option.text
            color: option.highlighted || option.hovered ? "#ffffff" : control.colors.ink
            font.family: control.font.family
            font.pixelSize: control.font.pixelSize
            font.bold: control.currentIndex === option.index
            verticalAlignment: Text.AlignVCenter
            leftPadding: 10
        }
        background: Rectangle {
            color: option.highlighted || option.hovered ? control.colors.primary : control.colors.surface
        }
    }
    popup: Popup {
        y: control.height + 3
        width: control.width
        padding: 2
        implicitHeight: contentItem.implicitHeight + topPadding + bottomPadding
        topMargin: 6
        bottomMargin: 6
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.delegateModel
            currentIndex: control.highlightedIndex
            highlightMoveDuration: 0
        }
        background: Rectangle {
            color: control.colors.surface
            border.color: control.colors.border
            border.width: 2
        }
    }
}
