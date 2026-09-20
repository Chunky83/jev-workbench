#!/bin/bash
# Run natively on an Apple Silicon Mac.
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"
if [ "$(uname -s)" != "Darwin" ]; then
    echo "This script requires macOS and the Xcode Command Line Tools." >&2
    exit 1
fi
xcrun --find clang++ >/dev/null
if [ "$(uname -m)" != "arm64" ]; then
    echo "This build requires Apple Silicon running natively (not Rosetta)." >&2
    exit 1
fi
python3 -m venv .mac-build-tools
build_python="$project_root/.mac-build-tools/bin/python"
"$build_python" -m pip install 'aqtinstall==3.3.0' 'cmake==3.31.6' 'pyinstaller==6.16.0'
"$build_python" -m pip install -r requirements-connectors.txt
qt_root="$project_root/.qt-macos/6.8.3/macos"
if [ ! -x "$qt_root/bin/macdeployqt" ]; then
    "$build_python" -m aqt install-qt mac desktop 6.8.3 clang_64 -O "$project_root/.qt-macos" --archives qtbase qtdeclarative qtshadertools qttools qttranslations
fi
export QT_ROOT="$qt_root"
export PATH="$project_root/.mac-build-tools/bin:$qt_root/bin:$PATH"
cmake -S . -B build-macos -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$qt_root" -DCMAKE_OSX_ARCHITECTURES="$(uname -m)" -DCMAKE_OSX_DEPLOYMENT_TARGET=12.0
cmake --build build-macos --parallel 4
QT_QPA_PLATFORM=offscreen ctest --test-dir build-macos --output-on-failure
PYTHONPATH=src "$build_python" -m unittest discover -s tests -v
bash scripts/package-macos.sh
