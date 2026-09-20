# Desktop guide

## Open the Windows application

Use the **Open Jev Workbench** shortcut for the current 0.1.0 package. See [the workspace map](../WORKSPACE.md). Keep its surrounding folders and DLLs together. The package includes Python, Qt, and the Visual C++ runtime; no separate Python installation is needed. This is a Windows x64 development package. For macOS, see [the release guide](releases.md).

State, Primitives, and raw Results highlight JSON keys, strings, numbers, and literals. Instructions highlights Markdown headings, bold text, inline code, and fenced code. Result summaries distinguish status labels and passed/failed words. Colors adapt to both themes. Highlighting does not rewrite your text or validate its meaning; Preview and Run still perform input validation.

## First five minutes

The app opens directly to State, Primitives, Instructions, and Results. The top
bar shows the case name, save status, sharing state, and assistant setup/activity.
An observed Claude request is historical activity, not a live account-login check.

1. Press **Run sample checks** for the guest-access fixture. No account or API key
   is needed. Results shows what was observed; this does not test a real project.
2. Use **Sample > Open existing sample** for a saved example with a proposed check to review. The
   review appears beside the editors. Inspect its scope and approve it once.
3. Use **Share case** to choose assistant access. Save current edits before
   sharing. After sharing with Claude, **Copy request for Claude** copies the
   exact case ID so identically named samples cannot be confused.
4. Paste and send the request in Claude. Incoming proposals appear in **Inbox**
   automatically. **Review proposal** opens the exact saved case beside the
   editors, preserving unsaved work in another case. Approval publishes the result
   in Results. Ask Claude to read the result after approval; an idle conversation
   does not resume by itself.
5. **Cases** lists saved work by name, date, sharing, and last result. **Open from folder** imports an existing saved case; **Save case** saves your edits. **Add question** inserts a
   Choice, Score, or Noul template. Replace its wording with a specific question.

For initial connection setup, use the Claude setup/activity button at the top.
Review and approve the proposed settings change, fully restart Claude, then
copy/send the connection test. Select **Check for Claude request** to inspect
recorded activity. Setup and sharing are separate approvals.

**Actions** retains Save as, evidence import, diagnostics, and API settings.
The side panel's selector switches between sharing, assistant evidence, review,
activity, and setup. Close or Escape returns focus to the workspace.

For a Jev assessment, set a session key in **Actions > API settings**, choose
**Jev assessment**, select its model, and inspect **Preview request** before
**Ask Jev**. This uses TypeSafe credits. The current workflow validation uses
synthetic local checks and does not exercise paid evaluations.

Drag the pane dividers or use Expand/Restore. Light and Night Shift are equally
supported. Ctrl+S saves, Ctrl+O opens, and Ctrl+Enter runs the selected mode.
Summary and Raw JSON display the same result. **History** shows the selected case's assistant evidence, proposals, approvals,
sample checks, and Jev assessments. **Show record** displays its saved detail in
Results; **Review proposal** opens that exact proposal for review. Reading history
never executes a check and leaves unsaved editors intact. The panel updates while
open. Dates and the short reference distinguish same-named cases.

**Sample > Open existing sample** reuses the latest available sample, creating one
only when none exists. **Sample > Create new sample** makes a separate case.
**Cases > Archive** asks for confirmation, revokes assistant access, and removes the
case from Active. Files and records are retained. Choose Archived and Restore to
bring it back privately; sharing must be approved again. Incomplete runs must be
resolved before archiving. An archive never discards the current editor draft.

New desktop runs record their case identity and actual input hash, including runs
against unsaved edits. Older runs without an identity stay under **Runs without a
case link**. They are never assigned by matching names. New unshared saved cases
are private; reopening or saving a shared case does not publish its new contents.

Case metadata lives in an additive desktop-only table in the existing workflow
database. Existing case files and immutable records are unchanged. Older versions
can ignore the new table and optional run fields. Workflow history is bounded to
100 records per kind and the latest 1,000 desktop run files, with a 300-event/2 MB
view limit. Unreadable or omitted records are reported and retained on disk.

The Jev model defaults to `jev-latest`. The catalog also includes `jev-1.13.0`
and `jev-preview`; opening a saved case preserves its chosen model even if absent
from the catalog. The model control appears when Jev assessment is selected.

## What runs

