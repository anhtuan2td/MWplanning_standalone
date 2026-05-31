$root = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
Set-Location $root
$ErrorActionPreference = "Stop"

# This script originally lived at repo root; kept here to organize packaging helpers.

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-Not $pythonCmd) {
    Write-Error "Python is required but was not found in PATH."
    exit 1
}
 
$python = $pythonCmd.Source
function Get-NodeExecutable {
    $node = Get-Command node -ErrorAction SilentlyContinue
    if ($node) {
        return $node.Source
    }

    $portableRoot = Join-Path $root "..\.nodejs"
    $nodeExe = Get-ChildItem -Path $portableRoot -Filter node.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($nodeExe) {
        return $nodeExe.FullName
    }

    return $null
}

function Install-PortableNode {
    $portableRoot = Join-Path $root "..\.nodejs"
    $nodeUrl = "https://nodejs.org/dist/v22.17.1/node-v22.17.1-win-x64.zip"
    $zipPath = Join-Path $portableRoot "node.zip"

    Write-Host "Downloading portable Node.js..."
    New-Item -ItemType Directory -Path $portableRoot -Force | Out-Null
    Invoke-WebRequest -Uri $nodeUrl -OutFile $zipPath -UseBasicParsing

    Write-Host "Extracting Node.js..."
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $portableRoot)
    Remove-Item $zipPath

    $nodeExe = Get-ChildItem -Path $portableRoot -Filter node.exe -Recurse | Select-Object -First 1
    if (-Not $nodeExe) {
        Write-Error "Failed to locate node.exe after extracting Node.js."
        exit 1
    }
    return $nodeExe.FullName
}

Write-Host "Building frontend assets..."
$nodeExe = Get-NodeExecutable
if (-Not $nodeExe) {
    Write-Host "Node.js not found in PATH. Installing portable Node.js to .nodejs..."
    $nodeExe = Install-PortableNode
}

$nodeDir = Split-Path $nodeExe -Parent
$env:PATH = "${nodeDir};$env:PATH"

$npmCli = Join-Path (Split-Path $nodeExe -Parent) "node_modules\npm\bin\npm-cli.js"
if (-Not (Test-Path $npmCli)) {
    $npmCli = Join-Path $root "..\.nodejs\node-v22.17.1-win-x64\node_modules\npm\bin\npm-cli.js"
}
if (-Not (Test-Path $npmCli)) {
    Write-Error "npm CLI not found. Please ensure Node.js extraction completed successfully."
    exit 1
}

Push-Location ..\frontend
& $nodeExe $npmCli install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $nodeExe $npmCli run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Pop-Location

Write-Host "Installing packaging dependency..."
& $python -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Packaging EXE with PyInstaller..."
& $python -m PyInstaller --clean --onefile --name MWPreplanning `
    --collect-all rasterio `
    --add-data "config\planner_config.yaml;config" `
    --add-data "data\mw_links\existing_links.csv;data\mw_links" `
    --add-data "frontend\dist;frontend\dist" `
    backend\run.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. Binary should be in dist\MWPreplanning.exe"
