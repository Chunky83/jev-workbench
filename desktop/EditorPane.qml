import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import JevWorkbench

Rectangle {
    id: pane
    required property var colors
    property string title
    property string subtitle
    property string footer
    property bool readOnly: false
    property bool expanded: false
    property bool dark: false
    property string syntaxLanguage: "json"
    property alias text: editor.text
    signal edited()
    signal maximize()
    function showStart() {
        editor.cursorPosition = 0
        editorScroll.ScrollBar.vertical.position = 0
    }
    color: colors.surface
    border.color: colors.border
    border.width: 2
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 2; spacing: 0
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 52
            color: pane.colors.heading
            RowLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: 12
                Text { text: pane.title; color: pane.colors.ink; font.pixelSize: 17; font.bold: true; font.family: "Segoe UI" }
                Text { visible: pane.width >= 360; text: pane.subtitle; color: pane.colors.muted; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                Item { visible: pane.width < 360; Layout.fillWidth: true }
                BlockButton {
                    colors: pane.colors; text: pane.expanded ? "Restore" : "Expand"
                    implicitHeight: 30; implicitWidth: 76; onClicked: pane.maximize()
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 2; color: pane.colors.border }
        ScrollView {
            id: editorScroll
            contentWidth: availableWidth
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true
            TextArea {
                id: editor
                objectName: pane.title + "Editor"
                readOnly: pane.readOnly
                selectByMouse: true
                persistentSelection: true
                wrapMode: TextEdit.Wrap
                color: pane.colors.ink
                selectionColor: pane.colors.primary
                selectedTextColor: "white"
                textFormat: TextEdit.PlainText
                verticalAlignment: TextEdit.AlignTop
                font.family: Qt.platform.os === "osx" ? "Menlo" : "Consolas"; font.pixelSize: 15
                padding: 18
                background: Rectangle { color: pane.colors.surface }
                onTextChanged: { pane.edited(); if (pane.readOnly) Qt.callLater(pane.showStart) }
                Component.onCompleted: pane.showStart()
                Accessible.name: pane.title + " editor"
                SyntaxHighlighter {
                    target: editor.textDocument
                    language: pane.syntaxLanguage
                    dark: pane.dark
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: pane.colors.border }
        Text {
            Layout.fillWidth: true; Layout.margins: 9
            text: pane.footer; color: pane.colors.muted; font.pixelSize: 11
            elide: Text.ElideRight
        }
    }
}
