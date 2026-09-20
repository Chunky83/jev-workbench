import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    visible: true
    width: 1440; height: 960
    minimumWidth: 1000; minimumHeight: 700
    title: (dirty ? "* " : "") + testTitle.text + " | Jev Workbench " + Application.version
    property bool systemDark: Application.styleHints.colorScheme === Qt.Dark
    property bool dark: workbench.theme === "Dark" || (workbench.theme === "System" && systemDark)
    property var colors: ({
        background: dark ? "#111214" : "#e9e9eb",
        surface: dark ? "#1d1f24" : "#ffffff",
        ink: dark ? "#f3f3f5" : "#16171c",
        muted: dark ? "#b8bcc8" : "#505466",
        heading: dark ? "#30364c" : "#dfe3ff",
        primary: dark ? "#4854c6" : "#3846bb",
        focus: dark ? "#ffee8b" : "#3846bb",
        border: dark ? "#9299b2" : "#17181c",
        shadow: "#090a0c",
        accent: dark ? "#373523" : "#fff4aa"
    })
    color: colors.background
    palette.window: colors.surface
    palette.base: colors.surface
    palette.button: colors.surface
    palette.text: colors.ink
    palette.windowText: colors.ink
    palette.buttonText: colors.ink
    palette.mid: colors.muted
    palette.dark: colors.ink
    palette.light: colors.surface
    palette.midlight: colors.heading
    palette.highlight: colors.primary
    palette.highlightedText: "white"
    property var inboxData: JSON.parse(workbench.inboxView)
    property var incomingProposals: inboxData.proposals || []
    property var notifiedProposals: []
    property int inboxNotificationCount: 0
    function openInbox() { inboxPopup.open(); workbench.refreshInbox() }
    property bool loading: true
    property bool dirty: false
    property bool guidedMode: Qt.application.arguments.indexOf("--ui-smoke") < 0 && Qt.application.arguments.indexOf("--capture-question") < 0 && Qt.application.arguments.indexOf("--capture-model") < 0 && Qt.application.arguments.indexOf("--capture-dropdown") < 0
    property int expanded: -1
    property string resultKind: "Welcome"
    property string rawOutput: ""
    property string summaryOutput: "Open a saved test, or start with Guest access.\n\n1. Run local checks to test a synthetic HTTP fixture.\n2. Use collected evidence to place the fresh observations in State.\n3. Preview the exact request.\n4. Choose Live Jev when you want to send it.\n\nLocal checks do not contact your website or TypeSafe."
    property var collected: null
    property int resultView: 0
    property string errorMessage: ""
    // Published model and aliases: https://docs.typesafe.ai/models
    property var publishedModels: ["jev-latest", "jev-1.13.0", "jev-preview"]

    function openActivity() { connectionPanel.activity() }
    function reviewProposal() { connectionPanel.review() }
    function openConnections() { connectionPanel.connections(); workbench.workflow("status") }
    function showWorkflowResults(view) {
        const result = {case: view.case, records: view.records || ({})}
        root.rawOutput = JSON.stringify(result, null, 2)
        root.summaryOutput = connectionPanel.results(result)
        root.resultKind = "Assistant workflow"
        root.collected = null
        root.resultView = 0
        root.guidedMode = false
    }
    function markDirty() { if (!loading) dirty = true }
    function document() {
        try {
            return JSON.stringify({schema_version: 1, title: testTitle.text, model: modelSelector.currentText,
                state: JSON.parse(statePane.text), primitives: JSON.parse(primitivesPane.text), instructions: instructionsPane.text,
                runner: {check: "guest_access_fixture", iterations: repetitions.currentIndex + 1}})
        } catch (error) { showError("Check the JSON in State and Primitives. " + error.message); return "" }
    }
    function showError(message) { errorMessage = message; errorDialog.open() }
    function loadCase(text) {
        loading = true
        let value = JSON.parse(text)
        testTitle.text = value.title
        // Keep a saved version even if it is absent from this build's catalog.
        let selectedModel = value.model || "jev-latest"
        modelSelector.model = publishedModels.indexOf(selectedModel) >= 0
            ? publishedModels : publishedModels.concat([selectedModel])
        modelSelector.currentIndex = modelSelector.model.indexOf(selectedModel)
        statePane.text = JSON.stringify(value.state, null, 2)
        primitivesPane.text = JSON.stringify(value.primitives, null, 2)
        instructionsPane.text = value.instructions
        repetitions.currentIndex = value.runner ? value.runner.iterations - 1 : 0
        collected = null
        loading = false; dirty = false
    }
    function save(asNew) { let text = document(); if (text) workbench.saveCase(text, asNew) }
    function addQuestion(kind) {
        try {
            let questions = JSON.parse(primitivesPane.text)
            let name = kind + "_question"; let count = 2
            while (questions[name] !== undefined) { name = kind + "_question_" + count; count++ }
            let question = {type: kind, instructions: "Replace this with a specific question about the evidence."}
            if (kind === "choice") question.criteria = {yes: "Describe this option.", no: "Describe this option.", unknown: "Evidence is insufficient."}
            if (kind === "score") question.criteria = ["No supporting evidence", "Partial supporting evidence", "Complete supporting evidence"]
            if (kind === "noul") question.criteria = {true: "Evidence supports yes.", false: "Evidence supports no."}
            questions[name] = question
            primitivesPane.text = JSON.stringify(questions, null, 2)
        } catch (error) { showError("Fix the Primitives JSON before adding a question.") }
    }
    function describeResult(result) {
        let text = result.summary + "\n\n"
        text += "Verification: " + result.verification + "\nStatus: " + result.status + "\nElapsed: " + result.elapsed_seconds + " seconds\n"
        if (result.error) text += "\nError: " + result.error + "\n"
        if (result.checks) {
            text += "\nCompleted iterations: " + result.iterations.length + "\n"
            text += "\n" + result.checks.source + "\nVerification: " + result.verification + "\n"
            for (let item of result.checks.observations) text += "\n" + item.id + "  " + item.role + " → HTTP " + item.status + "\nProtected content present: " + item.protected_content_present + "\nAssertion: " + (item.passed ? "PASSED" : "FAILED") + "\n"
        }
        if (result.response) {
            text += "\nModel: " + result.response.model + "\nVerification: not performed\n"
            for (let name in result.response.answers) {
                let answer = result.response.answers[name]
                text += "\n" + name + " [" + answer.type + "]\n" + JSON.stringify(answer, null, 2) + "\n"
            }
            text += "\nToken usage: " + JSON.stringify(result.response.usage) + "\nConfidence describes the answer distribution, not verified accuracy.\n"
        }
        return text + "\nRun: " + result.run_id + "\nSaved run: " + result.folder
    }
    Component.onCompleted: loadCase(workbench.initialCase())
    onClosing: function(close) {
        if (workbench.busy) { close.accepted = false; showError("Stop the current operation before closing.") }
        else if (dirty) close.accepted = workbench.confirmDiscard()
    }
    Connections {
        target: workbench
        function onInboxChanged() {
            const items = JSON.parse(workbench.inboxView).proposals || []
            const unseen = items.filter(x => notifiedProposals.indexOf(x.proposal_id) < 0)
            if (unseen.length) {
                notifiedProposals = notifiedProposals.concat(unseen.map(x => x.proposal_id))
                inboxNotificationCount++
                inboxPopup.open()
                workbench.notifyIncoming()
            }
        }
        function onReviewChanged() {
            if (JSON.parse(workbench.reviewView).case) {
                inboxPopup.close()
                connectionPanel.review()
            }
        }
        function onWorkflowChanged() {
            let view = JSON.parse(workbench.workflowView)
            if (view.demo_folder) root.reviewProposal()
        }
        function onWorkflowRunFinished(text) { root.showWorkflowResults(JSON.parse(text)) }
        function onCaseLoaded(text) { root.loadCase(text) }
        function onSaved() { root.dirty = false; workbench.workflow("status") }
        function onFailed(text) { root.showError(text) }
        function onOutputReady(text, kind) {
            root.rawOutput = text; root.resultKind = kind === "preview" ? "Request preview" : kind === "history" ? "Run history" : "Run result"
            let value = JSON.parse(text)
            if (kind === "preview") { root.summaryOutput = "Nothing sent. This is the exact Jev request.\n\n" + JSON.stringify(value.request, null, 2) }
            else if (kind === "history") {
                let runs = value.runs
                let output = "Saved runs, newest first. No new API calls.\n\n"
                if (!runs.length) output += "No saved runs yet."
                for (let run of runs) output += run.run_id + "\n" + run.title + " / " + run.mode + " / " + run.status + "\nVerification: " + run.verification + "\n\n"
                if (runs.length >= 2) output += "Latest two runs (inspect inputs before comparing):\n\n" + root.describeResult(runs[1]) + "\n\n--------\n\n" + root.describeResult(runs[0])
                root.summaryOutput = output
            } else {
                root.summaryOutput = root.describeResult(value.result)
                root.collected = value.result.checks || null
            }
            root.resultView = 0
        }
    }
    Shortcut { sequence: StandardKey.Save; enabled: !workbench.busy; onActivated: root.save(false) }
    Shortcut { sequence: StandardKey.Open; enabled: !workbench.busy; onActivated: { if (!dirty || workbench.confirmDiscard()) workbench.openCase() } }
    Shortcut { sequence: "Ctrl+Return"; enabled: !workbench.busy; onActivated: runButton.clicked() }
    Shortcut { sequence: "Escape"; onActivated: root.expanded = -1 }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 18; spacing: 12
        RowLayout {
            Layout.fillWidth: true; spacing: 18
            Text { text: "Jev Workbench"; color: root.colors.ink; font.family: "Segoe UI"; font.pixelSize: 29; font.weight: Font.Black }
            Text { text: "v" + Application.version; color: root.colors.muted; font.pixelSize: 13; Layout.fillWidth: true }
            BlockButton { colors: root.colors; text: root.guidedMode ? "Advanced editor" : "Overview"; onClicked: root.guidedMode = !root.guidedMode }
            BlockButton { objectName: "inboxButton"; colors: root.colors; primary: workbench.pendingCount > 0; text: "Inbox (" + workbench.pendingCount + ")"; onClicked: root.openInbox() }
            BlockButton { colors: root.colors; text: "Connect assistants"; enabled: !workbench.busy; onClicked: root.openConnections() }
            Text { visible: !root.guidedMode && root.width > 1200; text: workbench.keyAvailable ? "TypeSafe key ready" : "TypeSafe key not set"; color: root.colors.muted; font.pixelSize: 12 }
            ThemeComboBox {
                colors: root.colors
                id: themePicker; model: ["Light", "Night Shift", "System"]
                currentIndex: workbench.theme === "Dark" ? 1 : workbench.theme === "Light" ? 0 : 2
                onActivated: workbench.theme = currentIndex === 1 ? "Dark" : currentText
                Accessible.name: "Color theme"
                palette.window: root.colors.surface; palette.base: root.colors.surface
                palette.button: root.colors.surface; palette.text: root.colors.ink; palette.buttonText: root.colors.ink
            }
        }
        RowLayout {
            visible: !root.guidedMode
            Layout.fillWidth: true; spacing: 10
            Text { text: "Test"; color: root.colors.ink; font.bold: true }
            TextField {
                id: testTitle; Layout.preferredWidth: 230; color: root.colors.ink
                onTextEdited: root.markDirty(); enabled: !workbench.busy
                background: Rectangle { color: root.colors.surface; border.color: root.colors.border; border.width: 2 }
                Accessible.name: "Test name"
            }
            Text { text: dirty ? "Unsaved edits" : workbench.caseFolder ? "Saved / unchanged" : "New test"; color: root.colors.muted; font.pixelSize: 12; Layout.fillWidth: true }
            Text { text: "Model"; color: root.colors.ink }
            ThemeComboBox {
                id: modelSelector; objectName: "modelSelector"
                colors: root.colors; Layout.preferredWidth: 170
                model: root.publishedModels
                onActivated: root.markDirty(); enabled: !workbench.busy
                Accessible.name: "Jev model"
            }
            BlockButton { id: questionButton; objectName: "questionButton"; colors: root.colors; text: "+ Question"; enabled: !workbench.busy; onClicked: questionMenu.popup(questionButton, 0, questionButton.height + 4) }
        }
        Rectangle {
            visible: root.guidedMode; Layout.fillWidth: true; Layout.fillHeight: true
            color: root.colors.surface; border.color: root.colors.border; border.width: 2
            ColumnLayout {
                anchors.centerIn: parent; width: Math.min(parent.width - 64, 820); spacing: 22
                Text { text: "What would you like to check?"; font.pixelSize: 30; font.bold: true; color: root.colors.ink; Layout.fillWidth: true; wrapMode: Text.Wrap }
                Text { text: "Connect an assistant to bring selected evidence into Workbench. You review its proposal, approve a check, and see what actually passed."; font.pixelSize: 18; color: root.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                RowLayout {
                    spacing: 14
                    BlockButton { colors: root.colors; primary: true; text: "Connect an assistant"; enabled: !workbench.busy; onClicked: root.openConnections() }
                    BlockButton { colors: root.colors; text: "Try a sample"; enabled: !workbench.busy && !root.dirty; onClicked: workbench.previewFixture() }
                    BlockButton { colors: root.colors; text: "Open a saved test"; enabled: !workbench.busy; onClicked: { if (!root.dirty || workbench.confirmDiscard()) { root.guidedMode = false; workbench.openCase() } } }
                }
                Text { text: "The sample is saved for you and needs no account or API key. It checks a synthetic guest-access example on this computer."; color: root.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                BlockButton { colors: root.colors; text: "Activity and diagnostics"; enabled: !workbench.busy; onClicked: root.openActivity() }
                Text { text: "Your workflow"; font.pixelSize: 20; font.bold: true; color: root.colors.ink }
                Text { text: "1. Connect • discover your assistant and approve setup.\n2. Share • choose the saved evidence the assistant can access.\n3. Review • approve a specific check, then read its result."; font.pixelSize: 16; lineHeight: 1.5; color: root.colors.ink; Layout.fillWidth: true; wrapMode: Text.Wrap }
                Text { text: "Current preview: synthetic checks only. Real-project checks and automatic ChatGPT setup are still to come."; color: root.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                BlockButton { colors: root.colors; text: "Review proposals and results"; visible: !!workbench.caseFolder; enabled: !workbench.busy; onClicked: { root.reviewProposal(); workbench.workflow("status") } }
            }
        }
        SplitView {
            visible: !root.guidedMode
            id: verticalSplit; orientation: Qt.Vertical
            Layout.fillWidth: true; Layout.fillHeight: true
            handle: Rectangle { implicitHeight: 10; color: root.colors.background
                Rectangle { width: 32; height: 3; color: root.colors.muted; anchors.centerIn: parent } }
            SplitView {
                orientation: Qt.Horizontal
                visible: root.expanded < 0 || root.expanded < 2
                SplitView.preferredHeight: verticalSplit.height / 2
                SplitView.minimumHeight: 160
                handle: Rectangle { implicitWidth: 12; color: root.colors.background
                    Rectangle { width: 3; height: 32; color: root.colors.muted; anchors.centerIn: parent } }
                EditorPane {
                    id: statePane; colors: root.colors; dark: root.dark; title: "STATE"; subtitle: "state.json"
                    footer: "Facts and observations. Keep secrets out of evidence."
                    SplitView.preferredWidth: verticalSplit.width / 2; SplitView.minimumWidth: 260
                    visible: root.expanded < 0 || root.expanded === 0
                    expanded: root.expanded === 0; readOnly: workbench.busy
                    onEdited: root.markDirty(); onMaximize: root.expanded = expanded ? -1 : 0
                }
                EditorPane {
                    id: primitivesPane; colors: root.colors; dark: root.dark; title: "PRIMITIVES"; subtitle: "primitives.json"
                    footer: "Edit the options Jev evaluates. Each question is independent."
                    SplitView.fillWidth: true; SplitView.minimumWidth: 260
                    visible: root.expanded < 0 || root.expanded === 1
                    expanded: root.expanded === 1; readOnly: workbench.busy
                    onEdited: root.markDirty(); onMaximize: root.expanded = expanded ? -1 : 1
                }
            }
            SplitView {
                orientation: Qt.Horizontal
                visible: root.expanded < 0 || root.expanded >= 2
                SplitView.fillHeight: true; SplitView.minimumHeight: 160
                handle: Rectangle { implicitWidth: 12; color: root.colors.background
                    Rectangle { width: 3; height: 32; color: root.colors.muted; anchors.centerIn: parent } }
                EditorPane {
                    id: instructionsPane; colors: root.colors; dark: root.dark; syntaxLanguage: "markdown"; title: "INSTRUCTIONS"; subtitle: "instructions.md"
                    footer: "Common directions, added to each question. Plain language."
                    SplitView.preferredWidth: verticalSplit.width / 2; SplitView.minimumWidth: 260
                    visible: root.expanded < 0 || root.expanded === 2
                    expanded: root.expanded === 2; readOnly: workbench.busy
                    onEdited: root.markDirty(); onMaximize: root.expanded = expanded ? -1 : 2
                }
                ColumnLayout {
                    visible: root.expanded < 0 || root.expanded === 3
                    SplitView.fillWidth: true; SplitView.minimumWidth: 260; spacing: 6
                    RowLayout {
                        BlockButton { colors: root.colors; text: "Summary"; primary: root.resultView === 0; implicitHeight: 30; onClicked: root.resultView = 0 }
                        BlockButton { colors: root.colors; text: "Raw JSON"; primary: root.resultView === 1; implicitHeight: 30; onClicked: root.resultView = 1 }
                        Item { Layout.fillWidth: true }
                        BlockButton { colors: root.colors; text: "History"; implicitHeight: 30; enabled: !workbench.busy; onClicked: workbench.history() }
                    }
                    EditorPane {
                        id: resultsPane; colors: root.colors; dark: root.dark; syntaxLanguage: root.resultView === 1 ? "json" : "log"; title: "RESULTS"; subtitle: root.resultKind
                        footer: "Read-only run record. Model judgments need independent verification."
                        Layout.fillWidth: true; Layout.fillHeight: true
                        readOnly: true; text: root.resultView === 0 ? root.summaryOutput : root.rawOutput
                        expanded: root.expanded === 3; onMaximize: root.expanded = expanded ? -1 : 3
                    }
                    BlockButton {
                        colors: root.colors; text: "Use collected evidence in State"; visible: root.collected !== null
                        enabled: !workbench.busy
                        onClicked: { statePane.text = JSON.stringify(root.collected, null, 2); root.collected = null }
                    }
                }
            }
        }
        Text { text: workbench.connectorStatus; color: root.colors.muted; Layout.fillWidth: true; elide: Text.ElideRight; font.pixelSize: 12 }
        Text { text: workbench.status; color: root.colors.muted; Layout.fillWidth: true; elide: Text.ElideRight; font.pixelSize: 12 }
        Rectangle {
            visible: !root.guidedMode
            Layout.fillWidth: true; Layout.preferredHeight: 72
            color: root.colors.heading; border.color: root.colors.border; border.width: 2
            RowLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 14
                BlockButton { id: actionsButton; colors: root.colors; text: "Actions ↑"; enabled: !workbench.busy; onClicked: actionsMenu.popup(actionsButton, 0, -actionsMenu.height) }
                Text {
                    text: runMode.currentIndex === 0 ? "Synthetic fixture • no API cost" : "Sends State to TypeSafe • uses API credits"
                    color: root.colors.ink; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.Wrap
                }
                ThemeComboBox {
                    colors: root.colors
                    id: runMode; objectName: "runMode"; model: ["Local checks", "Live Jev"]; enabled: !workbench.busy
                    Accessible.name: "Run mode"
                    palette.window: root.colors.surface; palette.base: root.colors.surface; palette.button: root.colors.surface
                    palette.text: root.colors.ink; palette.buttonText: root.colors.ink
                }
                ThemeComboBox {
                    colors: root.colors
                    id: repetitions; model: ["1 pass", "2 passes", "3 passes"]
                    visible: runMode.currentIndex === 0; enabled: !workbench.busy
                    onActivated: root.markDirty()
                    Accessible.name: "Local check repetitions"
                }
                BlockButton { colors: root.colors; text: "Preview request"; enabled: !workbench.busy; onClicked: { let text = root.document(); if (text) workbench.preview(text) } }
                BlockButton {
                    id: runButton; objectName: "runButton"; colors: root.colors; primary: true; text: workbench.busy ? "Stop" : "Run test"
                    onClicked: {
                        if (workbench.busy) workbench.cancel()
                        else { let text = root.document(); if (text) workbench.evaluate(text, runMode.currentIndex === 0 ? "local" : "live") }
                    }
                }
            }
        }
    }
    Popup {
        id: inboxPopup; objectName: "incomingPopup"
        parent: Overlay.overlay; z: 100
        x: Math.max(18, (parent.width - width) / 2); y: 76
        width: Math.min(parent.width - 48, 680); height: Math.min(parent.height - 110, 440)
        modal: false; focus: false; closePolicy: Popup.CloseOnEscape
        padding: 18
        background: Rectangle { color: root.colors.surface; border.color: root.colors.border; border.width: 3 }
        contentItem: ColumnLayout {
            spacing: 12
            RowLayout {
                Text { text: workbench.pendingCount ? "Assistant proposals are ready" : "Assistant inbox"; font.pixelSize: 22; font.bold: true; color: root.colors.ink; Layout.fillWidth: true; wrapMode: Text.Wrap }
                BlockButton { colors: root.colors; text: "Later"; onClicked: inboxPopup.close() }
            }
            Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: root.colors.muted
                text: workbench.pendingCount ? "Choose a proposal to review. No check runs until you approve it." : "No incoming proposals yet. Workbench checks automatically while this app is open." }
            Text { text: workbench.inboxStatus; color: root.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
            ScrollView { id: incomingScroll; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
                ColumnLayout { width: incomingScroll.availableWidth; spacing: 12
                    Repeater { model: root.incomingProposals
                        ColumnLayout { required property var modelData; required property int index; Layout.fillWidth: true; spacing: 6
                            Text { textFormat: Text.PlainText; text: modelData.submitted_by + " • " + modelData.title + " • " + modelData.case_id.slice(-8); font.bold: true; color: root.colors.ink; Layout.fillWidth: true; wrapMode: Text.Wrap }
                            Text { textFormat: Text.PlainText; text: modelData.summary; maximumLineCount: 3; elide: Text.ElideRight; color: root.colors.ink; Layout.fillWidth: true; wrapMode: Text.Wrap }
                            RowLayout {
                                Text { text: modelData.status === "ready" ? "Waiting for your approval" : modelData.status === "stale" ? "Case changed since submission. Review why." : "Access was revoked. Review details."; color: root.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                                BlockButton { objectName: index === 0 ? "reviewIncomingFirst" : "reviewIncomingOther"; colors: root.colors; primary: true; text: "Review proposal"; enabled: !workbench.busy
                                    onClicked: workbench.reviewIncoming(modelData.case_id, modelData.proposal_id) }
                            }
                            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: root.colors.border }
                        }
                    }
                }
            }
            Text { text: root.inboxData.notice || ""; visible: text.length > 0; color: root.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
        }
    }
    ConnectionPanel {
        id: connectionPanel; colors: root.colors; editorDirty: root.dirty
        onOpenInboxRequested: { connectionPanel.close(); root.openInbox() }
        onUseState: function(state) {
            if (root.dirty) { root.showError("Save your edits before accepting incoming state."); return }
            statePane.text = JSON.stringify(state, null, 2); root.markDirty(); connectionPanel.close()
        }
        onShowResults: function(view) {
            root.showWorkflowResults(view); connectionPanel.close()
        }
    }
    Menu {
        id: actionsMenu
        palette.window: root.colors.surface; palette.text: root.colors.ink
        MenuItem { text: "New test"; onTriggered: { if (!dirty || workbench.confirmDiscard()) workbench.newCase() } }
        MenuItem { text: "Open test...    Ctrl+O"; onTriggered: { if (!dirty || workbench.confirmDiscard()) workbench.openCase() } }
        MenuItem { text: "Save test    Ctrl+S"; onTriggered: root.save(false) }
        MenuItem { text: "Save as..."; onTriggered: root.save(true) }
        MenuSeparator {}
        MenuItem { text: "Show files"; onTriggered: workbench.showFolder() }
        MenuItem { text: "Connections and proposals..."; onTriggered: root.openConnections() }
        MenuItem { text: "API settings..."; onTriggered: keyDialog.open() }
    }
    Menu {
        id: questionMenu
        width: 270
        padding: 2
        background: Rectangle { color: root.colors.surface; border.color: root.colors.border; border.width: 2 }
        palette.window: root.colors.surface; palette.text: root.colors.ink
        ThemeMenuItem { colors: root.colors; text: "Choice: choose an option"; onTriggered: root.addQuestion("choice") }
        ThemeMenuItem { objectName: "scoreOption"; colors: root.colors; text: "Score: evaluate a rubric"; onTriggered: root.addQuestion("score") }
        ThemeMenuItem { colors: root.colors; text: "Noul: evaluate yes / no"; onTriggered: root.addQuestion("noul") }
    }
    Dialog {
        id: errorDialog; title: "Needs attention"; anchors.centerIn: parent; width: 510
        modal: true; standardButtons: Dialog.Ok
        palette.window: root.colors.surface; palette.text: root.colors.ink; palette.buttonText: root.colors.ink
        background: Rectangle { color: root.colors.surface; border.color: root.colors.border; border.width: 3 }
        contentItem: Text { text: root.errorMessage; color: root.colors.ink; wrapMode: Text.Wrap; font.pixelSize: 15 }
    }
    Dialog {
        id: keyDialog; title: "TypeSafe API settings"; anchors.centerIn: parent; width: 510
        modal: true; standardButtons: Dialog.Save | Dialog.Cancel
        palette.window: root.colors.surface; palette.text: root.colors.ink; palette.buttonText: root.colors.ink
        background: Rectangle { color: root.colors.surface; border.color: root.colors.border; border.width: 3 }
        onAccepted: { workbench.setApiKey(keyField.text); keyField.clear() }
        onRejected: keyField.clear()
        contentItem: ColumnLayout {
            spacing: 16
            Text { text: "The key stays in memory for this session. It is never saved in your test files. An environment key is also supported."; color: root.colors.ink; wrapMode: Text.Wrap; Layout.fillWidth: true }
            TextField { id: keyField; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: "TypeSafe API key"; Accessible.name: "TypeSafe API key" }
            Text { text: "Saving an empty field clears the session key. An existing environment key remains available."; color: root.colors.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
    }
}