Local checks run the built-in guest-access fixture, regardless of the editable evidence. The bottom taskbar labels this clearly. Choose one, two, or three passes; the loop stops on an assertion failure. This is an executable learning example, not a security assessment of an external website.

Live Jev sends one request with your editable evidence. It does not run local checks first or modify your evidence. No automatic retries or model-selected commands execute. Jev answers are hypotheses; confidence is not verified accuracy. Live requests have not been exercised during this build; response handling is tested with synthetic responses.

Website collectors, existing repository test suites, vision processing, and automatic escalation to a coding model are future integrations. This version provides the desktop, file, worker, and bounded-loop foundation for them. There is no generic shell terminal or arbitrary script execution field.

## Files you can edit

```text
my-test/
  test.json                    Current revision, name, model, format version
  revisions/<revision-id>/
    state.json                 Evidence
    primitives.json            Questions, types, and criteria
    instructions.md            Common plain-language instructions
    runner.json                Named local check and 1-3 pass limit
```

Saving writes a fresh revision, then replaces `test.json` atomically. If a save fails, the previous revision remains loadable. Edit the files in the revision named in `test.json`, then reopen to reload external changes. The GUI does not watch external edits. Avoid editing the same case in multiple application instances.

Runs are stored in the Windows local application-data directory under `JevWorkbench/Jev Workbench/runs`. Every run records its state, questions, instructions, runner, exact request, and result. Files are not overwritten by later runs. Cancelled or forcibly interrupted runs can retain a `running` record without a completion result. Stop terminates the worker; a request already received by TypeSafe may still be billed.

Keep customer data, credentials, cookies, and authorization headers out of State. Saved evidence is local plaintext and is not automatically redacted. The API settings key is never included in cases or run records.

## Code map

```text
desktop/
  Main.qml                     Four panes and taskbar
  EditorPane.qml               Shared light/dark editor
  BlockButton.qml              Shared neubrutalist button
  Workbench.cpp                Desktop actions and Python process boundary
  main.cpp                     C++ application entry
src/jev_diagnostics/
  worker.py                    One JSON message in, one response out
  case_store.py                Separate files and transactional revisions
  workbench_request.py         Choice, Score, Noul validation
  local_checks.py              Synthetic HTTP test
  api_key.py                   Environment key loading
  typesafe_client.py           TypeSafe HTTP request
```

`prompts/collect_evidence.md` is the readable evidence-collection prompt. `examples/demo_timeout.json` is entirely fictional and uses the original CLI evidence format, not a desktop test manifest.

## Build and verify

On this Windows workstation, Qt and the Python build utilities live in this project's `.qt` and `.build-tools` folders. Run `powershell -File scripts/build-windows.ps1` from the project to configure and build with those local tools. The packaging script also defaults to these locations and `build/python-embed.zip`; no legacy external folder is required. The separate 0.1.0 preview package is not overwritten by this build command.

Requirements: CMake 3.24+, Qt 6.8+ with Quick, Quick Controls and Widgets, and a C++17 compiler. The local Windows build uses Visual Studio 2022 Build Tools and Qt 6.8.3. Dependencies are isolated in ignored `.build-tools` and `.qt` directories.

```powershell
.\.build-tools\Scripts\cmake.exe -S . -B build -G "Visual Studio 17 2022" -A x64 -DCMAKE_PREFIX_PATH="$PWD/.qt/6.8.3/msvc2022_64"
.\.build-tools\Scripts\cmake.exe --build build --config Release --parallel 4
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
.\scripts\package-windows.ps1
```

`scripts/package-windows.ps1` deploys the executable, Qt, Python modules, and a downloaded official embeddable Python ZIP at `build/python-embed.zip`. This build uses Python 3.13.15 from python.org. The package's Python search path explicitly contains `../worker`; user-installed Python packages are not required.

The executable supports `--case-library-ui-smoke` for sample reuse, duplicate case selection, mixed history, draft-preserving cancellation, archive and restore; `--compact` also exercises the minimum window. It supports `--smoke-test` for the bundled save/open/local-run path and `--ui-smoke --theme Light` (or Dark) for editing and running through QML. `--capture <absolute-png-path>` saves the application's own window. Tests must run with normal desktop permissions; the restricted agent sandbox cannot reliably initialize native Qt processes.

The source is portable in structure, but only Windows packaging and execution have been verified. See THIRD_PARTY_NOTICES.md before preparing a distributable release.
