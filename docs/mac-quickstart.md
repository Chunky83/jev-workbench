# Jev Workbench on your Mac

Jev Workbench is a public project. Packages, when available, appear on the repository’s Releases or Actions pages.

## Download a build

1. Open the repository's Releases page and choose a tested macOS package, if one is published. Otherwise open Actions → Build macOS packages → a successful run and download its artifact.
2. Choose **arm64** for Apple Silicon (M1 or newer). Intel Macs are not supported. Apple menu → About This Mac shows which you have.
3. Extract the download. An Actions artifact contains another ZIP; extract that too to find `JevWorkbench.app`.
4. Move the app into Applications and open it. The package bundles Python and Qt; you do not need a development environment to use it.

These initial test packages are ad-hoc signed, not Apple-notarized. If macOS blocks this trusted download, attempt to open it once, then use System Settings → Privacy & Security → Open Anyway if your Mac policy permits it. Do not disable system-wide security protections. Managed Macs may require administrator assistance.

## First run

Start with Local checks. Run the included fixture, inspect State and Results, and save your case to a folder you choose. The fixture is a demonstration; it does not test an external website. Light and Night Shift themes are both available.

For Live Jev, enter your own TypeSafe key through API settings. Keys are session-only and are not included in saved cases. Do not commit credentials or private logs. The current Windows preview includes a Claude connector. ChatGPT account-side setup and current macOS connector validation remain pending; see `docs/assistant-connectors-plan.md`.

## Contribute code

Use the repository’s **Code** menu to copy its clone URL, then clone it or your fork. Install Python 3.11 or newer and Xcode Command Line Tools to build from source. From the cloned project folder:

```sh
git switch -c feature/my-change
bash scripts/build-macos.sh
```

The script downloads build dependencies and runs the tests before producing an app ZIP. Build natively on Apple Silicon, not through Rosetta. See `docs/releases.md` for release numbering and packaging details.
