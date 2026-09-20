---
name: release-readiness
description: Assess or prepare a Jev Workbench release using version, test, packaging, documentation, artifact, and platform-specific evidence. Use for release checks or release preparation; not for routine feature implementation.
---

# Release Readiness

Treat readiness as an evidence-backed assessment. Read `docs/releases.md`, `docs/desktop.md`, `VERSION.txt`, the packaging scripts, and the current platform workflow before making claims.

## Checklist

1. Confirm the requested release scope and compare it with the documented current baseline. Check the worktree for uncommitted or unrelated changes without discarding them.
2. Verify `VERSION.txt` is the intended SemVer source and that CMake, Python metadata, desktop display, and package naming derive from it. Keep application and persisted-schema versions separate.
3. Run the full Python suite. Run the syntax-highlighting, desktop smoke, UI smoke in Light and Dark, connector round-trip, and packaged-runtime checks when they are in scope and available.
4. Build and inspect the platform package with the repository scripts. Confirm expected executable, Qt runtime, Python worker, connector dependencies, notices, and absence of secrets or local runtime data.
5. Check setup, release, limitations, and platform documentation against observed behavior. Keep synthetic-fixture claims scoped.
6. Treat macOS as ready only after the manual workflow or local build succeeds and the package is validated on an appropriate Mac. Ad-hoc signing is not notarization.
7. List blockers, residual risks, and unrun checks. A successful source test suite alone is not packaged-release evidence.

Do not publish, tag, push, upload, sign, notarize, or change external release state unless the user explicitly requests that action. When asked only for an assessment, make no release mutations.

## Output format

- Verdict: ready, ready with caveats, or not ready
- Release scope and target platforms
- Evidence collected, including exact checks and artifacts inspected
- Platform status
- Blocking findings
- Residual risks and caveats
- Unrun or unavailable checks
- Recommended next action
