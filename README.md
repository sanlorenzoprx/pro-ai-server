# Pro AI Server

Turn a spare Android phone into a local AI coding server for Continue-compatible IDEs such as VS Code, Cursor, VSCodium, and Windsurf.

Repository:

```text
https://github.com/sanlorenzoprx/pro-ai-server.git
```

## Current MVP

This branch contains the Python CLI MVP for preparing an Android phone to run Ollama from Termux and expose it to Continue.

The CLI currently supports:

- `doctor` host checks for Python, IDE CLIs, and ADB availability.
- `validate-platform-tools` checks for bundled Windows Platform Tools runtime files.
- `scan --serial <device>` Android hardware assessment over ADB.
- `generate-scripts` creation of inspectable Termux bootstrap, start, model install, Android optimization, and Termux:Widget helper files.
- `push-scripts --serial <device>` delivery of generated Termux files with `adb push`.
- `configure-continue --mode usb` Continue `config.yaml` generation, with backup protection for an existing config.
- `tunnel --serial <device>` USB forwarding with `adb reverse tcp:11434 tcp:11434`.
- `setup` plan mode and `setup --execute --yes` for the guided MVP flow.
- `diagnose --output diagnostics.txt` support reports for host, phone, tunnel, and local Ollama checks.

The MVP prefers bundled ADB at `embedded-tools/windows/platform-tools/adb.exe`, then falls back to system `adb` on `PATH`. Fastboot is not used by MVP behavior.

## Windows Quickstart

```powershell
cd "C:\repos\Pro-AI-Server"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]

pro-ai-server doctor
pro-ai-server validate-platform-tools
pro-ai-server scan
pro-ai-server generate-scripts --mode usb
pro-ai-server push-scripts
pro-ai-server configure-continue --mode usb
pro-ai-server tunnel
```

When multiple phones are connected, pass `--serial <device>` to ADB-backed commands such as `scan`, `push-scripts`, and `tunnel`.

See [docs/CLI_WORKFLOW.md](docs/CLI_WORKFLOW.md) for the full MVP CLI flow, including setup plan/execute mode, LAN/Tailscale warnings, Continue backup behavior, and Termux:Widget placement.

## Connection Modes

USB is the default and safest MVP mode. It keeps Ollama bound to `127.0.0.1:11434` on the phone and uses `adb reverse` so Continue talks to `http://localhost:11434` on the host.

LAN and Tailscale modes require `--host` when configuring Continue or planning setup. LAN exposes Ollama to devices on the local network. Tailscale should use a private Tailscale hostname or `100.x.x.x` IP address.

## Design Principles

- Ask before changing device or IDE settings.
- Back up existing Continue configuration before writing a new one.
- Prefer inspectable scripts over invisible automation.
- Keep the Ollama server bound to safe defaults unless the user explicitly chooses LAN or private tunnel mode.
- Detect RAM, storage, CPU architecture, Android version, battery, and Termux readiness before model install.
- Treat low-memory phones as experimental/lightweight devices.
