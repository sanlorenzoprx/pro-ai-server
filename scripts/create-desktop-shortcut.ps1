param(
    [string]$ShortcutName = "DroidShield",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "$ShortcutName.lnk"
$iconPath = Join-Path $repoRoot "assets\icons\droidshield.ico"
$launcherPath = Join-Path $repoRoot "scripts\launch-ui.vbs"
$desktopExe = Join-Path $repoRoot "dist\DroidShield.Desktop\DroidShield.Desktop.exe"

if (-not (Test-Path $iconPath)) {
    throw "Icon not found: $iconPath. Run the icon generation step first."
}
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
if (Test-Path $desktopExe) {
    $shortcut.TargetPath = $desktopExe
    $shortcut.Arguments = ""
} else {
    if (-not (Test-Path $launcherPath)) {
        throw "Launcher not found: $launcherPath."
    }
    $shortcut.TargetPath = "$env:WINDIR\System32\wscript.exe"
    $shortcut.Arguments = "`"$launcherPath`""
}
$shortcut.WorkingDirectory = $repoRoot
$shortcut.IconLocation = $iconPath
$shortcut.Description = "Launch the DroidShield local dashboard"
$shortcut.Save()

Write-Output "Created shortcut: $shortcutPath"
