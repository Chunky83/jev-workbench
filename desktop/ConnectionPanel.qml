import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: panel
    objectName: "connectionPanel"
    readonly property int currentPage: pages.currentIndex
    readonly property int currentProposalCount: proposals.length
    required property var colors
    property bool editorDirty: false
    property var view: JSON.parse(workbench.workflowView)
    property var incoming: JSON.parse(workbench.reviewView)
    property bool reviewingIncoming: pages.currentIndex === 2 && !!incoming.case
    property var shared: reviewingIncoming ? incoming.case : (view.case || null)
    property var records: reviewingIncoming ? incoming.records : (view.records || ({}))
    property var proposals: reviewingIncoming ? (records.proposal || []) : (records.proposal || []).filter(x => shared && x.review_revision === shared.revision)
    property var selected: proposals.length && proposalPicker.currentIndex >= 0 ? proposals[proposalPicker.currentIndex] : null
    property var inboxItems: (JSON.parse(workbench.inboxView).proposals || [])
    property var inboxSelection: reviewingIncoming && selected ? inboxItems.find(x => x.proposal_id === selected.id) : null
    property bool alreadyApproved: !!selected && (records.approval || []).some(x => x.proposal_id === selected.id)
    property string approvalBlockReason: {
        if (workbench.busy) return "A task is running. Wait for it to finish or use Stop."
        if (alreadyApproved) return "This proposal was already approved. View its results below. To repeat the walkthrough, load a new synthetic walkthrough from Connections."
        if (editorDirty && !reviewingIncoming) return "Save your editor changes before reviewing a proposal. If the saved inputs changed, share them and request a new proposal."
        if (!shared) return "No shared case is selected. Share a saved snapshot or load the synthetic walkthrough from Connections."
        if (!selected) return "This editor case has no current proposal. Use Inbox to see incoming proposals for every case."
        if (shared.shared_with.indexOf(selected.submitted_by) < 0) return "Access for this proposal's connection was revoked. Share the case and request a new proposal."
        if (reviewingIncoming && inboxSelection && inboxSelection.status === "revoked") return "Access was revoked after this review opened. Request a new proposal after sharing again."
        if (reviewingIncoming && inboxSelection && inboxSelection.revision !== shared.revision) return "This case changed while you were reviewing. Refresh this review to see its current state."
        if (selected.review_revision !== shared.revision) return "The case changed after this proposal. Request a new proposal for the current revision, or load a fresh synthetic walkthrough."
        return ""
    }
    property var integration: view.integration || ({profiles: [], activity: [], warnings: []})
    property var profiles: integration.profiles || []
    property var profile: profiles.length === 1 ? profiles[0] : (profilePicker.currentIndex > 0 ? profiles[profilePicker.currentIndex - 1] : null)
    property var setupPlan: integration.plan || null
    property var claudeActivity: (integration.activity || []).find(x => x.host === "claude") || null
    property bool activityDetails: false
    property bool advanced: false
    property bool undoReview: false
    property bool rawProposal: false
    property var selectedRun: selected ? (records.run || []).find(x => x.proposal_id === selected.id) : null
    property var selectedOutcome: selectedRun ? (records.outcome || []).find(x => x.run_id === selectedRun.id) : null
    signal openInboxRequested()
    signal useState(var state)
    signal showResults(var view)
    title: pages.currentIndex === 2 ? "Review assistant proposal" : pages.currentIndex === 3 ? "Activity and diagnostics" : "Connect assistants"
    anchors.centerIn: parent
    width: Math.min(parent.width - 48, 960)
    height: Math.min(parent.height - 48, 720)
    modal: true
    closePolicy: Popup.CloseOnEscape
    palette.window: colors.surface; palette.text: colors.ink; palette.buttonText: colors.ink
    background: Rectangle { color: panel.colors.surface; border.color: panel.colors.border; border.width: 3 }
    function connections() { pages.currentIndex = 0; open() }
    function activity() { pages.currentIndex = 3; open(); panel.send("activity") }
    function review() { pages.currentIndex = 2; open() }
    function send(operation, data) { workbench.workflow(operation, JSON.stringify(data || {})) }
    function activityText() {
        if (!view.activity) return "Select Refresh to load activity."
        const entries = view.activity.events
        const names = {session: "Application session", setup_review: "Setup review prepared", setup_apply: "Claude setup", setup_cancel: "Setup review cancelled", setup_undo: "Claude setup restored", diagnostics: "Local connector diagnostic", demo: "Sample walkthrough", share: "Snapshot sharing", revoke: "Access revoked", budget: "Jev allowance changed", approval: "Check approved", approve: "Approved check", outcome: "Check outcome saved", inbox: "Assistant inbox updated", review_proposal: "Proposal opened for review", run: "Run", list_cases: "List shared cases", read_case: "Read shared case", submit_evidence: "Evidence received", submit_proposal: "Check proposal received", save: "Save test", open: "Open test", activity_export: "Export diagnostics", allowance_consumed: "Jev call allowance consumed"}
        let shown = activityDetails ? entries : entries.filter(x => {
            if (x.operation === "activity" || x.operation === "status") return false
            if (x.status === "started") return false
            if (x.actor === "desktop" && entries.some(y => y.actor === "worker" && y.request_id === x.request_id && y.status === x.status)) return false
            return true
        })
        if (!shown.length) return "No completed actions recorded yet. Run the local diagnostic or try the sample."
        let identity = ""
        if (activityDetails && view.diagnostic) {
            identity = "Workspace: " + (view.diagnostic.workspace_id || "Unavailable") + "\nOpened database: " + (view.diagnostic.physical_database_path || "Unavailable") + "\n\n"
        }
        return identity + shown.map(x => {
            let who = x.actor === "worker" || x.actor === "desktop" ? "Workbench" : x.actor === "diagnostic" ? "Local diagnostic" : x.actor
            let text = new Date(x.created_at).toLocaleString() + " • " + who + "\n" + (names[x.operation] || x.operation.split("_").join(" ")) + " — " + x.status
            if (activityDetails) text += "\nRequest: " + (x.request_id || "—") + (x.record_id ? " • Record: " + x.record_id : "") + (x.error !== "none" ? " • Error: " + x.error : "")
            return text
        }).join("\n\n")
    }
    function reviewText() {
        if (!selected) return "No proposal to approve.\n\nSubmit evidence and a named-check proposal from a configured assistant, or load the synthetic walkthrough."
        let result = ""
        if (selectedOutcome && selectedOutcome.verification && selectedOutcome.verification.assertions) {
            result = "RESULT: " + selectedOutcome.verification.status.toUpperCase() + " — synthetic fixture only\n"
            for (let assertion of selectedOutcome.verification.assertions)
                result += assertion.role + ": HTTP " + assertion.status + "; protected content " + (assertion.protected_content_present ? "present" : "absent") + "\n"
            result += "\n"
        }
        let text = result + selected.summary + "\n\nSubmitted by: " + selected.submitted_by + " (unverified proposal)"
        text += "\n\nCHECK TO RUN\n" + selected.check_id + "\n" + selected.scope
        text += "\n\nEXPECTED RESULT\n" + selected.expected_result
        text += "\n\nSUPPORTING EVIDENCE\n"
        for (let id of selected.evidence_ids) {
            let item = (records.evidence || []).find(x => x.id === id)
            text += item ? item.origin + "\nReceived: " + item.created_at + "\n" + item.content + "\n\n" : id + " (refresh to inspect)\n"
        }
        return text + "Approval applies once to this exact proposal and revision. The check runs a synthetic localhost HTTP server and sends two local requests. It does not access your repository or any external website."
    }
    function results(view) {
        const resultRecords = view.records || ({})
        let text = view.case ? "CASE: " + view.case.snapshot.title + " • " + view.case.case_id.slice(-8) + "\n\n" : ""
        text += "ASSISTANT PROPOSALS (unverified)\n"
        for (let item of resultRecords.proposal || []) text += "\n" + item.submitted_by + ": " + item.summary + "\n"
        text += "\nJEV ASSESSMENTS (not independent verification)\n"
        let assessments = (resultRecords.outcome || []).filter(x => x.response !== undefined)
        if (!assessments.length) text += "Not requested. No TypeSafe credits used by this walkthrough.\n"
        for (let item of assessments) text += JSON.stringify(item.response, null, 2) + "\n"
        text += "\nVERIFIED CHECKS\n"
        let checks = (resultRecords.outcome || []).filter(x => x.checks !== undefined || x.status === "interrupted")
        if (!checks.length) text += "Not performed.\n"
        for (let item of checks) {
            if (item.status === "interrupted") { text += "Interrupted. Verification not performed.\n"; continue }
            text += item.verification.status.toUpperCase() + " / " + item.verification.scope + "\n"
            for (let assertion of item.verification.assertions)
                text += "\n" + assertion.role + ": HTTP " + assertion.status + "; protected content " + (assertion.protected_content_present ? "present" : "absent") + "; " + (assertion.passed ? "PASSED" : "FAILED")
            text += "\n\nRun: " + item.run_id + "\n"
        }
        return text
    }
    contentItem: ColumnLayout {
        spacing: 12
        RowLayout {
            Repeater {
                model: ["Connections", "Evidence & state", "Review & run", "Activity"]
                BlockButton { required property string modelData; required property int index
                    colors: panel.colors; text: modelData; primary: pages.currentIndex === index
                    onClicked: { pages.currentIndex = index; if (index === 3) panel.send("activity") } }
            }
            Item { Layout.fillWidth: true }
            BlockButton { colors: panel.colors; text: "Refresh"; enabled: !workbench.busy; onClicked: panel.reviewingIncoming ? workbench.reviewIncoming(panel.shared.case_id, panel.incoming.proposal_id) : panel.send(pages.currentIndex === 3 ? "activity" : "status") }
            BlockButton { colors: panel.colors; text: "Close"; onClicked: panel.close() }
        }
        Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted
            text: panel.shared ? "Saved snapshot available to: " + (panel.shared.shared_with.join(", ") || "nobody") : "No test shared yet. Connect first, or start with the sample below." }
        Text { objectName: "sharingFeedback"; Accessible.name: text; Layout.fillWidth: true
            visible: text.length > 0; text: panel.reviewingIncoming ? "" : (panel.view.notice || ""); wrapMode: Text.Wrap
            color: panel.colors.ink; font.bold: true }
        StackLayout {
            id: pages; Layout.fillWidth: true; Layout.fillHeight: true
            ScrollView {
                id: setupScroll
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                contentWidth: availableWidth
                ScrollBar.vertical.policy: ScrollBar.AlwaysOn
                ColumnLayout {
                    width: setupScroll.availableWidth; spacing: 12
                    Text { text: "1. Let Workbench prepare Claude"; font.pixelSize: 22; font.bold: true; color: panel.colors.ink }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted
                        text: "This adds Jev tools to Claude Desktop. After your approval, Workbench saves the setup. When you restart Claude, Claude launches the local Jev connector. No browser address or API key is needed." }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink
                        text: !panel.view.integration ? "Looking for supported assistant settings…" : panel.profiles.length ? "Found " + panel.profiles.length + " Claude profile" + (panel.profiles.length > 1 ? "s. Choose the one you use." : ". Workbench can set up the connection for you.") : "No accessible Claude profile found. Open Claude once, then scan again. Automatic setup currently supports Windows." }
                    ThemeComboBox { id: profilePicker; objectName: "profilePicker"; colors: panel.colors; Layout.fillWidth: true
                        visible: panel.profiles.length > 1
                        model: ["Choose your Claude profile"].concat(panel.profiles.map(x => x.label + " — " + x.path)) }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted
                        text: panel.profile ? panel.profile.label + " • " + (panel.profile.available ? panel.profile.server_count + " existing connections" : panel.profile.problem) : ""; visible: text.length > 0 }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink
                        text: panel.profile && panel.profile.configured ? "Setup saved for this Workbench. Quit and reopen Claude when ready, then ask it: List my Jev Workbench cases." : "Setup requires your approval. Your other connections stay in place. No passwords or tokens are needed." }
                    RowLayout {
                        BlockButton { objectName: "reviewSetup"; colors: panel.colors; primary: true; text: "Review setup"
                            enabled: !workbench.busy && !!panel.profile && panel.profile.available && !panel.profile.configured
                            onClicked: panel.send("setup_review", {profile_id: panel.profile.id}) }
                        BlockButton { colors: panel.colors; text: "Scan again"; enabled: !workbench.busy; onClicked: panel.send("status") }
                        BlockButton { objectName: "checkConnection"; colors: panel.colors; text: "Check for Claude request"; enabled: !workbench.busy; onClicked: panel.send("connection_check") }
                    }
                    Rectangle { Layout.fillWidth: true; implicitHeight: planColumn.implicitHeight + 24; visible: !!panel.setupPlan && panel.setupPlan.state === "review"
                        color: panel.colors.background; border.color: panel.colors.border; border.width: 2
                        ColumnLayout { id: planColumn; anchors.fill: parent; anchors.margins: 12; spacing: 10
                            Text { text: "Review before setup"; font.bold: true; color: panel.colors.ink }
                            Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink; text: panel.setupPlan ? panel.setupPlan.summary : "" }
                            Text { Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; color: panel.colors.muted; text: panel.setupPlan ? panel.setupPlan.path : "" }
                            BlockButton { colors: panel.colors; text: "Cancel setup review"; enabled: !workbench.busy
                                onClicked: panel.send("setup_cancel", {plan_id: panel.setupPlan.id}) }
                            BlockButton { objectName: "approveSetup"; colors: panel.colors; primary: true; text: "Approve setup"; enabled: !workbench.busy
                                onClicked: panel.send("setup_apply", {plan_id: panel.setupPlan.id}) }
                        }
                    }
                    Text { text: "2. Restart Claude and send the test request"; font.pixelSize: 20; font.bold: true; color: panel.colors.ink }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted
                        text: "After setup is saved, quit Claude fully and reopen it. Start a new conversation, paste the test request below, and send it. Approve the Jev tool if Claude asks. An empty case list still proves the tool answered." }
                    RowLayout {
                        BlockButton { colors: panel.colors; text: "Copy test request for Claude"; enabled: !workbench.busy; onClicked: { workbench.copyConnectionPrompt(); copiedPrompt.visible = true } }
                        BlockButton { objectName: "testLocalConnector"; colors: panel.colors; text: "Test local connector"; enabled: !workbench.busy; onClicked: panel.send("diagnostics") }
                    }
                    Text { id: copiedPrompt; visible: false; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink; text: "Copied. Paste into a new Claude conversation and send it, then choose Check for Claude request here." }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted; text: "Test local connector checks this package only. Check for Claude request looks for a tool call made through the configured connection." }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink
                        text: panel.claudeActivity ? "Tool request received: " + panel.claudeActivity.tool + " at " + panel.claudeActivity.seen + ". This records local connection activity; account identity is not verified." : "Waiting for the first Claude tool request. Saved settings alone do not verify the connection." }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted
                        text: (panel.integration.warnings || []).join("\n"); visible: text.length > 0 }
                    Text { text: "3. Choose what to share"; font.pixelSize: 22; font.bold: true; color: panel.colors.ink }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted
                        text: !workbench.caseFolder ? "Start with a sample: Workbench saves it automatically. Or save your current test to share it." : panel.editorDirty ? "Save your current edits before sharing." : "Share the saved test with the assistants you choose. Free text is not automatically redacted." }
                    BlockButton { colors: panel.colors; text: "Start sample walkthrough"; enabled: !workbench.busy && !panel.editorDirty
                        onClicked: { workbench.previewFixture(); panel.review() } }
                    RowLayout {
                        CheckBox { id: claude; objectName: "shareClaude"; text: "Claude"; palette.windowText: panel.colors.ink }
                        CheckBox { id: chatgpt; text: "ChatGPT"; palette.windowText: panel.colors.ink }
                        CheckBox { id: codex; text: "Codex"; palette.windowText: panel.colors.ink }
                    }
                    RowLayout {
                        BlockButton { objectName: "shareSnapshot"; colors: panel.colors; text: "Share saved snapshot"; enabled: !workbench.busy && !panel.editorDirty && !!workbench.caseFolder && (claude.checked || chatgpt.checked || codex.checked)
                            onClicked: panel.send("share", {hosts: (claude.checked ? ["claude"] : []).concat(chatgpt.checked ? ["chatgpt"] : []).concat(codex.checked ? ["codex"] : [])}) }
                        BlockButton { colors: panel.colors; text: "Revoke access"; enabled: !workbench.busy && !!panel.shared; onClicked: panel.send("revoke") }
                    }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; text: panel.shared ? "Accessible to: " + (panel.shared.shared_with.join(", ") || "nobody") : "Accessible to: nobody"; color: panel.colors.ink }
                    Text { text: "4. Ask, review, run"; font.pixelSize: 22; font.bold: true; color: panel.colors.ink }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink
                        text: "In your connected assistant, ask: Read my shared Jev case and propose a guest-access check. Workbench will show the proposal automatically. Choose Review proposal in the Inbox. Approving a check runs it once; the result stays in history." }
                    Text { text: "ChatGPT"; font.bold: true; color: panel.colors.ink }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted
                        text: "ChatGPT needs account-side Developer mode and a private connection bridge. This preview does not automate that setup yet. Selecting ChatGPT above grants case access only; it does not create a connection." }
                    BlockButton { colors: panel.colors; text: panel.advanced ? "Hide advanced options" : "Advanced options"; onClicked: panel.advanced = !panel.advanced }
                    ColumnLayout { visible: panel.advanced; Layout.fillWidth: true; spacing: 10
                        Text { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Optional Jev assessment • separate TypeSafe credits. Default: off."; color: panel.colors.muted }
                        RowLayout {
                            ThemeComboBox { id: allowance; colors: panel.colors; model: ["0", "1", "2", "3"] }
                            BlockButton { colors: panel.colors; text: "Set additional call allowance"; enabled: !workbench.busy && !!panel.shared
                                onClicked: panel.send("budget", {limit: allowance.currentIndex}) }
                        }
                        Text { text: "Manual launch configuration"; font.bold: true; color: panel.colors.ink }
                        ThemeComboBox { id: hostPicker; colors: panel.colors; model: ["claude", "chatgpt", "codex"] }
                        TextArea { Layout.fillWidth: true; text: workbench.connectorCommand(hostPicker.currentText); readOnly: true; selectByMouse: true
                            color: panel.colors.ink; font.family: "Consolas"; font.pixelSize: 12; wrapMode: TextEdit.Wrap
                            background: Rectangle { color: panel.colors.background } }
                        BlockButton { colors: panel.colors; text: "Undo last Claude setup…"; visible: !!panel.setupPlan && panel.setupPlan.state === "applied"; enabled: !workbench.busy
                            onClicked: panel.undoReview = !panel.undoReview }
                        Text { visible: panel.undoReview; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink
                            text: "Restore Claude's exact settings from before this setup? Undo stops if the settings have changed since. Case sharing is unchanged." }
                        BlockButton { colors: panel.colors; text: "Approve restoring previous settings"; visible: panel.undoReview && !!panel.setupPlan && panel.setupPlan.state === "applied"; enabled: !workbench.busy
                            onClicked: { panel.send("setup_undo", {plan_id: panel.setupPlan.id}); panel.undoReview = false } }
                    }
                }
            }
            ColumnLayout {
                Text { text: "Incoming evidence stays separate"; font.pixelSize: 22; font.bold: true; color: panel.colors.ink }
                Text { text: "Assistant observations retain origin, timestamp and content hash. Proposed state enters your editor only when you accept it; save and share again to update the assistant snapshot."; wrapMode: Text.Wrap; Layout.fillWidth: true; color: panel.colors.muted }
                ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    TextArea { text: JSON.stringify({evidence: panel.records.evidence || [], pending_state: panel.records.state || []}, null, 2)
                        readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; color: panel.colors.ink; font.family: "Consolas"; font.pixelSize: 12
                        background: Rectangle { color: panel.colors.background } } }
                BlockButton { colors: panel.colors; text: "Accept latest state into editor"; enabled: !workbench.busy && !panel.editorDirty && !!panel.records.state && panel.records.state.length > 0
                    onClicked: panel.useState(panel.records.state[0].state) }
                Text { text: panel.editorDirty ? "Save current edits before accepting state." : "Assistant state is a proposal, not a verified fact."; color: panel.colors.muted }
            }
            ColumnLayout {
                RowLayout {
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink; font.bold: true
                        text: panel.shared ? "Reviewing: " + panel.shared.snapshot.title + " • " + panel.shared.case_id.slice(-8) : "No case selected for review" }
                    BlockButton { colors: panel.colors; text: "Open Inbox"; onClicked: panel.openInboxRequested() }
                }
                Text { visible: panel.reviewingIncoming; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted
                    text: "This review uses the proposal's saved case. Your editor and unsaved work stay in place." }
                Text { text: "Review the exact check before approving"; font.pixelSize: 22; font.bold: true; color: panel.colors.ink }
                Text { text: "This preview runs only the synthetic guest-access fixture. It cannot patch a repository, run arbitrary commands, or verify a real project."; color: panel.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                ThemeComboBox { id: proposalPicker; Layout.fillWidth: true; colors: panel.colors
                    model: panel.proposals.length ? panel.proposals.map(x => x.submitted_by + ": " + x.summary.substring(0, 90)) : ["No current proposal for this editor case. Open Inbox to find incoming proposals."] }
                ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    TextArea { text: panel.rawProposal && panel.selected ? JSON.stringify(panel.selected, null, 2) : panel.reviewText()
                        readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; color: panel.colors.ink; font.family: "Consolas"; font.pixelSize: 12
                        background: Rectangle { color: panel.colors.background } } }
                Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink; font.bold: true
                    text: panel.selectedOutcome ? "Check result: " + (panel.selectedOutcome.verification.status || panel.selectedOutcome.status) + " / synthetic fixture only" : "Verification: not performed" }
                RowLayout {
                    BlockButton { objectName: "approveProposal"; colors: panel.colors; primary: true; text: panel.alreadyApproved ? "Already approved" : "Approve and run check"
                        enabled: panel.approvalBlockReason.length === 0
                        onClicked: panel.send("approve", {case_id: panel.shared.case_id, revision: panel.shared.revision, proposal_id: panel.selected.id, proposal_hash: panel.selected.review_hash, incoming_review: panel.reviewingIncoming}) }
                    BlockButton { colors: panel.colors; text: "Stop"; enabled: workbench.busy; onClicked: workbench.cancel() }
                    BlockButton { colors: panel.colors; text: panel.rawProposal ? "Readable review" : "Raw proposal"; onClicked: panel.rawProposal = !panel.rawProposal }
                    BlockButton { colors: panel.colors; text: "Show workflow results"; onClicked: panel.showResults({case: panel.shared, records: panel.records}) }
                }
                Text { objectName: "approvalFeedback"; Accessible.name: text; text: panel.approvalBlockReason || "Ready for your approval. This check runs once for the exact proposal and revision shown."; color: panel.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
            }
            ColumnLayout {
                Text { text: "Activity and diagnostics"; font.pixelSize: 22; font.bold: true; color: panel.colors.ink }
                Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted; text: "Timestamped operations, approvals, records, errors and connection calls. Request IDs link desktop and worker steps. Contents and credentials are excluded from this timeline." }
                Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted; text: panel.view.activity ? panel.view.activity.retention : "Select Refresh to load recent activity." }
                ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    TextArea { objectName: "activityTimeline"; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; color: panel.colors.ink; font.family: "Consolas"; font.pixelSize: 12
                        text: panel.activityText()
                        background: Rectangle { color: panel.colors.background } }
                }
                Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink; text: panel.view.activity ? panel.view.activity.warnings.join("\n") : ""; visible: text.length > 0 }
                RowLayout {
                    BlockButton { colors: panel.colors; text: panel.activityDetails ? "Readable activity" : "Technical details"; onClicked: panel.activityDetails = !panel.activityDetails }
                    BlockButton { colors: panel.colors; text: "Refresh activity"; enabled: !workbench.busy; onClicked: panel.send("activity") }
                    BlockButton { colors: panel.colors; text: "Export diagnostic report"; enabled: !workbench.busy; onClicked: panel.send("activity_export") }
                    BlockButton { objectName: "runDiagnostics"; colors: panel.colors; text: "Test local connector"; enabled: !workbench.busy; onClicked: panel.send("diagnostics") }
                }
            }
        }
    }
}
