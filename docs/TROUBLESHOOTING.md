# Troubleshooting

Use these checks when the Windows host, Android phone, Termux, Ollama, or Continue does not behave like the MVP workflow expects.

## ADB and Device Selection

### No device found

Run:

```powershell
droidshield doctor
adb devices
```

Confirm the phone is connected by USB, USB debugging is enabled in Android developer options, and the cable supports data. Reconnect the phone, then rerun the command that failed.

Release builds should use bundled ADB from `embedded-tools/windows/platform-tools/adb.exe`. If bundled ADB is missing or invalid, run `droidshield validate-platform-tools`. As a fallback for development machines, install Android Studio or the Android SDK Platform Tools and make sure `adb.exe` is on `PATH`.

The MVP has no fastboot flow: fastboot is not used, and `fastboot.exe` is not required.

### Unauthorized device

If `adb devices` shows `unauthorized`, unlock the phone and accept the USB debugging prompt. If the prompt does not appear, revoke USB debugging authorizations in Android developer options, reconnect USB, and accept the new prompt.

### Multiple devices require --serial

When more than one Android device or emulator is visible, use the serial from `adb devices`:

```powershell
droidshield scan --serial <device-serial>
droidshield termux-check --serial <device-serial>
droidshield push-scripts --serial <device-serial>
droidshield tunnel --serial <device-serial>
```

## Termux Readiness

Run this before pushing scripts:

```powershell
droidshield termux-check
```

If Termux is missing, install Termux from F-Droid or GitHub, then open it once. If Termux:API is missing, install Termux:API, then rerun `termux-check`. If Termux home is not initialized, open Termux once on the phone so `/data/data/com.termux/files/home` exists.

Termux:Widget manual placement is still required. Install Termux:Widget, confirm the generated `Start DroidShield` shortcut is in `~/.shortcuts`, confirm the generated icon is in `~/.shortcuts/icons/Start DroidShield.png`, then add the widget or shortcut from the Android home screen. If the shortcut already existed before the icon was added, remove it from the home screen and add it again.

## Ollama and Models

### Ollama not responding on localhost:11434

For USB mode, start the generated script inside Termux, then create the forward tunnel:

```powershell
droidshield tunnel
```

Confirm Continue points to `http://localhost:11434`. In USB mode, Ollama should bind to `127.0.0.1:11434` on the phone and Windows reaches it through `adb forward tcp:11434 tcp:11434`.

For LAN or Tailscale mode, confirm the phone script was generated for that mode and that Continue uses the explicit `--host` value.

### Missing models

Run the generated model installer inside Termux:

```sh
~/install-models.sh
```

If Continue reports missing models, compare the model names in `%USERPROFILE%\.continue\config.yaml` with `ollama list` inside Termux. Re-run `droidshield generate-scripts --mode usb` if you changed the profile or model plan.

## Continue Configuration

`droidshield configure-continue` writes `%USERPROFILE%\.continue\config.yaml`. When an existing Continue config is present, the Continue backup is written next to it with this filename pattern:

```text
config.yaml.droidshield-backup-YYYYMMDD-HHMMSS
```

Keep that backup if you need to restore previous Continue settings.

## LAN and Tailscale Exposure

USB mode is the safest default because Continue uses `http://localhost:11434` through an ADB tunnel. LAN mode exposes Ollama on the local network, and LAN or Tailscale scripts bind Ollama to `0.0.0.0:11434`.

Use LAN only on trusted networks:

```powershell
droidshield configure-continue --mode lan --host 192.168.1.50
```

For Tailscale, prefer the private Tailscale hostname or the `100.x.x.x` Tailscale IP:

```powershell
droidshield configure-continue --mode tailscale --host pro-ai-phone
droidshield configure-continue --mode tailscale --host 100.x.x.x
```

## Release Validation

Before publishing or handing off a build, run:

```powershell
droidshield validate-release
```

`validate-release` checks bundled ADB runtime files, package data for embedded tools, and CI gates. Use `droidshield validate-platform-tools` for a narrower bundled ADB validation when troubleshooting host ADB problems.
