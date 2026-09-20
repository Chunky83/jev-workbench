param(
    [string]$QtRoot,
    [string]$PythonArchive,
    [string]$PackageName
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$version = (Get-Content -LiteralPath (Join-Path $projectRoot 'VERSION.txt') -Raw).Trim()
if (-not $PackageName) { $PackageName = "JevWorkbench-$version" }
if (-not $QtRoot) { $QtRoot = Join-Path $projectRoot '.qt\6.8.3\msvc2022_64' }
if (-not $PythonArchive) { $PythonArchive = Join-Path $projectRoot 'build\python-embed.zip' }
$packageRoot = Join-Path (Join-Path $projectRoot 'dist') $PackageName
New-Item -ItemType Directory -Force $packageRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'build\Release\JevWorkbench.exe') -Destination $packageRoot
& (Join-Path $QtRoot 'bin\windeployqt.exe') --release --no-translations --no-compiler-runtime --qmldir (Join-Path $projectRoot 'desktop') (Join-Path $packageRoot 'JevWorkbench.exe')
if ($LASTEXITCODE -ne 0) { throw 'Qt deployment failed.' }
$runtime = Join-Path $packageRoot 'runtime'
New-Item -ItemType Directory -Force $runtime | Out-Null
Expand-Archive -LiteralPath $PythonArchive -DestinationPath $runtime -Force
$pathFile = Get-ChildItem -LiteralPath $runtime -Filter 'python*._pth' | Select-Object -First 1
$zipName = (Get-ChildItem -LiteralPath $runtime -Filter 'python*.zip' | Select-Object -First 1).Name
@($zipName, '.', '..\worker') | Set-Content -LiteralPath $pathFile.FullName -Encoding ascii
$worker = Join-Path $packageRoot 'worker\jev_diagnostics'
New-Item -ItemType Directory -Force $worker | Out-Null
Copy-Item -Path (Join-Path $projectRoot 'src\jev_diagnostics\*') -Destination $worker -Recurse -Force
$storyWorlds = Join-Path $packageRoot 'test-kits\four-worlds'
New-Item -ItemType Directory -Force $storyWorlds | Out-Null
Copy-Item -Path (Join-Path $projectRoot 'test-kits\four-worlds\*') -Destination $storyWorlds -Recurse -Force
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vsRoot = & $vswhere -latest -products '*' -property installationPath
$redistRoot = Join-Path $vsRoot 'VC\Redist\MSVC'
$redistVersion = Get-ChildItem -LiteralPath $redistRoot -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'x64\Microsoft.VC143.CRT') } | Sort-Object Name -Descending | Select-Object -First 1
if (-not $redistVersion) { throw 'Visual C++ app-local runtime was not found.' }
Get-ChildItem -LiteralPath (Join-Path $redistVersion.FullName 'x64\Microsoft.VC143.CRT') -Filter '*.dll' | Copy-Item -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $projectRoot 'README.md') -Destination $packageRoot
New-Item -ItemType Directory -Force (Join-Path $packageRoot 'docs') | Out-Null
Get-ChildItem -LiteralPath (Join-Path $projectRoot 'docs') -Filter '*.md' | Copy-Item -Destination (Join-Path $packageRoot 'docs')
Copy-Item -LiteralPath (Join-Path $projectRoot 'THIRD_PARTY_NOTICES.md') -Destination $packageRoot
Copy-Item -LiteralPath (Join-Path $projectRoot 'VERSION.txt') -Destination $packageRoot
Write-Output "Packaged desktop app: $packageRoot\JevWorkbench.exe"
