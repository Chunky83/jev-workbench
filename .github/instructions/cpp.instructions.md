---
applyTo: "desktop/**/*.cpp,desktop/**/*.h"
---

# C++ and Qt conventions

- Keep C++ at the desktop boundary: expose clear Qt properties, signals, and invokable user actions; manage native dialogs, settings, processes, and application lifecycle; delegate workflow logic to Python.
- Do not duplicate Python validation, connector policy, Jev request construction, or workflow-state transitions in C++.
- Keep QML-facing contracts explicit and stable. When a property or invokable changes, update its notifications, callers, smoke coverage, and user-facing error behavior together.
- Bound child-process time and output, preserve cancellation behavior, and treat malformed or incomplete worker responses as failures. Never convert interruption or missing verification into success.
- Pass structured arguments and JSON through existing boundaries. Do not build commands from untrusted shell text.
- Change `CMakeLists.txt` only when sources, resources, Qt components, build settings, tests, or installation behavior actually change.
- Run the smallest relevant native check and the affected Python tests. UI and packaged smoke tests require normal desktop permissions; report whether they were run.
