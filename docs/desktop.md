# Desktop guide

## Open the Windows application

Use the **Open Jev Workbench** shortcut for the current 0.1.0 package. See [the workspace map](../WORKSPACE.md). Keep its surrounding folders and DLLs together. The package includes Python, Qt, and the Visual C++ runtime; no separate Python installation is needed. This is a Windows x64 development package. For macOS, see [the release guide](releases.md).

State, Primitives, and raw Results highlight JSON keys, strings, numbers, and literals. Instructions highlights Markdown headings, bold text, inline code, and fenced code. Result summaries distinguish status labels and passed/failed words. Colors adapt to both themes. Highlighting does not rewrite your text or validate its meaning; Preview and Run still perform input validation.

## First five minutes

1. Leave the mode at **Local checks** and press **Run test**. Python starts a synthetic local HTTP fixture and verifies guest denial, absence of private content, and owner access. No website is contacted and no API credits are used.
2. Press **Use collected evidence in State**. The actual observations become editable JSON in the upper-left pane.
3. Edit the question and its possible answers in **Primitives**. **+ Question** inserts a Choice, Score, or Noul template. Replace the template wording with your own specific question.
4. Edit the common directions in **Instructions**. These directions are added to each question independently.
5. Use **Actions > Save as**. Create or select a folder for this experiment. To reopen it, use **Actions > Open test** and choose its `test.json`.
6. Press **Preview request** to inspect the exact request without sending it.
7. For a real evaluation, enter your key in **Actions > API settings**, switch to **Live Jev**, and press **Run test**. This sends your current State and questions to TypeSafe and uses API credits. The key is held only for the session. An inherited `TYPESAFE_API_KEY` also works.

Use the top-right selector for Light, Dark, or System. Drag the dividers or use each pane's Expand button. Escape restores the four-pane view. Ctrl+S saves, Ctrl+O opens, and Ctrl+Enter runs. Results can be read as a summary or raw JSON. History lists saved runs and displays the latest two for comparison.

The Model dropdown defaults to `jev-latest` for new tests. It also offers the published pinned version `jev-1.13.0` and the `jev-preview` alias. The catalog comes from https://docs.typesafe.ai/models (checked September 19, 2026); it is not fetched automatically. Opening a saved test preserves its model, including version names absent from the built-in catalog.

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

The executable supports `--smoke-test` for the bundled save/open/local-run path and `--ui-smoke --theme Light` (or Dark) for editing and running through QML. `--capture <absolute-png-path>` saves the application's own window. Tests must run with normal desktop permissions; the restricted agent sandbox cannot reliably initialize native Qt processes.

The source is portable in structure, but only Windows packaging and execution have been verified. See THIRD_PARTY_NOTICES.md before preparing a distributable release.
