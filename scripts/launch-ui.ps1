param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$url = "http://127.0.0.1:$Port/"

function Test-ProAiServerUi {
    try {
        $response = Invoke-WebRequest -UseBasicParsing $url -TimeoutSec 1
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

if (-not (Test-ProAiServerUi)) {
    Start-Process -FilePath "C:\Windows\py.exe" `
        -ArgumentList @("-3.11", "-m", "pro_ai_server.cli", "ui", "--port", "$Port", "--no-open") `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden

    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 250
        if (Test-ProAiServerUi) {
            break
        }
    }
}

$browserCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
)

$browser = $browserCandidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if ($browser) {
    Start-Process -FilePath $browser -ArgumentList @("--app=$url", "--new-window")
} else {
    Start-Process $url
}
