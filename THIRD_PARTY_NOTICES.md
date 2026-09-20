# Bundled components

This local development package uses dynamically linked Qt 6.8.3 (Core, Gui, Widgets, Qml, Quick and Quick Controls, plus required plugins). Qt offers LGPL/GPL and commercial licensing; individual component licenses must be retained and reviewed before distributing a release. Qt source for this exact version is available at https://download.qt.io/archive/qt/6.8/6.8.3/single/ . Licensing information: https://doc.qt.io/qt-6/licensing.html .

The Windows package includes unmodified Python 3.13.15 from the Python Software Foundation, under the licenses reproduced in runtime/LICENSE.txt. Source: https://www.python.org/downloads/release/python-31315/ . Mac packaging bundles the build interpreter through PyInstaller; the build script copies that interpreter's license and records its version inside the app. PyInstaller's licensing information is at https://pyinstaller.org/en/stable/license.html .

Microsoft Visual C++ runtime DLLs are copied from the installed Visual Studio Build Tools redistributable directory. Their redistribution terms are supplied with Visual Studio. This is a local development build, not a signed public installer.

The repository's application source and the Python worker source remain separate from these third-party components. No TypeSafe API credentials are bundled.
