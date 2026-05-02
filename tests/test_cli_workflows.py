from typer.testing import CliRunner

from pro_ai_server import cli
from pro_ai_server.diagnostics import DiagnosticsReport
from pro_ai_server.release_validation import ReleaseValidationIssue, ReleaseValidationResult


def test_setup_prints_plan_without_executing_actions():
    runner = CliRunner()

    result = runner.invoke(cli.app, ["setup", "--mode", "usb", "--no-continue", "--no-tunnel"])

    assert result.exit_code == 0
    assert "Setup plan" in result.output
    assert "Plan only" in result.output
    assert "Generated Termux files" not in result.output


def test_setup_execute_refuses_continue_config_without_yes():
    runner = CliRunner()

    result = runner.invoke(cli.app, ["setup", "--execute"])

    assert result.exit_code == 1
    assert "Refusing to execute without --yes" in result.output


def test_diagnose_writes_output_file(tmp_path, monkeypatch):
    runner = CliRunner()
    output_path = tmp_path / "diagnostics.txt"

    monkeypatch.setattr(cli, "resolve_adb", lambda: None)
    monkeypatch.setattr(cli, "build_diagnostics_report", lambda _: DiagnosticsReport(text="diagnostic text"))

    result = runner.invoke(cli.app, ["diagnose", "--output", str(output_path)])

    assert result.exit_code == 0
    assert output_path.read_text(encoding="utf-8") == "diagnostic text"
    assert "Wrote diagnostics report" in result.output


def test_validate_platform_tools_reports_missing_required_files(tmp_path):
    runner = CliRunner()

    result = runner.invoke(cli.app, ["validate-platform-tools", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "one or more" in result.output
    assert "layouts" in result.output
    assert "adb.exe" in result.output


def test_termux_check_reports_ready_phone(monkeypatch):
    runner = CliRunner()
    outputs = {
        ("adb", "devices"): "List of devices attached\nABC123\tdevice\n",
        ("adb", "-s", "ABC123", "shell", "pm", "path", "com.termux"): "package:/data/app/com.termux/base.apk",
        ("adb", "-s", "ABC123", "shell", "pm", "path", "com.termux.api"): (
            "package:/data/app/com.termux.api/base.apk"
        ),
        (
            "adb",
            "-s",
            "ABC123",
            "shell",
            "test",
            "-d",
            "/data/data/com.termux/files/home",
            "&&",
            "echo",
            "yes",
            "||",
            "echo",
            "no",
        ): "yes",
        ("adb", "-s", "ABC123", "shell", "dumpsys", "package", "com.termux"): "versionName=0.118.1",
    }

    def fake_run(command, capture_output, text):
        import subprocess

        return subprocess.CompletedProcess(command, 0, stdout=outputs[tuple(command)], stderr="")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["termux-check"])

    assert result.exit_code == 0
    assert "Device: ABC123" in result.output
    assert "Termux version: 0.118.1" in result.output
    assert "Termux:API installed" in result.output


def test_termux_check_exits_nonzero_when_api_is_missing(monkeypatch):
    runner = CliRunner()

    def fake_run(command, capture_output, text):
        import subprocess

        if command == ["adb", "devices"]:
            return subprocess.CompletedProcess(command, 0, stdout="List of devices attached\nABC123\tdevice\n", stderr="")
        if command[-1] == "com.termux.api":
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="")
        if command[-1] == "com.termux":
            return subprocess.CompletedProcess(command, 0, stdout="package:/data/app/com.termux/base.apk", stderr="")
        if command[-4:] == ["||", "echo", "no"]:
            return subprocess.CompletedProcess(command, 0, stdout="yes", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["termux-check"])

    assert result.exit_code == 1
    assert "Termux:API is not installed" in result.output


def test_validate_release_reports_issues(monkeypatch, tmp_path):
    runner = CliRunner()

    monkeypatch.setattr(
        cli,
        "validate_release_layout",
        lambda _: ReleaseValidationResult(
            issues=(
                ReleaseValidationIssue(
                    code="missing-ci-workflow",
                    message="Missing GitHub Actions workflow.",
                    path=tmp_path / ".github" / "workflows" / "ci.yml",
                ),
            )
        ),
    )

    result = runner.invoke(cli.app, ["validate-release", "--root", str(tmp_path)])

    assert result.exit_code == 1
    assert "Release validation failed" in result.output
    assert "missing-ci-workflow" in result.output


def test_server_check_reports_missing_models(monkeypatch):
    runner = CliRunner()

    def fake_run(command, capture_output, text):
        import subprocess

        assert command == ["curl", "--silent", "--show-error", "http://localhost:11434/api/tags"]
        return subprocess.CompletedProcess(command, 0, stdout='{"models":[{"name":"qwen2.5-coder:3b"}]}', stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["server-check", "--profile", "professional"])

    assert result.exit_code == 1
    assert "qwen2.5-coder:3b" in result.output
    assert "qwen2.5-coder:1.5b-base" in result.output
    assert "ollama pull qwen2.5-coder:1.5b-base" in result.output


def test_server_check_accepts_custom_api_base(monkeypatch):
    runner = CliRunner()

    def fake_run(command, capture_output, text):
        import subprocess

        assert command == ["curl", "--silent", "--show-error", "http://pro-ai-phone:11434/api/tags"]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"models":[{"name":"qwen2.5-coder:3b"},{"name":"qwen2.5-coder:1.5b-base"}]}',
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["server-check", "--api-base", "http://pro-ai-phone:11434"])

    assert result.exit_code == 0
    assert "Ollama API: http://pro-ai-phone:11434" in result.output
