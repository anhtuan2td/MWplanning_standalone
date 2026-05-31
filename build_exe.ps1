$root = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
Set-Location $root
$ErrorActionPreference = "Stop"

$distExe = Join-Path $root "dist\MWPreplanning.exe"
$runningDistExe = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $distExe }
if ($runningDistExe) {
    $processIds = ($runningDistExe | ForEach-Object { $_.Id }) -join ", "
    Write-Error "Cannot build because dist\MWPreplanning.exe is running. Close it first. Process ID(s): $processIds"
    exit 1
}

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

    $portableRoot = Join-Path $root ".nodejs"
    $nodeExe = Get-ChildItem -Path $portableRoot -Filter node.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($nodeExe) {
        return $nodeExe.FullName
    }

    return $null
}

function Install-PortableNode {
    $portableRoot = Join-Path $root ".nodejs"
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
# Forward build to packaging\build_exe.ps1 to centralize packaging helpers.
if (-Not (Test-Path "$root\packaging\build_exe.ps1")) {
    Write-Error "packaging\build_exe.ps1 not found. Run packaging/build_exe.ps1 or restore the file."
    exit 1
}
& "$root\packaging\build_exe.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
