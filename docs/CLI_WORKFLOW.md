# CLI Workflow

This is the current MVP flow for Windows hosts. Commands assume PowerShell from the repository root after `pip install -e .`.

## 1. Check the Host

```powershell
pro-ai-server doctor
```

`doctor` reports Python, Continue-compatible IDE CLIs, and ADB availability. Release builds should include bundled ADB at `embedded-tools/windows/platform-tools/adb.exe`; the CLI prefers that bundled ADB and falls back to system `adb` on `PATH`.

On Windows, this includes Cursor when the `cursor` CLI is installed. Cursor integration uses the Continue extension and the same `%USERPROFILE%\.continue\config.yaml` written by `configure-continue`.

Fastboot is not used in MVP behavior.

## 2. Validate Bundled Platform Tools

```powershell
pro-ai-server validate-platform-tools
```

This validates the Windows ADB runtime layouts and required files:

- `adb.exe`
- `AdbWinApi.dll`
- `AdbWinUsbApi.dll`

The MVP does not require `fastboot.exe`.

Run this after updating bundled platform-tools, before publishing a release, or when `doctor` reports that ADB is missing. There is no fastboot requirement for the MVP.

## 3. Validate Release Readiness

```powershell
pro-ai-server validate-release
```

Run `validate-release` before tagging or handing off a Windows release build. It checks that bundled ADB runtime files are present in the source and packaged layouts, that embedded tool package data is included, and that CI still runs the required gates.

## 4. Scan the Phone

Connect the phone over USB, enable USB debugging, accept the Android authorization prompt, then run:

```powershell
pro-ai-server scan
```

If more than one device is connected:

```powershell
pro-ai-server scan --serial <device-serial>
```

The scan reads Android version, ABI, RAM, storage, battery, and model information over ADB, then recommends a model profile.

## 5. Check Termux Readiness

```powershell
pro-ai-server termux-check
```

Run `termux-check` after the phone is visible to ADB and before pushing scripts. It verifies that Termux is installed, Termux:API is installed, and the Termux home directory has been initialized by opening Termux at least once.

With multiple devices:

```powershell
pro-ai-server termux-check --serial <device-serial>
```

## 6. Generate Termux Scripts

```powershell
pro-ai-server generate-scripts --mode usb
```

This writes inspectable files under `generated/termux`, including:

- `bootstrap.sh`
- `start-pro-ai-server.sh`
- `install-models.sh`
- `.shortcuts/Start Pro AI Server`
- `ANDROID_OPTIMIZATION_CHECKLIST.txt`
- `TERMUX_WIDGET_INSTRUCTIONS.txt`

USB mode binds Ollama to `127.0.0.1:11434`. LAN and Tailscale script modes bind Ollama to `0.0.0.0:11434`, which exposes the server beyond phone-local loopback.

## 7. Push Scripts to Termux

```powershell
pro-ai-server push-scripts
```

With multiple devices:

```powershell
pro-ai-server push-scripts --serial <device-serial>
```

The CLI uses `adb push` to copy generated files to the Termux home directory and creates the `.shortcuts` folder. After pushing, run the printed commands inside Termux.

Termux:Widget still requires manual installation and placement: install Termux:Widget on Android, add the generated `Start Pro AI Server` shortcut to `~/.shortcuts`, then place the widget/shortcut on the Android home screen.

## 8. Configure Continue

USB is the default and safest MVP mode:

```powershell
pro-ai-server configure-continue --mode usb
```

This writes `%USERPROFILE%\.continue\config.yaml` for an Ollama-compatible API at `http://localhost:11434`. If a Continue config already exists, the CLI backs it up first with a `config.yaml.pro-ai-server-backup-YYYYMMDD-HHMMSS` filename.

Cursor uses this same Continue configuration path when the Continue extension is installed, so no separate Cursor-specific config file is required for the MVP flow.

LAN and Tailscale require an explicit host:

```powershell
pro-ai-server configure-continue --mode lan --host 192.168.1.50
pro-ai-server configure-continue --mode tailscale --host pro-ai-phone
pro-ai-server configure-continue --mode tailscale --host 100.x.x.x
```

LAN mode exposes Ollama to devices on the local network. Tailscale mode should use a private Tailscale hostname or `100.x.x.x` IP address.

## 9. Set Up Tailscale

Use Tailscale when the phone and laptop should keep a stable private address without relying on the same Wi-Fi router:

```powershell
pro-ai-server setup-tailscale
```

The command verifies the Windows host client with `tailscale version`, checks the connected Android phone for package `com.tailscale.ipn`, and opens the Tailscale Play Store page on the phone when the Android app is missing.

To install the Windows client with `winget`:

```powershell
pro-ai-server setup-tailscale --install-host --yes
```

To install a local Android APK over ADB:

```powershell
pro-ai-server setup-tailscale --android-apk C:\path\to\tailscale.apk --yes
```

Android Play Store installation and Tailscale sign-in still require user approval on the device. After Tailscale is installed and signed in on both devices, configure Continue with the phone's private Tailscale hostname or `100.x.x.x` IP:

```powershell
pro-ai-server configure-continue --mode tailscale --host pro-ai-phone
```

## 10. Create the USB Tunnel

```powershell
pro-ai-server tunnel
```

With multiple devices:

```powershell
pro-ai-server tunnel --serial <device-serial>
```

This requests:

```text
adb reverse tcp:11434 tcp:11434
```

After the tunnel is active, Continue can use `http://localhost:11434` from the Windows host while Ollama remains bound to phone-local loopback in USB mode.

## 11. Guided Setup

Plan mode is the default:

```powershell
pro-ai-server setup
```

The plan prints the actions and safety notes without writing Continue config, pushing files, or creating the tunnel.

To execute the planned MVP actions:

```powershell
pro-ai-server setup --execute --yes
```

`--yes` is required because setup can write Continue config and can change network exposure when LAN or Tailscale mode is selected.

Useful variants:

```powershell
pro-ai-server setup --mode usb --push-scripts --execute --yes
pro-ai-server setup --mode tailscale --host pro-ai-phone
pro-ai-server setup --mode lan --host 192.168.1.50 --no-tunnel
```

## 12. Check Live Status

```powershell
pro-ai-server server-endpoints
pro-ai-server status
```

`server-endpoints` prints the local access URLs for the Termux/Ollama lane on `127.0.0.1:11434`; by default it also probes that forwarded endpoint and lists live models when it is reachable. If you have separately forwarded a native Android llama.cpp server, pass `--native-api-base` to display and probe that optional lane. `status` prints a concise readiness view for the connected phone, USB tunnel, Ollama `/api/tags`, and Continue-ready IDE integration. Both commands are read-only and intended for quick daily checks before opening Cursor, VS Code, VSCodium, or Windsurf.

Use a custom API base for LAN or Tailscale checks:

```powershell
pro-ai-server status --api-base http://pro-ai-phone:11434
```

## 13. Capture Diagnostics

```powershell
pro-ai-server diagnose
pro-ai-server diagnose --output diagnostics.txt
```

Diagnostics include host details, ADB path, connected phone state, selected hardware facts, `adb reverse --list`, IDE CLI discovery, and a local Ollama tags check. Reports redact user-profile paths where possible.
