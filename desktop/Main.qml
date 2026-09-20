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
    property bool caseRefreshPending: false
    function refreshCasesIfNeeded() {
        if (caseRefreshPending && libraryPanel.visible && !workbench.busy) {
            caseRefreshPending = false
            libraryPanel.refresh()
        }
    }
    function openInbox() { inboxPopup.open(); workbench.refreshInbox() }
    property bool loading: true
    property bool dirty: false
    property int expanded: -1
    property string resultKind: "Ready"
    property string rawOutput: ""
    property string summaryOutput: "Ready to check Guest access.\n\nRun sample checks below for observed results. No account or API key is needed. This is a synthetic fixture, not a check of a real project."
    property var collected: null
    property int resultView: 0
    property string errorMessage: ""
    property string runnerCheck: "guest_access_fixture"
    // Published model and aliases: https://docs.typesafe.ai/models
    property var publishedModels: ["jev-latest", "jev-1.13.0", "jev-preview"]

    property var returnFocus: null
    property var workflowData: JSON.parse(workbench.workflowView)
    property var editorShared: workflowData.case || null
    property var integration: workflowData.integration || ({})
    property var lastClaudeCall: (integration.activity || []).find(x => x.host === "claude") || null
    property bool claudeConfigured: (integration.profiles || []).some(x => x.configured)
    property string assistantLabel: lastClaudeCall ? "Claude activity received" : claudeConfigured ? "Claude setup saved" : "Set up Claude"
    property string sharingLabel: {
        const hosts = editorShared ? editorShared.shared_with.filter(x => x !== "preview") : []
        return workflowData.archived ? "Archived; restore in Cases to share" : hosts.length ? "Shared with " + hosts.join(", ") + (dirty ? "; saved copy only" : workflowData.saved_snapshot_current === false ? "; shared copy is older" : "") : "Not shared with assistants"
    }
    function rememberFocus() { if (!connectionPanel.visible && !libraryPanel.visible) returnFocus = root.activeFocusItem; libraryPanel.visible = false }
    function openCases() { rememberFocus(); connectionPanel.close(); libraryPanel.historyPage = false; libraryPanel.visible = true; libraryPanel.forceActiveFocus(); libraryPanel.refresh() }
    function openCaseHistory(caseId) { rememberFocus(); connectionPanel.close(); libraryPanel.historyPage = true; libraryPanel.selectedId = caseId; libraryPanel.visible = true; libraryPanel.forceActiveFocus(); libraryPanel.refresh() }
    function openSavedCase(caseId) { if (!root.dirty || workbench.confirmDiscard()) workbench.workflow("open_case", JSON.stringify({case_id: caseId})) }
    function showHistoryEvent(item) {
        const details = item.details || ({})
        root.rawOutput = JSON.stringify(details, null, 2)
        const title = libraryPanel.timeline.case ? libraryPanel.timeline.case.title + " · " + libraryPanel.timeline.case.case_id.slice(-8) : "Unlinked run"
        let text = title + "\n" + item.label + " · " + item.status + "\n" + libraryPanel.date(item.created_at) + "\nVerification: " + item.verification + "\n\n" + item.summary
        if (details.result) text = title + "\n\n" + root.describeResult(details.result)
        if (details.outcome) {
            const outcome = details.outcome
            const assertions = outcome.verification && outcome.verification.assertions ? outcome.verification.assertions : []
            for (const assertion of assertions)
                text += "\n\n" + root.assertionText(assertion)
            if (outcome.error) text += "\n\n" + outcome.error
            if (outcome.response) {
                text += "\n\nJev answers are hypotheses."
                for (const name in outcome.response.answers) text += "\n" + name + ": " + JSON.stringify(outcome.response.answers[name])
            }
        }
        else if (item.kind === "evidence") text += "\n\n" + (details.content || "")
        else if (item.kind === "proposal") text += "\n\nExpected: " + (details.expected_result || "") + "\nNo check runs until you approve its exact inputs."
        root.summaryOutput = text; root.resultView = 0; root.resultKind = "Case history"; root.collected = null
    }
    function openActivity() { rememberFocus(); connectionPanel.activity() }
    function reviewProposal() { rememberFocus(); connectionPanel.review() }
    function openConnections() { rememberFocus(); connectionPanel.connections(); workbench.workflow("status") }
    function openSharing() { rememberFocus(); connectionPanel.sharing(); workbench.workflow("status") }
    function startSample(fresh = false) { if (!root.dirty || workbench.confirmDiscard()) workbench.openSample(fresh) }
    function startStoryWorld(worldId) { if (!root.dirty || workbench.confirmDiscard()) workbench.openStoryWorld(worldId) }
    function showWorkflowResults(view) {
        const result = {case: view.case, records: view.records || ({})}
        root.rawOutput = JSON.stringify(result, null, 2)
        root.summaryOutput = connectionPanel.results(result)
        root.resultKind = "Assistant workflow"
        root.collected = null
        root.resultView = 0
    }
    function markDirty() { if (!loading) dirty = true }
    function document() {
        try {
            return JSON.stringify({schema_version: 1, title: testTitle.text, model: modelSelector.currentText,
                state: JSON.parse(statePane.text), primitives: JSON.parse(primitivesPane.text), instructions: instructionsPane.text,
                runner: {check: root.runnerCheck, iterations: root.runnerCheck === "guest_access_fixture" ? repetitions.currentIndex + 1 : 1}})
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
        runnerCheck = value.runner ? value.runner.check : "guest_access_fixture"
        repetitions.currentIndex = value.runner ? value.runner.iterations - 1 : 0
        collected = null
        resultKind = "Ready"
        rawOutput = ""
        summaryOutput = runnerCheck === "guest_access_fixture"
            ? "Ready to check " + value.title + ".\n\nRun sample checks below, or share the saved case with an assistant. Local checks use a synthetic fixture; they do not test a real project."
            : "Ready to explore " + value.title + ".\n\nShare this fictional case with an assistant. Its decisions remain an unverified proposal until you approve the exact named local fixture."
        loading = false; dirty = false
        Qt.callLater(function() { statePane.showStart(); primitivesPane.showStart(); instructionsPane.showStart() })
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
    function assertionText(assertion) {
        if (assertion.decision !== undefined)
            return (assertion.name || assertion.id) + ": chose " + assertion.decision + "; fixture expected " + assertion.expected_decision + "; " + (assertion.passed ? "PASSED" : "FAILED")
        return assertion.role + ": HTTP " + assertion.status + "; protected content " + (assertion.protected_content_present ? "present" : "absent") + "; " + (assertion.passed ? "PASSED" : "FAILED")
    }
    function describeResult(result) {
        let text = result.summary + "\n\n"
        text += "Verification: " + result.verification + "\nStatus: " + result.status + "\nElapsed: " + result.elapsed_seconds + " seconds\n"
        if (result.error) text += "\nError: " + result.error + "\n"
        if (result.checks) {
            text += "\nCompleted iterations: " + result.iterations.length + "\n"
            text += "\n" + result.checks.source + "\nVerification: " + result.verification + "\n"
            for (let item of result.checks.observations) text += "\n" + root.assertionText(item) + "\n"
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
            if (libraryPanel.visible) { caseRefreshPending = true; Qt.callLater(root.refreshCasesIfNeeded) }
        }
        function onBusyChanged() { if (!workbench.busy) Qt.callLater(root.refreshCasesIfNeeded) }
        function onReviewChanged() {
            if (JSON.parse(workbench.reviewView).case) {
                inboxPopup.close()
                libraryPanel.visible = false
                connectionPanel.review()
            }
        }
        function onWorkflowChanged() {
            let view = JSON.parse(workbench.workflowView)
            if (view.demo_folder) root.reviewProposal()
        }
        function onWorkflowRunFinished(text) { root.showWorkflowResults(JSON.parse(text)) }
        function onCaseLoaded(text) { libraryPanel.visible = false; root.loadCase(text); workbench.clearIncomingReview(); connectionPanel.close() }
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
    Shortcut { sequence: "Escape"; onActivated: { if (libraryPanel.visible) libraryPanel.close(); else if (connectionPanel.visible) connectionPanel.close(); else root.expanded = -1 } }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 18; spacing: 10
        RowLayout {
            Layout.fillWidth: true; spacing: 12
            Text { text: "Jev Workbench"; color: root.colors.ink; font.family: "Segoe UI"; font.pixelSize: 25; font.weight: Font.Bold }
            Text { text: "v" + Application.version; color: root.colors.muted; font.pixelSize: 12; Layout.fillWidth: true }
            BlockButton { objectName: "inboxButton"; colors: root.colors; primary: workbench.pendingCount > 0; text: "Inbox (" + workbench.pendingCount + ")"; onClicked: root.openInbox() }
            BlockButton { objectName: "assistantSetupButton"; colors: root.colors; text: root.assistantLabel; enabled: !workbench.busy; onClicked: root.openConnections() }
            ThemeComboBox {
                colors: root.colors; id: themePicker; model: ["Light", "Night Shift", "System"]
                currentIndex: workbench.theme === "Dark" ? 1 : workbench.theme === "Light" ? 0 : 2
                onActivated: workbench.theme = currentIndex === 1 ? "Dark" : currentText
                Accessible.name: "Color theme"
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 10
            Text { text: "Case"; color: root.colors.ink; font.bold: true }
            TextField {
                id: testTitle; objectName: "caseTitle"; Layout.fillWidth: true; Layout.minimumWidth: 160
                color: root.colors.ink; onTextEdited: root.markDirty(); enabled: !workbench.busy
                background: Rectangle { color: root.colors.surface; border.color: root.colors.border; border.width: 2 }
                Accessible.name: "Case name"
            }
            BlockButton { objectName: "savedCasesButton"; colors: root.colors; text: "Cases"; enabled: !workbench.busy; onClicked: root.openCases() }
            BlockButton { objectName: "saveCaseButton"; colors: root.colors; text: "Save case"; enabled: !workbench.busy; onClicked: root.save(false) }
            BlockButton { objectName: "shareCaseButton"; colors: root.colors; text: "Share case"; enabled: !workbench.busy; onClicked: root.openSharing() }
            BlockButton { id: sampleButton; objectName: "newSampleButton"; colors: root.colors; text: "Sample"; enabled: !workbench.busy; onClicked: sampleMenu.popup(sampleButton, 0, sampleButton.height) }
        }
        RowLayout {
            Layout.fillWidth: true
            Text { objectName: "caseContext"; text: (root.dirty ? "Unsaved edits" : workbench.caseFolder ? "Saved" : "Sample draft") + "  ·  " + root.sharingLabel; color: root.colors.muted; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
            BlockButton { id: questionButton; objectName: "questionButton"; colors: root.colors; text: "Add question"; implicitHeight: 30; enabled: !workbench.busy; onClicked: questionMenu.popup(questionButton, 0, questionButton.height + 4) }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
        SplitView {
            id: verticalSplit; objectName: "workspaceEditors"; orientation: Qt.Vertical
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
                    expanded: root.expanded === 0; enabled: !workbench.busy
                    onEdited: root.markDirty(); onMaximize: root.expanded = expanded ? -1 : 0
                }
                EditorPane {
                    id: primitivesPane; colors: root.colors; dark: root.dark; title: "PRIMITIVES"; subtitle: "primitives.json"
                    footer: "Edit the options Jev evaluates. Each question is independent."
                    SplitView.fillWidth: true; SplitView.minimumWidth: 260
                    visible: root.expanded < 0 || root.expanded === 1
                    expanded: root.expanded === 1; enabled: !workbench.busy
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
                    expanded: root.expanded === 2; enabled: !workbench.busy
                    onEdited: root.markDirty(); onMaximize: root.expanded = expanded ? -1 : 2
                }
                ColumnLayout {
                    visible: root.expanded < 0 || root.expanded === 3
                    SplitView.fillWidth: true; SplitView.minimumWidth: 260; spacing: 6
                    RowLayout {
                        BlockButton { colors: root.colors; text: "Summary"; primary: root.resultView === 0; implicitHeight: 30; implicitWidth: 80; onClicked: root.resultView = 0 }
                        BlockButton { colors: root.colors; text: "Raw JSON"; primary: root.resultView === 1; implicitHeight: 30; implicitWidth: 86; onClicked: root.resultView = 1 }
                        Item { Layout.fillWidth: true }
                        BlockButton { colors: root.colors; objectName: "caseHistoryButton"; text: "History"; implicitHeight: 30; implicitWidth: 92; enabled: !workbench.busy; onClicked: root.openCaseHistory(root.editorShared ? root.editorShared.case_id : "") }
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
        Pane {
            id: libraryPanel; objectName: "caseLibraryPanel"
            visible: false; padding: 14; focus: visible
            Layout.preferredWidth: Math.min(480, root.width * 0.38); Layout.fillHeight: true
            property bool historyPage: false
            property string selectedId: ""
            property var data: JSON.parse(workbench.caseLibraryView)
            property var timeline: JSON.parse(workbench.caseHistoryView)
            property var selectedEvent: null
            property var archiveTarget: null
            property var filtered: (data.cases || []).filter(x => !caseSearch.text || x.title.toLowerCase().indexOf(caseSearch.text.toLowerCase()) >= 0 || x.case_id.indexOf(caseSearch.text) >= 0)
            function refresh() {
                if (workbench.busy) return
                workbench.workflow(historyPage ? "case_history" : "case_list", JSON.stringify(historyPage ? {case_id: selectedId} : {archived: caseFilter.currentIndex === 1}))
            }
            function close() { visible = false; if (root.returnFocus) root.returnFocus.forceActiveFocus(Qt.OtherFocusReason) }
            function date(value) { return value ? new Date(value).toLocaleString(Qt.locale(), Locale.ShortFormat) : "Date unavailable" }
            Keys.onEscapePressed: event => { close(); event.accepted = true }
            background: Rectangle { color: root.colors.surface; border.color: root.colors.border; border.width: 2 }
            contentItem: ColumnLayout {
                spacing: 10
                RowLayout {
                    Text { text: libraryPanel.historyPage ? "Case history" : "Saved cases"; color: root.colors.ink; font.pixelSize: 20; font.bold: true; Layout.fillWidth: true }
                    BlockButton { objectName: "closeCaseLibrary"; colors: root.colors; text: "Close"; onClicked: libraryPanel.close() }
                }
                RowLayout {
                    visible: !libraryPanel.historyPage
                    TextField { id: caseSearch; objectName: "caseSearch"; Layout.fillWidth: true; placeholderText: "Find a case"; placeholderTextColor: root.colors.muted; color: root.colors.ink; Accessible.name: "Find a saved case"; background: Rectangle { color: root.colors.surface; border.color: root.colors.border; border.width: 1 } }
                    ThemeComboBox { id: caseFilter; colors: root.colors; model: ["Active", "Archived"]; enabled: !workbench.busy; onActivated: libraryPanel.refresh(); Accessible.name: "Case list filter" }
                }
                Text {
                    visible: libraryPanel.historyPage; Layout.fillWidth: true; wrapMode: Text.Wrap; textFormat: Text.PlainText; color: root.colors.ink; font.bold: true
                    text: libraryPanel.timeline.case ? libraryPanel.timeline.case.title + " · " + libraryPanel.timeline.case.case_id.slice(-8) : "Runs without a case link"
                }
                Text { visible: libraryPanel.historyPage && !!libraryPanel.timeline.case && !!root.editorShared && libraryPanel.timeline.case.case_id !== root.editorShared.case_id; text: "Viewing another case. Your editor contents stay in place."; color: root.colors.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                RowLayout {
                    BlockButton { colors: root.colors; text: libraryPanel.historyPage ? "All cases" : "Open from folder"; enabled: !workbench.busy
                        onClicked: { if (libraryPanel.historyPage) root.openCases(); else if (!root.dirty || workbench.confirmDiscard()) workbench.openCase() } }
                    Item { Layout.fillWidth: true }
                    BlockButton { colors: root.colors; text: "Refresh"; enabled: !workbench.busy; onClicked: libraryPanel.refresh() }
                }
                Text {
                    visible: !libraryPanel.historyPage && !libraryPanel.filtered.length
                    text: workbench.busy ? "Loading saved cases…" : caseSearch.text ? "No cases match your search." : caseFilter.currentIndex === 1 ? "No archived cases." : "No saved cases yet. Open a saved folder or start a sample."
                    color: root.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap
                }
                Text { visible: libraryPanel.historyPage && !(libraryPanel.timeline.events || []).length; text: workbench.busy ? "Loading history…" : "No recorded activity for this case yet."; color: root.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                ScrollView {
                    id: caseScroll; Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; clip: true
                    ColumnLayout {
                        width: caseScroll.availableWidth; spacing: 14
                        Repeater {
                            model: libraryPanel.historyPage ? [] : libraryPanel.filtered
                            ColumnLayout {
                                required property var modelData; required property int index; Layout.fillWidth: true; spacing: 5
                                Text { textFormat: Text.PlainText; text: modelData.title; font.bold: true; font.pixelSize: 15; color: root.colors.ink; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Text { visible: !!root.editorShared && root.editorShared.case_id === modelData.case_id; text: "Open in editors"; color: root.colors.ink; font.bold: true }
                                Text { text: libraryPanel.date(modelData.updated_at) + " · " + modelData.case_id.slice(-8); color: root.colors.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Text { text: modelData.shared_with.length ? "Shared with " + modelData.shared_with.join(", ") : "Private"; color: root.colors.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Text { text: modelData.last_result; color: root.colors.ink; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Text { visible: !modelData.available; text: "Saved files unavailable. Use Open from folder to locate them."; color: root.colors.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Flow {
                                    Layout.fillWidth: true; spacing: 8
                                    BlockButton { objectName: index === 0 ? "openFirstSavedCase" : "openSavedCase"; colors: root.colors; text: "Open"; visible: !modelData.archived; enabled: !workbench.busy && modelData.available
                                        onClicked: root.openSavedCase(modelData.case_id) }
                                    BlockButton { objectName: index === 0 ? "historyFirstSavedCase" : "historySavedCase"; colors: root.colors; text: "History"; enabled: !workbench.busy; onClicked: root.openCaseHistory(modelData.case_id) }
                                    BlockButton { colors: root.colors; text: modelData.archived ? "Restore" : "Archive"; enabled: !workbench.busy
                                        onClicked: {
                                            if (modelData.archived) workbench.workflow("restore_case", JSON.stringify({case_id: modelData.case_id, archived: true}))
                                            else { libraryPanel.archiveTarget = modelData; archiveDialog.open() }
                                        } }
                                }
                                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: root.colors.border }
                            }
                        }
                        Repeater {
                            model: libraryPanel.historyPage ? libraryPanel.timeline.events || [] : []
                            ColumnLayout {
                                required property var modelData; required property int index; Layout.fillWidth: true; spacing: 5
                                Text { text: modelData.label + " · " + modelData.status; font.bold: true; color: root.colors.ink; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Text { text: libraryPanel.date(modelData.created_at) + " · " + modelData.actor; color: root.colors.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Text { textFormat: Text.PlainText; text: modelData.summary; color: root.colors.ink; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Text { text: "Verification: " + modelData.verification; color: root.colors.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Flow {
                                    Layout.fillWidth: true; spacing: 8
                                    BlockButton { objectName: index === 0 ? "showFirstHistoryEvent" : "showHistoryEvent"; colors: root.colors; text: "Show record"; enabled: !workbench.busy; onClicked: root.showHistoryEvent(modelData) }
                                    BlockButton { colors: root.colors; text: "Review proposal"; visible: modelData.kind === "proposal"; enabled: !workbench.busy; onClicked: workbench.reviewIncoming(libraryPanel.selectedId, modelData.proposal_id) }
                                }
                                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: root.colors.border }
                            }
                        }
                    }
                }
                Text { visible: libraryPanel.historyPage; text: libraryPanel.timeline.notice || ""; color: root.colors.muted; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Text { text: (libraryPanel.historyPage ? libraryPanel.timeline.warnings || [] : libraryPanel.data.warnings || []).join("\n"); visible: text.length > 0; color: root.colors.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                BlockButton { visible: !libraryPanel.historyPage && !libraryPanel.filtered.length && caseFilter.currentIndex === 0 && !caseSearch.text; colors: root.colors; text: "Open sample"; enabled: !workbench.busy; onClicked: root.startSample(false) }
                BlockButton { visible: !libraryPanel.historyPage && libraryPanel.data.unlinked_count > 0; colors: root.colors; text: "Runs without a case link (" + (libraryPanel.data.unlinked_count || 0) + ")"; enabled: !workbench.busy; onClicked: root.openCaseHistory("") }
            }
        }

        ConnectionPanel {
            id: connectionPanel; colors: root.colors; editorDirty: root.dirty
            Layout.preferredWidth: Math.min(460, root.width * 0.38)
            Layout.fillHeight: true
            onDismissed: { if (root.returnFocus) root.returnFocus.forceActiveFocus(Qt.OtherFocusReason) }
            onSaveRequested: root.save(false)
            onSampleRequested: root.startSample()
            onOpenInboxRequested: { connectionPanel.close(); root.openInbox() }
            onUseState: function(state) {
                if (root.dirty) { root.showError("Save your edits before accepting incoming state."); return }
                statePane.text = JSON.stringify(state, null, 2); root.markDirty(); connectionPanel.close()
            }
            onShowResults: function(view) { root.showWorkflowResults(view); connectionPanel.close() }
        }
        }
        Text { text: workbench.status; color: root.colors.muted; Layout.fillWidth: true; elide: Text.ElideRight; font.pixelSize: 12 }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 72
            color: root.colors.heading; border.color: root.colors.border; border.width: 2
            RowLayout {
                anchors.fill: parent; anchors.margins: 12; spacing: 14
                BlockButton { id: actionsButton; colors: root.colors; text: "Actions ↑"; enabled: !workbench.busy; onClicked: actionsMenu.popup(actionsButton, 0, -actionsMenu.height) }
                Text {
                    text: runMode.currentIndex === 0 ? (root.runnerCheck === "guest_access_fixture" ? "Synthetic fixture • no API cost" : "Story fixtures run only after proposal approval") : "Sends State to TypeSafe • uses API credits"
                    color: root.colors.ink; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.Wrap
                }
                ThemeComboBox {
                    colors: root.colors
                    id: runMode; objectName: "runMode"; model: ["Sample checks", "Jev assessment"]; enabled: !workbench.busy
                    Accessible.name: "Run mode"
                    palette.window: root.colors.surface; palette.base: root.colors.surface; palette.button: root.colors.surface
                    palette.text: root.colors.ink; palette.buttonText: root.colors.ink
                }
                ThemeComboBox {
                    id: modelSelector; objectName: "modelSelector"; colors: root.colors
                    Layout.preferredWidth: 145; model: root.publishedModels
                    visible: runMode.currentIndex === 1; enabled: !workbench.busy
                    onActivated: root.markDirty(); Accessible.name: "Jev model"
                }
                ThemeComboBox {
                    colors: root.colors
                    id: repetitions; model: ["1 pass", "2 passes", "3 passes"]
                    visible: runMode.currentIndex === 0 && root.runnerCheck === "guest_access_fixture"; enabled: !workbench.busy
                    onActivated: root.markDirty()
                    Accessible.name: "Local check repetitions"
                }
                BlockButton { colors: root.colors; text: "Preview request"; enabled: !workbench.busy; onClicked: { let text = root.document(); if (text) workbench.preview(text) } }
                BlockButton {
                    id: runButton; objectName: "runButton"; colors: root.colors; primary: true
                    enabled: workbench.busy || runMode.currentIndex === 1 || root.runnerCheck === "guest_access_fixture"
                    text: workbench.busy ? "Stop" : (runMode.currentIndex === 0 ? (root.runnerCheck === "guest_access_fixture" ? "Run sample checks" : "Approve proposal to run") : "Ask Jev")
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
    Dialog {
        id: archiveDialog; title: "Archive case"; anchors.centerIn: parent; width: Math.min(500, root.width - 48); modal: true
        palette.window: root.colors.surface; palette.text: root.colors.ink
        background: Rectangle { color: root.colors.surface; border.color: root.colors.border; border.width: 2 }
        contentItem: Text { textFormat: Text.PlainText; color: root.colors.ink; wrapMode: Text.Wrap; text: libraryPanel.archiveTarget ? "Archive “" + libraryPanel.archiveTarget.title + "”? This removes it from active cases and revokes assistant access. Saved files and history are kept. Restoring does not share it again." : "" }
        footer: DialogButtonBox {
            BlockButton { colors: root.colors; text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            BlockButton { colors: root.colors; text: "Archive case"; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole }
            onRejected: archiveDialog.close()
            onAccepted: { workbench.workflow("archive_case", JSON.stringify({case_id: libraryPanel.archiveTarget.case_id, archived: caseFilter.currentIndex === 1})); archiveDialog.close() }
        }
    }
    Menu {
        id: sampleMenu; palette.window: root.colors.surface; palette.text: root.colors.ink
        ThemeMenuItem { colors: root.colors; text: "Open existing sample"; onTriggered: root.startSample(false) }
        ThemeMenuItem { colors: root.colors; text: "Create new sample"; onTriggered: root.startSample(true) }
        MenuSeparator {}
        ThemeMenuItem { colors: root.colors; text: "The Astral Post Office"; onTriggered: root.startStoryWorld("astral-post-office") }
        ThemeMenuItem { colors: root.colors; text: "The Lantern Room"; onTriggered: root.startStoryWorld("lantern-room") }
        ThemeMenuItem { colors: root.colors; text: "The Museum of Tiny Planets"; onTriggered: root.startStoryWorld("museum-of-tiny-planets") }
        ThemeMenuItem { colors: root.colors; text: "The Pocket Weather Bureau"; onTriggered: root.startStoryWorld("pocket-weather-bureau") }
    }
    Menu {
        id: actionsMenu
        palette.window: root.colors.surface; palette.text: root.colors.ink
        MenuItem { text: "New test"; onTriggered: { if (!dirty || workbench.confirmDiscard()) workbench.newCase() } }
        MenuItem { text: "Open from folder...    Ctrl+O"; onTriggered: { if (!dirty || workbench.confirmDiscard()) workbench.openCase() } }
        MenuItem { text: "Save test    Ctrl+S"; onTriggered: root.save(false) }
        MenuItem { text: "Save as..."; onTriggered: root.save(true) }
        MenuSeparator {}
        MenuItem { text: "Show files"; onTriggered: workbench.showFolder() }
        MenuItem { text: "Assistant setup..."; onTriggered: root.openConnections() }
        MenuItem { text: "Share saved case..."; onTriggered: root.openSharing() }
        MenuItem { text: "Evidence from assistant..."; onTriggered: { root.rememberFocus(); connectionPanel.open(); connectionPanel.showEvidence() } }
        MenuItem { text: "Activity and diagnostics..."; onTriggered: root.openActivity() }
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
