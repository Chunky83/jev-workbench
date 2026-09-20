#!/bin/bash
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"
if [ "$(uname -s)" != "Darwin" ]; then
    echo "Packaging must run on macOS." >&2
    exit 1
fi
version="$(tr -d '\r\n' < VERSION.txt)"
architecture="$(uname -m)"
if [ "$architecture" != "arm64" ]; then
    echo "Mac packages require an Apple Silicon Mac running natively (not Rosetta)." >&2
    exit 1
fi
qt_root="${QT_ROOT:-$project_root/.qt-macos/6.8.3/macos}"
build_python="$project_root/.mac-build-tools/bin/python"
package_root="$project_root/dist/macos-$version-$architecture"
application="$package_root/JevWorkbench.app"
mkdir -p "$package_root"
if [ -e "$application" ]; then
    echo "Output already exists: $application. Choose a new release version or move this build aside." >&2
    exit 1
fi
ditto build-macos/JevWorkbench.app "$application"
"$qt_root/bin/macdeployqt" "$application" -qmldir="$project_root/desktop" -always-overwrite -appstore-compliant
# A single executable avoids nested Python directories being mistaken for bundles by codesign.
"$build_python" -m PyInstaller --noconfirm --clean --onefile --target-arch arm64 --name jev-worker \
    --paths "$project_root/src" --distpath "$project_root/build-worker/dist" \
    --workpath "$project_root/build-worker/work" --specpath "$project_root/build-worker" \
    scripts/mac_worker_entry.py
mkdir -p "$application/Contents/Helpers/jev-worker" "$application/Contents/Resources/worker/jev_diagnostics"
cp build-worker/dist/jev-worker "$application/Contents/Helpers/jev-worker/jev-worker"
codesign --verify --strict "$application/Contents/Helpers/jev-worker/jev-worker"
cp src/jev_diagnostics/*.py "$application/Contents/Resources/worker/jev_diagnostics/"
cp VERSION.txt THIRD_PARTY_NOTICES.md "$application/Contents/Resources/"
"$build_python" -c 'import sys; print(sys.version)' > "$application/Contents/Resources/PYTHON_VERSION.txt"
"$build_python" -c 'import sys; print(sys.copyright)' > "$application/Contents/Resources/PYTHON_COPYRIGHT.txt"
"$build_python" -c 'import pathlib, sys; candidates = [pathlib.Path(sys.base_prefix) / "LICENSE.txt", pathlib.Path(sys.base_prefix) / "lib" / ("python" + str(sys.version_info.major) + "." + str(sys.version_info.minor)) / "LICENSE.txt"]; found = next((p for p in candidates if p.exists()), None); sys.exit("Python license not found; copy the matching interpreter license before distribution.") if found is None else print(found.read_text())' > "$application/Contents/Resources/PYTHON_LICENSE.txt"
ditto docs "$application/Contents/Resources/docs"
# Local ad-hoc signing is sufficient for testing. Public distribution needs Developer ID and notarization.
codesign --force --deep --sign - "$application"
codesign --verify --deep --strict "$application"
executable="$application/Contents/MacOS/JevWorkbench"
"$executable" --smoke-test
"$executable" --ui-smoke --theme Light
"$executable" --ui-smoke --theme Dark
archive="$project_root/dist/JevWorkbench-$version-macos-$architecture.zip"
ditto -c -k --sequesterRsrc --keepParent "$application" "$archive"
echo "Built and checked: $archive"
