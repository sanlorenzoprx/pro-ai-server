# DroidShield

Run autonomous AI agents safely on isolated Android sandbox nodes.

DroidShield turns inexpensive Android phones into disposable execution workers
for AI coding agents. The product is the containment layer: gateway, policy
engine, monitoring, kill switch path, and Android node runtime.

## Why This Exists

AI agents can run shell commands, edit repositories, install dependencies, use
MCP tools, and touch credentials. DroidShield puts those actions behind a
policy-enforced gateway and routes approved work to physically separate Android
devices instead of exposing a real workstation or cloud host.

## MVP Architecture

```text
AI Agent / MCP Client
        |
        v
DroidShield Gateway
        |
        v
Policy Engine -> Audit Log -> Dashboard / Alerts
        |
        v
Android Sandbox Node
        |
        v
Restricted Tool Runtime
```

## Current Surface

- Gateway task contracts and receipts.
- Command policy allow/block checks.
- Android sandbox node capability model.
- Append-only JSONL audit log.
- Agentic development loop contract.
- Existing ADB, Termux, USB tunnel, diagnostics, and desktop dashboard baseline
  inherited from the strongest DroidShield iteration.

## Windows Quickstart

```powershell
cd "C:\repos\DroidShield"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]

droidshield architecture
droidshield init-policy
droidshield policy-check "git status"
droidshield sandbox-run "git status" --agent cursor --objective "Inspect repo state"
droidshield agentic-plan "Run quality checks" -c "ruff check ." -c "pytest"
droidshield gateway-api
```

Android setup commands from the inherited baseline are still available:

```powershell
droidshield doctor
droidshield validate-platform-tools
droidshield scan --serial <device>
droidshield generate-scripts --mode usb
droidshield push-scripts --serial <device>
droidshield configure-continue --mode usb
droidshield tunnel
droidshield setup --execute --yes
droidshield setup-tailscale
droidshield setup-tailscale --install-host --yes
droidshield setup-tailscale --android-apk <path> --yes
droidshield server-endpoints
droidshield status
droidshield diagnose --output diagnostics.txt
droidshield ui
```

The gateway API starts on `http://127.0.0.1:8770` by default and exposes the
MVP agent contract:

```text
POST /api/v1/nodes/register
POST /api/v1/tasks
GET  /api/v1/tasks/{job_id}
POST /api/v1/jobs/{job_id}/kill
```

The MVP prefers bundled ADB from `embedded-tools/windows/platform-tools/adb.exe`
and then falls back to system `adb` on `PATH`. Fastboot is not used. Continue
integration writes `%USERPROFILE%\.continue\config.yaml` and will back up existing Continue configuration before
replacing it.

Cursor integration is supported through the Continue extension. LAN exposes Ollama to devices on the local network, so
LAN and Tailscale require `--host`.
Tailscale should use a private Tailscale hostname or `100.x.x.x` address.

## Project Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [CLI Workflow](docs/CLI_WORKFLOW.md)

## Product Positioning

DroidShield is disposable Android sandbox infrastructure for autonomous AI
agents. Android phones are the worker nodes. Safety, containment, policy, and
auditability are the product.
