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
        "diagnose --output",
    ):
        assert command in readme

    assert "bundled adb" in readme
    assert "fastboot is not used" in readme
    assert "back up existing continue configuration" in readme
    assert "lan exposes ollama" in readme
    assert "tailscale" in readme and "--host" in readme


def test_cli_workflow_documents_windows_first_flow_and_safety_claims():
    workflow = read_doc("docs/CLI_WORKFLOW.md")

    for command in (
        "pro-ai-server doctor",
        "pro-ai-server validate-platform-tools",
        "pro-ai-server scan --serial",
        "pro-ai-server generate-scripts",
        "pro-ai-server push-scripts",
        "pro-ai-server configure-continue --mode usb",
        "pro-ai-server tunnel",
        "pro-ai-server setup",
        "pro-ai-server setup --execute --yes",
        "pro-ai-server diagnose --output",
    ):
        assert command in workflow

    for safety_claim in (
        "bundled adb",
        "fastboot is not used",
        "does not require `fastboot.exe`",
        "backs it up first",
        "termux:widget still requires manual installation",
        "lan mode exposes ollama",
        "tailscale mode should use a private tailscale hostname",
        "lan and tailscale require an explicit host",
        "127.0.0.1:11434",
        "adb reverse tcp:11434 tcp:11434",
    ):
        assert safety_claim in workflow
