# Jev Workbench: desktop workflow review

Historical review from 19 September 2026. The later four-pane-first direction supersedes the Overview recommendation below. See [the current desktop guide](desktop.md) for implemented navigation and [result handoff](result-handoff.md) for subsequent connector verification. Earlier test counts describe that earlier build, not the latest package.

The central problem is that the prototype made the user act as its integration layer: find the right application folder, edit settings, save a case, share a revision, refresh, interpret a disabled button, and distinguish several kinds of results. Those responsibilities belong primarily to the software.

The recommended experience is **discover → review setup → approve → verify → choose evidence → review a check → see the result**. The interface should always explain the current state and the next useful action. Technical configuration belongs in troubleshooting.

## Implemented in the guided preview

- A task-first overview with **Connect an assistant**, **Try a sample**, and **Open a saved test**. The four existing editors remain under **Advanced editor**.
- A visible **Connect assistants** action, instead of a connection workflow hidden in the Actions menu.
- Automatic discovery of conventional Windows Claude profiles and Microsoft Store Claude profiles. Multiple profiles require a choice; inaccessible or malformed settings are identified instead of silently replaced.
- **Review setup → Approve setup**. The review identifies the file and describes the precise scope. The app adds or updates its own connection, preserving other settings and connections. It does not share a case as a side effect.
- Backup, rejection of changes made after review, a 15-minute approval expiry, cancellation, and explicit undo. Undo refuses to overwrite later edits. Completed setup can be recovered when the app exits between replacing the settings file and recording completion.
- Windows-native file operations to preserve the original file's access permissions during replacement. Backups stay beside the original settings, outside the repository.
- Successful MCP tool calls record connection activity. The interface distinguishes saved settings from observed tool activity and displays the last observation time. It does not claim to verify the provider account or current availability.
- **Try a sample** creates and saves the sample before opening its approval screen. There is no hidden “load the walkthrough first” prerequisite.
- Clear sharing and connection-check feedback. Previously approved proposals remain historical records; a new run needs a fresh proposal.
- Technical launch configuration and optional TypeSafe call allowances moved into advanced options. ChatGPT sharing explicitly does not imply ChatGPT setup is complete.

Automatic configuration is covered by temporary-profile tests. The Windows release checks also include a Claude-to-Workbench proposal, explicit approval, and result readback; see [result handoff](result-handoff.md).

## Prioritized findings

“Implemented” describes this local build. “Next” describes work still needed; it is not a claim that those capabilities exist.

| Priority | Problem and consequence | Change required | Status |
|---|---|---|---|
| P0 | Manual settings editing can target the wrong profile or replace existing connections. | Bounded profile discovery, explicit target selection, reviewed changes, backup and safe undo. | Implemented for Windows Claude. |
| P0 | Installation, configuration, account login and a working tool connection were conflated. | Separate statuses supported by evidence; never infer connection from a file. | Implemented for configuration and historical tool activity. Live health/authenticated identity remains separate work. |
| P1 | Startup exposes four technical editors before explaining the task. | Task-based overview; progressively disclose editors. | Implemented. |
| P1 | Sample and sharing prerequisites are hidden. | Save the sample automatically; explain what is shared and what comes next. | Implemented. |
| P1 | A completed approval looks like an unexplained disabled action. | Show consumed approval and results; keep history; make a fresh run explicit. | Existing fix retained and regression-tested. |
| P1 | ChatGPT requires several account/tunnel steps. | Guided account capability check, provider-owned authentication, managed private bridge, repair/reconnect flow. | Next. Current UI states the limitation. |
| P1 | “Pull data from programs” has no general collection/import workflow. | Source adapters for chosen files, project roots, app exports and supported APIs; preview evidence and approve its scope. | Next. Current input is saved cases and selected assistant evidence. |
| P1 | A crashed or abandoned run can block future runs globally. | Durable run ownership, heartbeat/lease, reconnect-or-mark-interrupted recovery, and a visible recovery action. Never label an abandoned run passed or retry a billed call automatically. | Next. Normal desktop cancellation exists; general crash recovery does not. |
| P1 | Portable, version-specific paths can break a connection after moving/upgrading the app. | Stable per-user launcher/runtime location, versioned packages, atomic activation and rollback, compatibility checks. | Next. The new preview is isolated; this is not an installer/update system. |
| P1 | App state is split across case folders, a workflow database, and independent client processes. | One displayed active workspace/profile identity, recent-case index and reconnect instructions that use that exact identity. | Next. Paths now derive from the running app for automatic setup. |
| P1 | Work can be lost or forgotten between sessions. | Autosaved local drafts, recent cases, restore-after-crash and clear dirty/saved/shared distinctions. | Next. Current explicit saves and discard protection remain. |
| P1 | Incoming proposals were hidden unless their case was open. | Desktop Inbox across all cases; two-second background polling, automatic notification, exact proposal review, preserved editor and visible outcomes. | Implemented and tested with a real MCP subprocess and two different cases. Stale/revoked entries retain explanations. |
| P2 | Incoming evidence and results still expose too much raw structure. | Readable evidence cards, source/time, reviewed excerpts, before/after state comparison, and a unified run timeline. | Partial. Check review is readable; evidence/state still needs redesign. |
| P2 | TypeSafe settings entered in the desktop do not automatically reach independently launched MCP workers. | Shared OS credential storage with explicit scope and clear allowance/cost controls. | Next. Default allowance remains zero; no secret is copied into Claude settings. |
| P2 | The interface offers integrations with unequal capabilities. | Adapter capability matrix and provider-specific action cards; unavailable actions explain why. | Partial. Claude automated; ChatGPT/Codex remain advanced/manual. |
| P2 | A single worker timeout and general errors cover unrelated operations. | Operation-specific deadlines, actionable diagnostics, bounded redacted support export, retry policy by operation. | Partial. Database errors now return a worker response; broader recovery remains. |
| P2 | Desktop resizing, keyboard use and high-DPI behavior need a wider matrix. | Verify setup at minimum supported size and 100/150/200% scaling, tab order, screen-reader names, focus restoration and scroll reachability. | Both themes checked; wider accessibility/DPI matrix remains. |
| P2 | macOS frozen-worker packaging does not yet provide the same MCP launch route. | A platform adapter and a supported frozen-worker MCP entry point, with signed manual-build validation. | Next. Automatic setup is explicitly Windows-only. |

