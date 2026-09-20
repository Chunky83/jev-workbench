# Approved results across desktop and assistants

Desktop approval publishes the completed case and workflow records to the
main Results pane. The review dialog remains open so the reviewer can inspect
its outcome. Summary and Raw JSON share that same case; other editor contents,
including unsaved edits, remain unchanged. Collected local-run evidence is
cleared when the displayed result switches to an assistant workflow.

MCP `read_case` includes up to 20 recent runs, newest first, with `run_id`,
`proposal_id`, revision, timestamp, current status, and verification. After
desktop approval, an assistant reads the case again, matches its proposal,
and calls `read_run`. It does not need the user to relay a run ID.

MCP `read_run` keeps the existing immutable `run` and `outcome` fields and
adds `current`. The run-start record can say `running` after completion;
`current` derives its status from the stored outcome. Without an outcome it
is `incomplete`, with verification `Not performed`. This does not mutate
historical records, the case revision, or the evaluation allowance.

All reads retain the existing case-sharing check. These additions are
backward compatible and add no approval or execution tool. Existing MCP
processes load the new implementation on their next restart/reconnection.
Workbench notifications do not wake an idle assistant conversation.

Validation: full Python suite in development and embedded runtimes; official
MCP SDK submit, desktop approve, discover, and read-back; native inbox smoke
in Light and Dark verifying result identity, automatic display, one-time
approval, and preservation of another case's unsaved editor.

During the September 19 Windows walkthrough, actual Claude Desktop submitted
a proposal, Workbench automatically displayed it, desktop approval ran the
fixture, and Claude read the stored successful outcome. Both fixture
assertions passed. No paid Jev evaluation or real-project check was run.

When running CTest from a shell, put the project-local Qt bin directory on
PATH and set QT_PLUGIN_PATH to its plugins directory. For headless desktop
checks set QT_QPA_PLATFORM=offscreen and provide the same plugin directory.
