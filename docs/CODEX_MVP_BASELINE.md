# Pro AI Server MVP Baseline

## Purpose

Build Pro AI Server as a transparent, test-driven installer and manager that
turns a spare Android phone into a local AI coding server for
Continue-compatible IDEs such as VS Code, Cursor, VSCodium, Windsurf, and
JetBrains.

Release builds should bundle Android Platform Tools and prefer bundled `adb`.
The MVP must not depend on customers manually installing ADB.

## MVP Product Promise

A developer can connect an Android phone, run Pro AI Server, and get:

1. Hardware-aware model recommendations.
2. A local Ollama server setup path for Termux.
3. A dual-model coding workflow:
   - chat, edit, and refactor model
   - fast autocomplete model
4. Safe Continue IDE config generation.
5. USB tunnel support through `adb reverse tcp:11434 tcp:11434`.
6. One-tap Android home screen startup through Termux:Widget.
7. Optional private remote access through Tailscale.
8. Diagnostics and support logs.

## Current Baseline Status

This branch now contains the Python CLI MVP described by this baseline. The
implemented surface includes:

- Python CLI scaffold and tested command routing.
- Bundled Windows ADB resolver with system ADB fallback.
- Host `doctor` checks for Python, supported IDE CLIs, and ADB.
- Real ADB hardware auto-assessment for RAM, storage, ABI, Android version,
  battery, charging state, and device identity.
- Hardware-aware model profile selection and model pull planning.
- Inspectable Termux bootstrap, startup, model install, Android optimization,
  and Termux:Widget helper script generation.
- Continue `config.yaml` generation for USB, LAN, and Tailscale modes with
  backup protection for existing configs.
- Termux readiness, Ollama readiness, USB tunnel, setup workflow, setup
  receipts, diagnostics, and release validation commands.
- CI enforcement for linting, tests, release validation, and wheel builds.

Deferred work should be tracked as new product requirements rather than as MVP
gaps in this baseline. Fastboot remains out of scope for the MVP flow.

## Test-Driven Rule

For every MVP feature:

1. Write tests first.
2. Make tests fail.
3. Implement the smallest code to pass.
4. Refactor.
5. Keep CLI behavior simple and visible.

No feature is complete unless it has automated tests.

## Feature 1: Bundled ADB Resolver

The app should use bundled ADB first, then system ADB:

1. bundled `embedded-tools/windows/platform-tools/adb.exe`
2. system `adb` on PATH
3. friendly error if neither exists

Do not use `fastboot` in MVP commands.

Required tests:

- returns bundled ADB when file exists
- falls back to system ADB when bundled ADB does not exist
- returns `None` when neither exists
- never calls or references `fastboot` in MVP command builders

## Feature 2: Hardware Auto-Assessment

Replace manual `profile 8` with a real device scan.

ADB data to collect:

- `cat /proc/meminfo`
- `df -k /data`
- `getprop ro.product.cpu.abi`
- `getprop ro.build.version.release`
- `getprop ro.product.manufacturer`
- `getprop ro.product.model`
- `dumpsys battery`

Optional later:

- `dumpsys thermalservice`

Minimum `DeviceProfile` fields:

- `serial`
- `manufacturer`
- `model`
- `android_version`
- `abi`
- `ram_gb`
- `free_storage_gb`
- `battery_level`
- `battery_temperature_c`
- `is_charging`
- `warnings`
- `recommended_profile`

Model profile rules:

- Lightweight: RAM under 5 GB, chat `qwen2.5-coder:1.5b`,
  autocomplete `qwen2.5-coder:0.5b`, status `experimental`.
- Professional: RAM from 5 GB to under 9 GB, chat `qwen2.5-coder:3b`,
  autocomplete `qwen2.5-coder:1.5b-base`, status `recommended`.
- Max: RAM 9 GB or greater, chat `qwen2.5-coder:7b`, autocomplete
  `qwen2.5-coder:1.5b-base`, status `high-memory`.

Storage rules:

- Warn before model download when free storage is under 8 GB.
- Block full install and recommend lightweight/manual cleanup when free storage
  is under 4 GB.

ABI rules:

- Prefer `arm64-v8a` or `aarch64`.
- Warn on 32-bit ABI.

## Feature 3: Android OS Optimization

Generate a user-visible checklist for Android battery settings:

1. Open Android Settings.
2. Open Apps.
3. Open Termux.
4. Open Battery.
5. Set battery usage to Unrestricted.

The app must not claim it can guarantee all OEM battery behavior.

Generated Termux startup scripts should run `termux-wake-lock`, verify
`termux-api` is installed, and show a clear error if Termux API is missing.

## Feature 4: Dual-Model Configuration

The selected profile should produce:

- `chat_model`
- `autocomplete_model`
- `ollama_pull_commands`
- `continue_config_yaml`

