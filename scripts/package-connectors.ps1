param(
    [string]$PackageName = 'JevWorkbench-0.1.0-preview',
    [string]$BuildPython = '.venv\Scripts\python.exe'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$packageRoot = Join-Path (Join-Path $projectRoot 'dist') $PackageName
$runtime = Join-Path $packageRoot 'runtime\python.exe'
if (-not (Test-Path -LiteralPath $runtime)) { throw 'Package the desktop first.' }
$pythonVersion = & $runtime -c 'import sys; print(str(sys.version_info.major) + "." + str(sys.version_info.minor))'
& $BuildPython -m pip install --target (Join-Path $packageRoot 'worker') --python-version $pythonVersion --only-binary=:all: -r (Join-Path $projectRoot 'requirements-connectors.txt')
if ($LASTEXITCODE -ne 0) { throw 'Connector dependency packaging failed.' }
& $runtime -m jev_diagnostics.connectors.mcp_server --help
if ($LASTEXITCODE -ne 0) { throw 'Packaged MCP server failed to start.' }
Write-Output 'Connector dependencies bundled. No account connection was configured.'
