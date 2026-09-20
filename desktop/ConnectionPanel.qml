import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Pane {
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
    property var selected: proposals.length && proposalPicker.currentIndex >= 0 ? (proposals[proposalPicker.currentIndex] || null) : null
    property var inboxItems: (JSON.parse(workbench.inboxView).proposals || [])
    property var inboxSelection: reviewingIncoming && selected ? inboxItems.find(x => x.proposal_id === selected.id) : null
    property bool alreadyApproved: !!selected && (records.approval || []).some(x => x.proposal_id === selected.id)
    property string approvalBlockReason: {
        if (workbench.busy) return "A task is running. Wait for it to finish or use Stop."
        if (alreadyApproved) return "This proposal was already approved. See Results. A new check needs a new proposal."
        if (editorDirty && !reviewingIncoming) return "Save your editor changes before reviewing a proposal. If the saved inputs changed, share them and request a new proposal."
        if (!shared) return "Share a saved case first, or choose New sample in the workspace."
        if (!selected) return "No current proposal for this case. Share it and ask the assistant to propose a check, or open Inbox."
        if (shared.shared_with.indexOf(selected.submitted_by) < 0) return "Access for this proposal's connection was revoked. Share the case and request a new proposal."
        if (reviewingIncoming && inboxSelection && inboxSelection.status === "revoked") return "Access was revoked after this review opened. Request a new proposal after sharing again."
        if (reviewingIncoming && inboxSelection && inboxSelection.revision !== shared.revision) return "This case changed while you were reviewing. Refresh this review to see its current state."
        if (selected.review_revision !== shared.revision) return "The case changed after this proposal. Request a new proposal for the current revision, or choose New sample in the workspace."
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
    visible: false
    focus: visible
    padding: 16
    readonly property bool opened: visible
    property bool otherAssistants: false
    signal dismissed()
    signal saveRequested()
    signal sampleRequested()
    background: Rectangle { color: panel.colors.surface; border.color: panel.colors.border; border.width: 2 }
    Keys.onEscapePressed: event => { close(); event.accepted = true }
    function open() { visible = true; forceActiveFocus(Qt.OtherFocusReason) }
    function close() { visible = false; dismissed() }
    function connections() { pages.currentIndex = 4; open() }
    function sharing() {
        workbench.clearIncomingReview()
        pages.currentIndex = 0
        const hosts = view.case ? view.case.shared_with.filter(x => x !== "preview") : []
        claude.checked = hosts.length ? hosts.indexOf("claude") >= 0 : true
        chatgpt.checked = hosts.indexOf("chatgpt") >= 0
        codex.checked = hosts.indexOf("codex") >= 0
        otherAssistants = chatgpt.checked || codex.checked
        open()
    }
    function activity() { pages.currentIndex = 3; open(); panel.send("activity") }
    function review() { pages.currentIndex = 2; open() }
    function showEvidence() { pages.currentIndex = 1; open(); panel.send("status") }
    function send(operation, data) { workbench.workflow(operation, JSON.stringify(data || {})) }
    function activityText() {
        if (!view.activity) return "Open Activity to load recorded operations."
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
        if (!selected) return "No proposal to approve.\n\nShare this case, copy the request, and send it to your assistant. Its proposal will appear automatically."
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
        const data = view.records || ({})
        const checks = (data.outcome || []).filter(x => x.checks !== undefined || x.status === "interrupted")
        const latest = checks.length ? checks[0] : null
        let text = latest ? (latest.status === "interrupted" ? "INTERRUPTED. Verification not performed." : latest.verification.status.toUpperCase() + " / " + latest.verification.scope) : "No verified check result yet."
        text += "\n\nCASE: " + (view.case ? view.case.snapshot.title + " · " + view.case.case_id.slice(-8) : "No case") + "\n"
        if (latest && latest.status !== "interrupted") {
            for (let assertion of latest.verification.assertions)
                text += "\n" + assertion.role + ": HTTP " + assertion.status + "; protected content " + (assertion.protected_content_present ? "present" : "absent") + "; " + (assertion.passed ? "PASSED" : "FAILED")
        }
        text += "\n\nAssistant proposals (unverified)\n"
        for (let item of data.proposal || []) text += "\n" + item.submitted_by + ": " + item.summary + "\n"
        const assessments = (data.outcome || []).filter(x => x.response !== undefined)
        text += "\nJev assessments (not independent verification)\n"
        if (!assessments.length) text += "No Jev response recorded.\n"
        for (let item of assessments) text += JSON.stringify(item.response, null, 2) + "\n"
        if (checks.length > 1) text += "\n" + checks.length + " check outcomes recorded. Inspect Raw JSON for earlier outcomes.\n"
        return text
    }
    contentItem: ColumnLayout {
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            ThemeComboBox {
                objectName: "taskPanelSection"; colors: panel.colors; Layout.fillWidth: true
                model: ["Share case", "Assistant evidence", "Review proposal", "Activity", "Assistant setup"]
                currentIndex: pages.currentIndex; Accessible.name: "Workspace panel"
                onActivated: { if (currentIndex === 0) panel.sharing(); else { pages.currentIndex = currentIndex; if (currentIndex === 3) panel.send("activity"); else if (currentIndex === 4) panel.send("status") } }
            }
            BlockButton { objectName: "closeTaskPanel"; colors: panel.colors; text: "Close"; implicitWidth: 68; onClicked: panel.close() }
        }
        Text {
            objectName: "sharingFeedback"; Accessible.name: text; Layout.fillWidth: true
            visible: text.length > 0; text: panel.reviewingIncoming ? "" : (panel.view.notice || "")
            textFormat: Text.PlainText; wrapMode: Text.Wrap; color: panel.colors.ink
        }
        StackLayout {
            id: pages; Layout.fillWidth: true; Layout.fillHeight: true
            ScrollView {
                id: sharingScroll; clip: true; contentWidth: availableWidth
                ColumnLayout {
                    width: sharingScroll.availableWidth; spacing: 14
                    Text { visible: !workbench.caseFolder; text: "Share the case in your editors"; textFormat: Text.PlainText; font.pixelSize: 20; font.bold: true; color: panel.colors.ink; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    Text { text: !workbench.caseFolder ? "Save this case first, or create a saved sample." : panel.editorDirty ? "Save your edits before sharing. Assistants can only read the saved copy." : "Choose which assistants may read the saved state, questions, instructions, and submitted evidence."; color: panel.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    BlockButton { colors: panel.colors; text: "Save current case"; visible: !workbench.caseFolder || panel.editorDirty; enabled: !workbench.busy; onClicked: panel.saveRequested() }
                    BlockButton { colors: panel.colors; text: "Create saved sample"; visible: !workbench.caseFolder; enabled: !workbench.busy; onClicked: panel.sampleRequested() }
                    BlockButton { objectName: "copyCaseRequest"; colors: panel.colors; primary: true; text: "Copy request for Claude"; visible: !!panel.view.case && panel.view.case.shared_with.indexOf("claude") >= 0; enabled: !workbench.busy && !panel.editorDirty; onClicked: workbench.copyProposalPrompt() }
                    Text { visible: !!panel.view.case && panel.view.case.shared_with.indexOf("claude") >= 0; text: "Paste the request into Claude and send it. Its proposal will appear in Inbox automatically. After approval, ask Claude to read the result."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted }
                    CheckBox { id: claude; objectName: "shareClaude"; text: "Claude"; palette.windowText: panel.colors.ink }
                    Text { Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted; text: panel.claudeActivity ? "Last Claude request: " + new Date(panel.claudeActivity.seen).toLocaleString() : "No Claude request recorded yet. Check Assistant setup if needed." }
                    BlockButton { colors: panel.colors; text: "Other assistants"; onClicked: panel.otherAssistants = !panel.otherAssistants }
                    ColumnLayout {
                        visible: panel.otherAssistants; Layout.fillWidth: true
                        CheckBox { id: chatgpt; text: "ChatGPT"; palette.windowText: panel.colors.ink }
                        CheckBox { id: codex; text: "Codex"; palette.windowText: panel.colors.ink }
                        Text { text: "These clients need separate manual setup. Sharing grants case access; it does not connect an account."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted }
                    }
                    BlockButton {
                        objectName: "shareSnapshot"; colors: panel.colors; primary: !panel.view.case || panel.view.case.shared_with.indexOf("claude") < 0; text: "Share saved case"
                        enabled: !workbench.busy && !panel.editorDirty && !!workbench.caseFolder && (claude.checked || chatgpt.checked || codex.checked)
                        onClicked: panel.send("share", {hosts: (claude.checked ? ["claude"] : []).concat(chatgpt.checked ? ["chatgpt"] : []).concat(codex.checked ? ["codex"] : [])})
                    }
                    Text { visible: !claude.checked && !chatgpt.checked && !codex.checked; text: "Choose an assistant before sharing."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted }
                    Text { text: "Shared with: " + (panel.view.case ? panel.view.case.shared_with.filter(x => x !== "preview").join(", ") || "no assistants" : "no assistants"); Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink }
                    BlockButton { colors: panel.colors; text: "Review current proposal"; visible: panel.proposals.length > 0; enabled: !workbench.busy; onClicked: { workbench.clearIncomingReview(); panel.review() } }
                    BlockButton { colors: panel.colors; text: "Revoke case access"; visible: !!panel.view.case && panel.view.case.shared_with.length > 0; enabled: !workbench.busy; onClicked: panel.send("revoke") }
                    BlockButton { colors: panel.colors; text: panel.advanced ? "Hide Jev allowance" : "Optional Jev allowance"; onClicked: panel.advanced = !panel.advanced }
                    ColumnLayout { visible: panel.advanced; Layout.fillWidth: true
                        Text { text: "Jev assessments use separate TypeSafe credits. Default: off. The connector needs its own credential access."; color: panel.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        RowLayout {
                            ThemeComboBox { id: allowance; colors: panel.colors; model: ["0", "1", "2", "3"] }
                            BlockButton { colors: panel.colors; text: "Set extra calls"; enabled: !workbench.busy && !!panel.view.case; onClicked: panel.send("budget", {limit: allowance.currentIndex}) }
                        }
                    }
                }
            }
            ColumnLayout {
                Text { text: "Evidence from assistants"; font.pixelSize: 20; font.bold: true; color: panel.colors.ink; Layout.fillWidth: true; wrapMode: Text.Wrap }
                Text { text: "Incoming observations and suggested state stay separate from your edits until you accept them."; color: panel.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    TextArea { text: JSON.stringify({evidence: panel.records.evidence || [], pending_state: panel.records.state || []}, null, 2); readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; color: panel.colors.ink; font.family: "Consolas"; font.pixelSize: 13; background: Rectangle { color: panel.colors.background } }
                }
                BlockButton { colors: panel.colors; text: "Accept latest state"; enabled: !workbench.busy && !panel.editorDirty && !!panel.records.state && panel.records.state.length > 0; onClicked: panel.useState(panel.records.state[0].state) }
                Text { text: panel.editorDirty ? "Save your edits before accepting state." : "Accepted state is still unverified. Save and share it to update the assistant's copy."; color: panel.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
            }
            ColumnLayout {
                ScrollView {
                    id: reviewScroll; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
                    ColumnLayout {
                        width: reviewScroll.availableWidth; spacing: 12
                        Text { objectName: "reviewCaseTitle"; text: panel.shared ? panel.shared.snapshot.title + " · " + panel.shared.case_id.slice(-8) : "No shared case selected"; textFormat: Text.PlainText; color: panel.colors.ink; font.bold: true; font.pixelSize: 19; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        Text { visible: panel.reviewingIncoming; text: "Reviewing the proposal's saved case. Your editor stays unchanged."; color: panel.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        ThemeComboBox { id: proposalPicker; Layout.fillWidth: true; colors: panel.colors; model: panel.proposals.length ? panel.proposals.map(x => x.submitted_by + ": " + x.summary.substring(0, 70)) : ["No current proposal"] }
                        TextArea { objectName: "proposalReviewText"; Layout.fillWidth: true; text: panel.rawProposal && panel.selected ? JSON.stringify(panel.selected, null, 2) : panel.reviewText(); readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; color: panel.colors.ink; font.family: panel.rawProposal ? "Consolas" : "Segoe UI"; font.pixelSize: 14; background: Rectangle { color: panel.colors.background } }
                        Text { text: panel.selectedOutcome ? "Result: " + (panel.selectedOutcome.verification.status || panel.selectedOutcome.status) : "Not run. Waiting for approval."; color: panel.colors.ink; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        RowLayout {
                            BlockButton { colors: panel.colors; text: panel.rawProposal ? "Readable review" : "Raw details"; onClicked: panel.rawProposal = !panel.rawProposal }
                            BlockButton { colors: panel.colors; text: "Show results"; onClicked: panel.showResults({case: panel.shared, records: panel.records}) }
                        }
                        RowLayout {
                            BlockButton { colors: panel.colors; text: "Open Inbox"; onClicked: panel.openInboxRequested() }
                            BlockButton { colors: panel.colors; text: "Reload review"; enabled: !workbench.busy; onClicked: panel.reviewingIncoming ? workbench.reviewIncoming(panel.shared.case_id, panel.incoming.proposal_id) : panel.send("status") }
                        }
                    }
                }
                RowLayout {
                    BlockButton { objectName: "approveProposal"; colors: panel.colors; primary: true; text: panel.alreadyApproved ? "Already approved" : "Approve and run check"; enabled: panel.approvalBlockReason.length === 0; onClicked: panel.send("approve", {case_id: panel.shared.case_id, revision: panel.shared.revision, proposal_id: panel.selected.id, proposal_hash: panel.selected.review_hash, incoming_review: panel.reviewingIncoming}) }
                    BlockButton { colors: panel.colors; text: "Stop"; visible: workbench.busy; onClicked: workbench.cancel() }
                }
                Text { objectName: "approvalFeedback"; Accessible.name: text; text: panel.approvalBlockReason || "This approval runs the exact check above once."; color: panel.colors.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
            }
            ColumnLayout {
                Text { text: "Recorded activity"; font.pixelSize: 20; font.bold: true; color: panel.colors.ink }
                Text { text: "Operations, approvals, errors, and tool calls. Evidence contents and credentials are excluded."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted }
                ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    TextArea { objectName: "activityTimeline"; text: panel.activityText(); readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; color: panel.colors.ink; font.family: panel.activityDetails ? "Consolas" : "Segoe UI"; font.pixelSize: 13; background: Rectangle { color: panel.colors.background } }
                }
                Text { text: panel.view.activity ? panel.view.activity.warnings.join("\n") : ""; visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink }
                RowLayout {
                    BlockButton { colors: panel.colors; text: panel.activityDetails ? "Readable activity" : "Technical details"; onClicked: panel.activityDetails = !panel.activityDetails }
                    BlockButton { colors: panel.colors; text: "Refresh activity"; enabled: !workbench.busy; onClicked: panel.send("activity") }
                }
                BlockButton { colors: panel.colors; text: "Export diagnostics"; enabled: !workbench.busy; onClicked: panel.send("activity_export") }
                BlockButton { objectName: "runDiagnostics"; colors: panel.colors; text: "Test local connector"; enabled: !workbench.busy; onClicked: panel.send("diagnostics") }
            }
            ScrollView {
                id: setupScroll; clip: true; contentWidth: availableWidth
                ColumnLayout {
                    width: setupScroll.availableWidth; spacing: 14
                    Text { text: "Claude Desktop"; font.pixelSize: 20; font.bold: true; color: panel.colors.ink }
                    Text { text: panel.claudeActivity ? "A Claude tool request was received at " + new Date(panel.claudeActivity.seen).toLocaleString() + ". This is recorded activity, not a live account check." : panel.profile && panel.profile.configured ? "Setup is saved. Send a test request in Claude to check the connection." : "Workbench finds Claude settings and prepares a change for your approval."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted }
                    ThemeComboBox { id: profilePicker; objectName: "profilePicker"; colors: panel.colors; Layout.fillWidth: true; visible: panel.profiles.length > 1; model: ["Choose a Claude profile"].concat(panel.profiles.map(x => x.label)); Accessible.name: "Claude profile" }
                    Text { visible: !panel.profile || panel.profiles.length > 1; text: panel.profile ? panel.profile.label : panel.profiles.length ? "Choose which profile to configure." : "No supported Claude profile found. Open Claude once, then check again."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink }
                    BlockButton { objectName: "reviewSetup"; colors: panel.colors; primary: !!panel.profile && !panel.profile.configured; text: panel.profile && panel.profile.configured ? "Review setup again" : "Review Claude setup"; enabled: !workbench.busy && !!panel.profile && panel.profile.available; onClicked: panel.send("setup_review", {profile_id: panel.profile.id}) }
                    ColumnLayout {
                        visible: !!panel.setupPlan && panel.setupPlan.state === "review"; Layout.fillWidth: true; spacing: 10
                        Text { text: "Change to approve"; color: panel.colors.ink; font.bold: true }
                        Text { text: panel.setupPlan ? panel.setupPlan.summary : ""; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink }
                        Text { text: panel.setupPlan ? panel.setupPlan.path : ""; textFormat: Text.PlainText; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; color: panel.colors.muted }
                        BlockButton { objectName: "approveSetup"; colors: panel.colors; primary: true; text: "Approve setup"; enabled: !workbench.busy; onClicked: panel.send("setup_apply", {plan_id: panel.setupPlan.id}) }
                        BlockButton { colors: panel.colors; text: "Cancel setup review"; enabled: !workbench.busy; onClicked: panel.send("setup_cancel", {plan_id: panel.setupPlan.id}) }
                    }
                    Text { text: "After saving setup, fully quit and reopen Claude. Copy the test request into a new conversation and send it."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted }
                    BlockButton { colors: panel.colors; primary: !!panel.profile && panel.profile.configured && !panel.claudeActivity; text: "Copy connection test"; enabled: !workbench.busy; onClicked: workbench.copyConnectionPrompt() }
                    BlockButton { objectName: "checkClaudeRequest"; colors: panel.colors; text: "Check for Claude request"; enabled: !workbench.busy; onClicked: panel.send("connection_check") }
                    Text { text: (panel.integration.warnings || []).join("\n"); visible: text.length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted }
                    BlockButton { colors: panel.colors; text: "Share a case"; enabled: !workbench.busy; onClicked: panel.sharing() }
                    BlockButton { colors: panel.colors; text: panel.advanced ? "Hide technical setup" : "Technical setup and undo"; onClicked: panel.advanced = !panel.advanced }
                    ColumnLayout { visible: panel.advanced; Layout.fillWidth: true; spacing: 10
                        Text { text: "ChatGPT and Codex need manual client setup. Selecting a host below only displays its launch configuration."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.muted }
                        ThemeComboBox { id: hostPicker; colors: panel.colors; model: ["claude", "chatgpt", "codex"] }
                        TextArea { text: workbench.connectorCommand(hostPicker.currentText); Layout.fillWidth: true; readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; color: panel.colors.ink; font.family: "Consolas"; font.pixelSize: 12; background: Rectangle { color: panel.colors.background } }
                        BlockButton { colors: panel.colors; text: "Review undo"; visible: !!panel.setupPlan && panel.setupPlan.state === "applied"; enabled: !workbench.busy; onClicked: panel.undoReview = !panel.undoReview }
                        Text { visible: panel.undoReview; text: "Restore settings from before this setup? Undo stops if Claude settings have changed. Sharing stays unchanged."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: panel.colors.ink }
                        BlockButton { colors: panel.colors; text: "Restore previous settings"; visible: panel.undoReview && !!panel.setupPlan && panel.setupPlan.state === "applied"; enabled: !workbench.busy; onClicked: { panel.send("setup_undo", {plan_id: panel.setupPlan.id}); panel.undoReview = false } }
                    }
                }
            }
        }
    }
}
