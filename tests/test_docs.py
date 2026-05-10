from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_doc(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8").lower()


def test_readme_documents_current_mvp_cli_commands_and_bundled_adb_policy():
    readme = read_doc("README.md")

    for command in (
        "doctor",
        "validate-platform-tools",
        "scan --serial",
        "generate-scripts",
        "push-scripts",
        "configure-continue --mode usb",
        "tunnel",
        "setup --execute --yes",
        "setup-tailscale",
        "server-endpoints",
        "status",
        "diagnose --output",
        "ui",
    ):
        assert command in readme

    assert "bundled adb" in readme
    assert "fastboot is not used" in readme
    assert "back up existing continue configuration" in readme
    assert "cursor integration is supported through the continue extension" in readme
    assert "%userprofile%\\.continue\\config.yaml" in readme
    assert "lan exposes ollama" in readme
    assert "tailscale" in readme and "--host" in readme
    assert "--install-host --yes" in readme
    assert "--android-apk <path> --yes" in readme


def test_cli_workflow_documents_windows_first_flow_and_safety_claims():
    workflow = read_doc("docs/CLI_WORKFLOW.md")

    for command in (
        "droidshield doctor",
        "droidshield validate-platform-tools",
        "droidshield validate-release",
        "droidshield scan --serial",
        "droidshield termux-check",
        "droidshield generate-scripts",
        "droidshield push-scripts",
        "droidshield configure-continue --mode usb",
        "droidshield setup-tailscale",
        "droidshield server-endpoints",
        "droidshield status",
        "droidshield ui",
        "droidshield tunnel",
        "droidshield setup",
        "droidshield setup --execute --yes",
        "droidshield diagnose --output",
    ):
        assert command in workflow

    for safety_claim in (
        "bundled adb",
        "fastboot is not used",
        "does not require `fastboot.exe`",
        "no fastboot",
        "includes cursor",
        "no separate cursor-specific config file is required",
        "backs it up first",
        "termux:widget still requires manual installation",
        "lan mode exposes ollama",
        "tailscale mode should use a private tailscale hostname",
        "lan and tailscale require an explicit host",
        "com.tailscale.ipn",
        "winget",
        "--android-apk",
        "concise readiness view",
        "127.0.0.1:11434",
        "adb forward tcp:11434 tcp:11434",
    ):
        assert safety_claim in workflow


def test_troubleshooting_documents_phone_setup_and_mvp_failure_modes():
    troubleshooting = read_doc("docs/TROUBLESHOOTING.md")

    for expected in (
        "no device found",
        "unauthorized",
        "multiple devices require --serial",
        "droidshield termux-check",
        "termux is missing",
        "termux:api is missing",
        "termux home is not initialized",
        "ollama not responding on localhost:11434",
        "missing models",
        "continue backup",
        "lan mode exposes ollama",
        "tailscale hostname",
        "100.x.x.x",
        "bundled adb",
        "android studio",
        "droidshield validate-platform-tools",
        "droidshield validate-release",
        "no fastboot",
        "--serial",
        "termux:widget manual placement",
    ):
        assert expected in troubleshooting


def test_release_doc_documents_windows_first_release_gates_and_smoke_flow():
    release = read_doc("docs/RELEASE.md")

    for expected in (
        "droidshield validate-release",
        "droidshield validate-platform-tools",
        "pytest",
        "ruff check .",
        "droidshield doctor",
        "bundled adb",
        "fastboot is not used",
        "fastboot.exe",
        "scripts/download-platform-tools.ps1",
        "android studio",
        "droidshield generate-scripts",
        "droidshield setup",
        "droidshield diagnose --output",
    ):
        assert expected in release


def test_ci_runs_release_validation_and_core_build_gates():
    ci = read_doc(".github/workflows/ci.yml")

    for expected in (
        "python -m pip install -e \".[dev]\"",
        "ruff check .",
        "pytest",
        "droidshield validate-release",
        "python -m pip wheel . --no-deps --wheel-dir dist",
    ):
        assert expected in ci
