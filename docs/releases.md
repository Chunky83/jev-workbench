# Current baseline: 0.1.0

`VERSION.txt` is the single source of the app's SemVer version. CMake,
desktop display, Python package metadata, and default package names use it.
Saved test `schema_version` is separate and currently remains 1.

This baseline includes the desktop workspace, Claude connector, automatic
incoming-proposal review, explicit approval, result discovery, activity
logging, application icon, and the offline four-world test kit.

Windows validation: 68 Python tests in development and packaged runtimes,
14 packaged desktop checks across Light and Dark, the syntax-highlighting
check, and an actual Claude-to-Workbench proposal/approval/result round trip.
The checks use synthetic fixtures; they do not certify a real project.

## Packaging

Build Windows with `scripts/build-windows.ps1`, package with
`scripts/package-windows.ps1`, and include connector dependencies with
`scripts/package-connectors.ps1`. Keep the portable package together.

The repository provides **Build macOS packages** as a manual-only
Actions workflow. Pushes and version changes do not start it. It targets
Apple Silicon, bundles the worker, and uploads a successful package as an
Actions artifact. The current baseline still needs a fresh macOS build and
real-device validation. Old-repository artifact links are no longer current.

On a Mac with Python 3.11+ and Xcode Command Line Tools, run
`bash scripts/build-macos.sh`. The build is ad-hoc signed. Developer ID
signing and notarization remain future work; no signing credentials are
stored here. See the [Mac quickstart](mac-quickstart.md).