Example Professional pull commands:

```bash
ollama pull qwen2.5-coder:3b
ollama pull qwen2.5-coder:1.5b-base
```

Duplicate model pulls should be emitted only once.

## Feature 5: Continue IDE Integration

Generate a safe Continue `config.yaml`.

Windows local config path:

```text
%USERPROFILE%\.continue\config.yaml
```

Before writing config:

1. Create `%USERPROFILE%\.continue` if missing.
2. If `config.yaml` exists, copy it to
   `config.yaml.pro-ai-server-backup-YYYYMMDD-HHMMSS`.
3. Write generated config.
4. Print the backup path when a backup was created.

USB mode should point Continue to:

```text
http://localhost:11434
```

LAN or Tailscale mode should point Continue to:

```text
http://<selected-host-or-ip>:11434
```

Minimum YAML shape:

```yaml
name: Pro AI Server Local
version: 0.0.1
schema: v1
models:
  - name: Pro AI Chat
    provider: ollama
    model: qwen2.5-coder:3b
    apiBase: http://localhost:11434
    roles:
      - chat
      - edit
      - apply
  - name: Pro AI Autocomplete
    provider: ollama
    model: qwen2.5-coder:1.5b-base
    apiBase: http://localhost:11434
    roles:
      - autocomplete
```

Detect installed IDE CLIs without failing if any are missing:

- `code`
- `cursor`
- `codium`
- `windsurf`

## Feature 6: Termux Bootstrap Script Generator

Generate inspectable scripts instead of relying on ADB typing long shell
commands into the phone UI.

Generated files:

- `generated/termux/bootstrap.sh`
- `generated/termux/start-pro-ai-server.sh`
- `generated/termux/install-models.sh`

`bootstrap.sh` responsibilities:

```bash
pkg update -y
pkg install -y proot-distro curl termux-api
proot-distro install debian
```

`start-pro-ai-server.sh` responsibilities:

```bash
termux-wake-lock
proot-distro login debian -- bash -lc 'export OLLAMA_HOST=127.0.0.1:11434; ollama serve'
```

For LAN or Tailscale mode only:

```bash
OLLAMA_HOST=0.0.0.0:11434
```

`install-models.sh` should pull the selected chat and autocomplete models inside
the Debian proot environment.

## Feature 7: Termux:Widget Startup

Generate a shortcut script intended for:

```text
~/.shortcuts/Start Pro AI Server
```

The script should call:

```bash
~/start-pro-ai-server.sh
```

The app should explain that the user must install Termux:Widget and add the
shortcut manually.

## Feature 8: Tailscale Private Access Mode

Tailscale is optional. USB mode remains the default.

Supported CLI examples:

```powershell
pro-ai-server configure-continue --mode usb
pro-ai-server configure-continue --mode tailscale --host pro-ai-phone
pro-ai-server configure-continue --mode tailscale --host 100.x.x.x
```

Security rules:

- USB mode uses `localhost`.
- Tailscale/LAN mode may bind Ollama to `0.0.0.0` on the phone only after
  explicit user choice.
- LAN mode should warn that Ollama is exposed to the local network.
- Prefer a Tailscale hostname or Tailscale IP over a random Wi-Fi IP.

## Feature 9: Diagnostics

Add:

```powershell
pro-ai-server diagnose
```

Diagnostics should include:

- Host: Python version, OS, Pro AI Server version, ADB path, IDE CLIs found.
- Phone: `adb devices`, manufacturer, model, Android version, ABI, RAM, free
  storage, battery level, charging state.
- Server: `adb reverse --list`, `curl http://localhost:11434/api/tags`.

Diagnostics should handle no phone connected and Ollama not responding.

## Feature 10: CI and Quality Gates

Every PR should run tests automatically.

Create `.github/workflows/ci.yml` with:

```yaml
python -m pip install -e ".[dev]"
ruff check .
pytest
```

Before merging MVP implementation PRs, run:

```powershell
pytest
ruff check .
pro-ai-server doctor
```

## Suggested Implementation Order

1. `tools.py`: bundled ADB resolver.
2. `hardware.py`: ADB output parsers and profile selection.
3. `models.py`: model plan generation.
4. `continue_config.py`: YAML generation and backup.
5. `termux_scripts.py`: script generation.
6. `ide.py`: IDE CLI detection.
7. `tunnel.py`: ADB reverse tunnel.
8. `diagnostics.py`: support report.
9. `cli.py`: expose commands.
10. `.github/workflows/ci.yml`: automated checks.

Expected CLI commands by MVP end:

```powershell
pro-ai-server doctor
pro-ai-server scan
pro-ai-server profile 8
pro-ai-server generate-scripts --mode usb
pro-ai-server configure-continue --mode usb
pro-ai-server tunnel
pro-ai-server diagnose
```