P0 denotes a prerequisite for safe usable setup, not a claim of a remotely exploitable vulnerability.

## Target architecture

Keep the existing boundary: Qt owns the desktop experience; Python owns discovery, evidence, integration and execution. Add a small adapter contract instead of hard-coding each application's workflow throughout the UI:

1. **Discover:** return profile candidates, supported capabilities, accessibility and reasons. Read only documented configuration locations and user-selected roots. A directory is evidence of a profile, not proof the program is installed or signed in.
2. **Plan:** produce a plain-language, time-limited change description with preconditions. Keep other programs' secret values out of UI responses and logs.
3. **Apply:** require the desktop approval for that exact plan; preserve unrelated settings; create recovery material; verify the resulting configuration.
4. **Observe:** track transport startup and successful tool calls separately from account identity and case permissions. Historic activity must never look like a live green light.
5. **Repair/undo:** explain what changed and offer a scoped operation. Never automatically overwrite another program's later edits.

The Claude implementation establishes these functions, but the adapter registry and the remaining provider implementations are still to be built.

For file/project integration, first ask the user to choose a project or source. Detect manifests and available tools within that boundary. Show a proposed evidence list with sizes and reasons before import. Ignore credentials, hidden application state and large/generated directories by default. Imported text remains data, never execution instructions. Share a reviewed snapshot rather than silently following all future file changes.

## Delivery order and acceptance criteria

**1 — Connection foundation: implemented locally.** A Windows user with an existing Claude profile can review and approve setup without opening Explorer, a terminal or a JSON editor. Other settings survive. A changed configuration rejects an old approval. Merely saving settings never produces a “connected” claim. A sample requires no folder choice.

**2 — Reliable daily use.** Add stable installation, recent cases, draft restore and run recovery before adding more automation. Acceptance: moving to a new version preserves connections; forced termination cannot permanently block all cases; reopening restores the user's chosen workspace and offers their unsaved draft without silently sharing it.

**3 — Managed source import and ChatGPT connection.** Add bounded file/project adapters and a provider-approved private bridge. Acceptance: a user chooses the source and approves scope, sees evidence before sharing, and can revoke access. ChatGPT setup reports unsupported account capabilities and can repair a disconnected bridge without copying session tokens.

**4 — Unify review/results.** Add evidence cards, revision comparison and a run timeline. Acceptance: a user can explain what was proposed, approved, run and observed without reading raw JSON. Real-project execution requires its own registered check and scoped approval; the sample must never imply it tested the user's project.

Target usability measures: zero manual configuration-file edits on the supported Claude path; no terminal commands for the sample; no unexplained disabled primary actions; connection status always tied to an observation; setup success measured with first-time users, not inferred from automated tests. These are acceptance targets, not measured usability-study results.

## Validation and limitations

The implementation is tested with disposable profiles, including Microsoft Store paths, multiple profiles, malformed/duplicate-key/oversized settings, unchanged unrelated secrets, stale approvals, expiry, backup integrity, undo, cancellation and recovery. Native UI tests exercise setup review and approval, alongside existing sharing and execution checks. Both Light and Night Shift are inspected.

Final checks: 39 Python tests passed in the development environment and again with the packaged runtime initialized through the app's Windows bootstrap. Setup, sharing and approval UI checks passed in both themes; editor checks also passed in both themes. The native syntax-highlighting test passed. The guided preview was compiled and packaged locally; no release was published. These checks do not substitute for a real account round trip or a first-time-user usability study.

A real signed-in Claude or ChatGPT round trip has not been newly verified in this review. The app currently runs only the synthetic guest-access check. The remaining roadmap above is substantive work; this preview is the first implemented correction, not the completed desktop product.

External programs do not participate in Workbench's database transaction. Setup checks settings again immediately before replacement and preserves a backup, but an unrelated process writing at precisely the same moment remains a concurrency limitation. Rare Windows replacement failures may require recovery from the backup. Same-user processes can modify local state; this is not a sandbox against the Windows account owner.

## Evidence and references

Reviewed source includes `desktop/Main.qml`, `desktop/ConnectionPanel.qml`, `desktop/Workbench.cpp`, case storage, workflow storage/approvals/budget, MCP server and handlers, Windows/macOS packaging and the associated tests. The actual Microsoft Store profile location was verified by read-only inspection. The new implementation is in `src/jev_diagnostics/integrations/claude.py`.

- [MCP: connecting local servers](https://modelcontextprotocol.io/docs/develop/connect-local-servers) — local Claude configuration and restart behavior.
- [Claude: local MCP servers](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop) — supported client-owned setup and extensions.
- [OpenAI: Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) — private connection approach; account capabilities must be checked rather than assumed.
- [Microsoft: ReplaceFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew) and [CopyFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-copyfilew) — Windows replacement, backup and file-security behavior used by setup.
