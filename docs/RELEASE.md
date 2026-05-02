# Release Checklist

This checklist is Windows-first and assumes PowerShell from the repository root after installing the project in editable mode:

```powershell
python -m pip install -e ".[dev]"
```

## Required Gates

Run these before tagging, packaging, or handing off a release build:

```powershell
pro-ai-server validate-release
pro-ai-server validate-platform-tools
pytest
ruff check .
pro-ai-server doctor
```

`validate-release` checks the bundled ADB runtime files, embedded tool package data, and CI gate coverage. `validate-platform-tools` is the narrower Windows Platform Tools check for the bundled ADB layout.

CI also runs `pro-ai-server validate-release` and a lightweight wheel build:

```powershell
python -m pip wheel . --no-deps --wheel-dir dist
```

The wheel command uses pip and the existing `pyproject.toml` build backend, so it does not add a new release dependency.

## Bundled Platform Tools

Release builds include these Windows ADB files:

- `embedded-tools/windows/platform-tools/adb.exe`
- `embedded-tools/windows/platform-tools/AdbWinApi.dll`
- `embedded-tools/windows/platform-tools/AdbWinUsbApi.dll`

Fastboot is not used by the MVP workflow, and release validation does not require `fastboot.exe`.

## Refresh Platform Tools

Preferred refresh path:

```powershell
scripts/download-platform-tools.ps1
pro-ai-server validate-platform-tools
```

Fallback path when the script cannot download Platform Tools:

1. Install or update Android Studio.
2. Open SDK Manager and install Android SDK Platform-Tools.
3. Copy `adb.exe`, `AdbWinApi.dll`, and `AdbWinUsbApi.dll` from the SDK `platform-tools` directory into `embedded-tools/windows/platform-tools`.
4. Run `pro-ai-server validate-platform-tools`.

Do not add `fastboot.exe` as a release requirement unless the product flow starts using fastboot.

## Smoke Commands

After the required gates pass, run the smoke path that exercises script generation, setup planning, and diagnostics without requiring a phone mutation:

```powershell
pro-ai-server generate-scripts --mode usb
pro-ai-server setup
pro-ai-server diagnose --output diagnostics.txt
```

Use `setup` without `--execute` for release smoke checks so it prints the plan without writing Continue config, pushing files, or creating an ADB tunnel.
