Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PlatformToolsUrl = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
$RequiredFiles = @(
    "adb.exe",
    "AdbWinApi.dll",
    "AdbWinUsbApi.dll"
)

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DownloadPath = Join-Path ([System.IO.Path]::GetTempPath()) "platform-tools-latest-windows.zip"
$ExtractRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("platform-tools-" + [System.Guid]::NewGuid().ToString("N"))
$SourcePlatformTools = Join-Path $ExtractRoot "platform-tools"
$DestinationDirs = @(
    (Join-Path $RepoRoot "embedded-tools\windows\platform-tools"),
    (Join-Path $RepoRoot "src\pro_ai_server\embedded-tools\windows\platform-tools")
)

try {
    Write-Host "Downloading Android Platform Tools for Windows..."
    Invoke-WebRequest -Uri $PlatformToolsUrl -OutFile $DownloadPath

    Write-Host "Extracting platform tools..."
    New-Item -ItemType Directory -Path $ExtractRoot -Force | Out-Null
    Expand-Archive -Path $DownloadPath -DestinationPath $ExtractRoot -Force

    foreach ($FileName in $RequiredFiles) {
        $SourceFile = Join-Path $SourcePlatformTools $FileName
        if (-not (Test-Path -LiteralPath $SourceFile -PathType Leaf)) {
            throw "Downloaded Platform Tools archive did not contain required file: $FileName"
        }
    }

    foreach ($DestinationDir in $DestinationDirs) {
        New-Item -ItemType Directory -Path $DestinationDir -Force | Out-Null

        foreach ($FileName in $RequiredFiles) {
            $SourceFile = Join-Path $SourcePlatformTools $FileName
            $DestinationFile = Join-Path $DestinationDir $FileName
            Copy-Item -LiteralPath $SourceFile -Destination $DestinationFile -Force
            Write-Host "Updated $DestinationFile"
        }
    }

    Write-Host "Bundled ADB runtime files are up to date."
}
finally {
    if (Test-Path -LiteralPath $ExtractRoot) {
        Remove-Item -LiteralPath $ExtractRoot -Recurse -Force
    }
}
