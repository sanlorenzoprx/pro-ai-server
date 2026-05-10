$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$project = Join-Path $repoRoot "apps\windows\DroidShield.Desktop.csproj"
$output = Join-Path $repoRoot "dist\DroidShield.Desktop"

Get-Process DroidShield.Desktop -ErrorAction SilentlyContinue | Stop-Process -Force

dotnet publish $project -c Release -r win-x64 --self-contained false -o $output
if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed with exit code $LASTEXITCODE."
}

Write-Output "Built desktop app: $(Join-Path $output 'DroidShield.Desktop.exe')"
