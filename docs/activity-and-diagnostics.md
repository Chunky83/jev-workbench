# Activity logging and Claude connection walkthrough

## What changed

The updated preview has an **Activity and diagnostics** screen. It records meaningful desktop and worker operations, setup actions, sharing/revocation, allowance changes, evidence/proposal/approval/run/outcome creation, connector sessions, and individual successful or failed tool calls—including calls rejected during argument validation. Request IDs link the desktop operation to its worker and records.

The default timeline uses readable action names and local times. **Technical details** exposes request and record IDs. **Export diagnostic report** saves a local metadata-only JSON report and opens its containing folder. It does not upload anything.

Logs deliberately exclude evidence bodies, prompts, arbitrary exception messages, credentials, other applications' configuration contents and backups. Existing saved cases and run records still contain the inputs the user explicitly saved; those are separate from diagnostic exports.

Worker events retain at most 30 days and 10,000 entries. Desktop lifecycle/error logs rotate at approximately 1 MB across five files; the timeline filters out events older than 30 days. Case/run records and configuration backups have separate retention. Logging starts with this build; it cannot reconstruct earlier unrecorded actions. A sudden process termination may leave a start event without a completion event. This is a bounded local diagnostic history, not a tamper-proof security audit or a keystroke recorder.

## What the connection actually does

1. **Workbench prepares settings.** It detects your Claude profile and prepares an entry named `jev-workbench` with the bundled connector's launch command.
2. **You approve setup.** Workbench saves that entry while preserving other settings and creating a backup. No case is shared by this action.
3. **Claude starts the connector.** After you fully quit and reopen Claude Desktop, Claude reads those settings and starts the local connector process.
4. **A Claude tool request confirms use.** In Claude, send the test request copied from Workbench. Claude invokes the Jev tool; Workbench records that call. An empty case list is a valid response when nothing is shared yet.
5. **Share a case separately.** Return to Workbench, create the sample or save a test, select Claude and share the saved snapshot. Then ask Claude to read that case and propose a check.

Sharing is an access decision. It does not install or configure the connection. A passed local diagnostic verifies the connector package; it is not proof that Claude read the settings or invoked a tool.

## Current connection and next step

Claude is connected. Its real list/read requests and its submitted proposal have been confirmed. The original missing-settings finding described the earlier setup state and is resolved.

The proposal was invisible because the old review page only loaded the editor's selected case and had no listener. The fixed version has an automatic Inbox across all shared cases. Open **Open Jev Workbench.lnk**, then choose **Review proposal** in the popup. Read [Claude-proposal-and-Inbox.md](Claude-proposal-and-Inbox.md) for the current workflow and findings. Do not repeat setup or resubmit the waiting proposal.

## Validation results

- Final development and packaged-runtime tests: 66 passed in each environment.
- Packaged UI walkthrough: local diagnostic → sample creation → approval → passed synthetic result → matching activity records, in Light and Night Shift.
- Setup review/apply against disposable profiles, sharing flow, and editor regression checks passed in both themes.
- Native syntax-highlighting check passed.
- Actual Claude profile discovery and review were verified without changing its settings.
- Final read-only diagnostic against the real preview database and reviewed launch command: runtime, database integrity, log storage, MCP handshake, seven tools and read-only request all passed. The result is saved in `local-diagnostics-result.json`. Claude setup remained absent; no signed-in round trip is claimed.

Subsequent verification: the user supplied the Claude conversation showing a successful `list_cases` response with five shared synthetic cases and a successful read of the first case. This confirms the live Claude-to-Workbench read connection from the supplied transcript. It does not verify an assistant-submitted proposal, a Jev evaluation, or a real-project check. The earlier local inspection was limited by an app-approval timeout and a stale database view; that visibility discrepancy remains unresolved. No evaluation or change was reported by Claude.

Two follow-up usability defects remain: repeated walkthroughs created five cases with the same title, and the local diagnostic view did not expose the activity observed in Claude. These should be fixed without deleting the user's case history or marking diagnostic requests as Claude calls. The next workflow test is one proposal for `case-32d1b7162a454f0a82252757a664adce`, using its current revision and existing evidence, followed by desktop review and approval.

The existing app instance was left running; the updated preview is packaged separately. The familiar preview shortcuts now point to the updated build. Save any unsaved work before leaving the older instance.
