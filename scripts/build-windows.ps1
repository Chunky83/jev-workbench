param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$buildPython = Join-Path $projectRoot '.build-tools\Scripts\python.exe'
$qtRoot = Join-Path $projectRoot '.qt\6.8.3\msvc2022_64'
if (-not (Test-Path -LiteralPath $buildPython) -or -not (Test-Path -LiteralPath $qtRoot)) {
    throw 'Install the project-local build tools and Qt first. See docs/desktop.md.'
}
& $buildPython -m cmake -S $projectRoot -B (Join-Path $projectRoot 'build') -G 'Visual Studio 17 2022' -A x64 "-DCMAKE_PREFIX_PATH=$qtRoot"
if ($LASTEXITCODE -ne 0) { throw 'Build configuration failed.' }
& $buildPython -m cmake --build (Join-Path $projectRoot 'build') --config Release --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed.' }
