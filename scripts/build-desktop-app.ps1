$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$project = Join-Path $repoRoot "apps\windows\ProAiServer.Desktop.csproj"
$output = Join-Path $repoRoot "dist\ProAiServer.Desktop"

Get-Process ProAiServer.Desktop -ErrorAction SilentlyContinue | Stop-Process -Force

dotnet publish $project -c Release -r win-x64 --self-contained false -o $output
if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed with exit code $LASTEXITCODE."
}

Write-Output "Built desktop app: $(Join-Path $output 'ProAiServer.Desktop.exe')"
