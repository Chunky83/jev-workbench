---
name: cpp-qml-boundary
description: Design or review changes that cross the Jev Workbench QML-to-C++ boundary, including Qt properties, signals, invokables, process lifecycle, and structured worker messages. Use when desktop behavior spans QML and C++; not for Python-only workflow changes.
---

# C++/QML Boundary

Keep QML declarative and user-facing, C++ responsible for the Qt/native boundary, and Python responsible for workflow and domain behavior.

When asked for a review, inspect and report without modifying files. When implementation is requested, keep the change within the established ownership boundary.

## Workflow

1. Trace the complete interaction from the QML control through a `Workbench` property or invokable, into any worker request, and back through signals or properties to the rendered state.
2. Assign each decision to one owner. QML may compose views and simple display transformations. C++ may manage Qt state, native UI, processes, cancellation, timeouts, and transport. Python must own domain validation, connector policy, Jev requests, execution rules, and reporting.
3. Keep boundary messages structured. Validate parse failures, missing fields, non-zero exits, timeouts, cancellation, and output limits without treating any of them as success.
4. Preserve stable QML-facing names where practical. If a contract changes, update declarations, emissions, QML callers, tests, and relevant documentation together.
5. Do not add a second implementation path for behavior already provided by `jev_diagnostics.worker` or workflow services.
6. Change CMake only if the set of compiled sources, resources, Qt dependencies, tests, or install outputs changes.

## Verification

Run focused Python tests for worker behavior and the smallest relevant native or UI smoke check for the QML/C++ contract. For a visual change, check both Light and Dark. State explicitly when native checks could not run because desktop permissions or Qt tooling were unavailable.

## Output format

- User interaction and data-flow trace
- Ownership decision for QML, C++, and Python responsibilities
- QML-facing contract changes
- Failure, cancellation, and recovery paths
- Files affected and why
- Verification performed and remaining gaps
