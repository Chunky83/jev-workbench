# Current workspace — Jev Workbench 0.1.0

This repository contains the current source and the four-world kit. Use one
current desktop package; saved cases and connection settings live outside
the repository and remain in place when source or Git history changes.

| Folder | Purpose |
|---|---|
| `desktop/` | Desktop interface and application icon |
| `src/jev_diagnostics/` | Engine, connectors, approvals, and activity logging |
| `test-kits/four-worlds/` | Four original worlds, artwork, prompts, fixtures, and offline runner |
| `tests/` | Automated regression checks |
| `docs/` | Current setup, architecture, and development guidance |
| `scripts/` | Build, packaging, and artwork source |
| `examples/` and `prompts/` | Small original CLI example and evidence prompt |
| `schemas/` and `instructions/` | Connector contracts and assistant guidance |
| `dist/` | One current local Windows package; excluded from Git |
| `build/`, `.qt/`, `.build-tools/`, `.venv/` | Local build tools and caches; excluded from Git |
| `.claude/` | Local Claude settings/worktree; excluded from Git |

Build output lives under `dist/`. Launch the packaged executable with
`--local-preview`. Keep its runtime folder in place after connecting Claude;
moving a package requires reviewing and approving its connection setup again.
Build scripts derive their locations from the repository root.

The four-world kit is a standalone offline fixture pack. Start with its
README; it has not been connected to the Workbench guest-access runner.

The public `main` branch starts from one snapshot of the current source.
Runtime data, credentials, machine settings, and build output are excluded
from source control.
