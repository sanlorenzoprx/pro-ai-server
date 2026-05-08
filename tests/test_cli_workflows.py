from typer.testing import CliRunner

from pro_ai_server import cli
from pro_ai_server.continue_config import ContinueConfigWriteResult
from pro_ai_server.diagnostics import DiagnosticsReport
from pro_ai_server.ide import IdeCli, IdeExtensionStatus
from pro_ai_server.ollama import OllamaServerStatus
from pro_ai_server.release_validation import ReleaseValidationIssue, ReleaseValidationResult
from pro_ai_server.status import ProAiStatus, StatusItem
from pro_ai_server import web


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


def test_server_endpoints_prints_access_urls_without_checking():
    runner = CliRunner()

    result = runner.invoke(cli.app, ["server-endpoints", "--no-check"])

    assert result.exit_code == 0
    assert "Server endpoints" in result.output
    assert "Termux/Ollama" in result.output
    assert "URL: http://127.0.0.1:11434" in result.output
    assert "Generate: http://127.0.0.1:11434/api/generate" in result.output
    assert "Native Android llama.cpp (optional)" in result.output
    assert "URL: not configured" in result.output
    assert "--native-api-base" in result.output


def test_server_endpoints_checks_ollama_live_models_by_default(monkeypatch):
    runner = CliRunner()
    commands = []

    def fake_run_optional(command):
        commands.append(command)
        if command[-1].endswith("/api/tags"):
            return '{"models":[{"name":"qwen2.5-coder:0.5b"},{"name":"qwen2.5-coder:1.5b"}]}'
        return ""

    monkeypatch.setattr(cli, "run_optional_command", fake_run_optional)

    result = runner.invoke(cli.app, ["server-endpoints"])

    assert result.exit_code == 0
    assert "Status: ready" in result.output
    assert "qwen2.5-coder:0.5b" in result.output
    assert "qwen2.5-coder:1.5b" in result.output
    assert "URL: not configured" in result.output
    assert any(command[-1].endswith("/api/tags") for command in commands)
    assert not any(command[-1].endswith("/health") for command in commands)
    assert not any(command[-1].endswith("/v1/models") for command in commands)


def test_server_endpoints_checks_native_models_when_configured(monkeypatch):
    runner = CliRunner()
    commands = []

    def fake_run_optional(command):
        commands.append(command)
        if command[-1].endswith("/api/tags"):
            return '{"models":[]}'
        if command[-1].endswith("/health"):
            return '{"status":"ok"}'
        if command[-1].endswith("/v1/models"):
            return '{"data":[{"id":"qwen2.5-coder-0.5b-instruct-q4_k_m.gguf"}]}'
        return ""

    monkeypatch.setattr(cli, "run_optional_command", fake_run_optional)

    result = runner.invoke(cli.app, ["server-endpoints", "--native-api-base", "http://127.0.0.1:11435"])

    assert result.exit_code == 0
    assert "URL: http://127.0.0.1:11435" in result.output
    assert "Completion: http://127.0.0.1:11435/completion" in result.output
    assert "Status: ready" in result.output
    assert "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf" in result.output
    assert any(command[-1].endswith("/api/tags") for command in commands)
    assert any(command[-1].endswith("/health") for command in commands)
    assert any(command[-1].endswith("/v1/models") for command in commands)


def test_ui_command_launches_dashboard(monkeypatch):
    runner = CliRunner()
    calls = []

    def fake_serve_ui(host, port, open_browser):
        calls.append((host, port, open_browser))
        return "http://127.0.0.1:8765"

    monkeypatch.setattr(web, "serve_ui", fake_serve_ui)

    result = runner.invoke(cli.app, ["ui", "--no-open"])

    assert result.exit_code == 0
    assert calls == [("127.0.0.1", 8765, False)]


def test_doctor_reports_missing_continue_extension(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(cli, "resolve_adb", lambda: None)
    monkeypatch.setattr(cli.shutil, "which", lambda command: "C:/bin/python.exe" if command == "python" else None)
    monkeypatch.setattr(cli, "detect_ide_clis", lambda: (IdeCli(command="cursor", path="C:/bin/cursor.cmd"),))
    monkeypatch.setattr(
        cli,
        "detect_continue_extension_status",
        lambda ide: IdeExtensionStatus(
            ide=ide,
            extension_id="Continue.continue",
            installed=False,
        ),
    )

    result = runner.invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "IDE CLI found: cursor" in result.output
    assert "Continue extension not installed" in result.output
    assert "install-continue-extension --ide cursor" in result.output


def test_install_continue_extension_command_installs_selected_ide(monkeypatch):
    runner = CliRunner()
    ide = IdeCli(command="cursor", path="C:/bin/cursor.cmd")

    monkeypatch.setattr(cli, "installed_ide_clis", lambda: (ide,))
    monkeypatch.setattr(
        cli,
        "detect_continue_extension_status",
        lambda current_ide: IdeExtensionStatus(
            ide=current_ide,
            extension_id="Continue.continue",
            installed=False,
        ),
    )
    monkeypatch.setattr(
        cli,
        "install_continue_extension",
        lambda current_ide: IdeExtensionStatus(
            ide=current_ide,
            extension_id="Continue.continue",
            installed=True,
        ),
    )

    result = runner.invoke(cli.app, ["install-continue-extension", "--ide", "cursor"])

    assert result.exit_code == 0
    assert "Installing Continue extension in cursor" in result.output
    assert "Installed" in result.output


def test_configure_continue_warns_when_no_continue_ready_ide_is_detected(monkeypatch, tmp_path):
    runner = CliRunner()

    monkeypatch.setattr(
        cli,
        "write_continue_config",
        lambda plan, mode, host: ContinueConfigWriteResult(
            config_path=tmp_path / ".continue" / "config.yaml",
            backup_path=None,
            api_base="http://localhost:11434",
        ),
    )
    monkeypatch.setattr(cli, "installed_ide_clis", lambda: (IdeCli(command="cursor", path="C:/bin/cursor.cmd"),))
    monkeypatch.setattr(
        cli,
        "detect_continue_extension_status",
        lambda ide: IdeExtensionStatus(ide=ide, extension_id="Continue.continue", installed=False),
    )

    result = runner.invoke(cli.app, ["configure-continue", "--mode", "usb"])

    assert result.exit_code == 0
    assert "No supported IDE with the Continue extension was detected" in result.output


def test_status_prints_concise_readiness_report(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli, "run_optional_command", lambda command: "output")
    monkeypatch.setattr(cli, "assess_ollama_server_status", lambda output: OllamaServerStatus(ok=True))
    monkeypatch.setattr(cli, "detect_ide_clis", lambda: ())
    monkeypatch.setattr(
        cli,
        "build_status_report",
        lambda devices, reverse, ollama, ides, adb_path: ProAiStatus(
            items=(
                StatusItem("Phone", True, "connected (ABC123)"),
                StatusItem("Ollama", True, "responding on /api/tags (0 models)"),
            )
        ),
    )

    result = runner.invoke(cli.app, ["status"])

    assert result.exit_code == 0
    assert "Pro AI Server Status" in result.output
    assert "OK Phone: connected (ABC123)" in result.output
    assert "OK Ollama: responding on /api/tags" in result.output


def test_setup_tailscale_reports_already_installed_on_host_and_phone(monkeypatch):
    runner = CliRunner()

    def fake_run(command, capture_output, text):
        import subprocess

        outputs = {
            ("adb", "devices"): "List of devices attached\nABC123\tdevice\n",
            ("tailscale", "version"): "1.96.4",
            ("adb", "-s", "ABC123", "shell", "pm", "path", "com.tailscale.ipn"): (
                "package:/data/app/com.tailscale.ipn/base.apk"
            ),
        }
        return subprocess.CompletedProcess(command, 0, stdout=outputs[tuple(command)], stderr="")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["setup-tailscale"])

    assert result.exit_code == 0
    assert "Tailscale is available on this Windows host" in result.output
    assert "Tailscale is installed on Android device ABC123" in result.output


def test_setup_tailscale_installs_android_apk_with_yes(monkeypatch, tmp_path):
    runner = CliRunner()
    apk = tmp_path / "tailscale.apk"
    apk.write_text("apk", encoding="utf-8")
    commands = []

    def fake_run(command, capture_output, text):
        import subprocess

        commands.append(command)
        if command == ["adb", "devices"]:
            return subprocess.CompletedProcess(command, 0, stdout="List of devices attached\nABC123\tdevice\n", stderr="")
        if command == ["tailscale", "version"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="not found")
        if command == ["adb", "-s", "ABC123", "shell", "pm", "path", "com.tailscale.ipn"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="package not found")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["setup-tailscale", "--android-apk", str(apk), "--yes"])

    assert result.exit_code == 0
    assert ["adb", "-s", "ABC123", "install", "-r", str(apk)] in commands
    assert "Installed" in result.output


def test_setup_tailscale_refuses_android_apk_install_without_yes(monkeypatch, tmp_path):
    runner = CliRunner()
    apk = tmp_path / "tailscale.apk"
    apk.write_text("apk", encoding="utf-8")

    def fake_run(command, capture_output, text):
        import subprocess

        if command == ["adb", "devices"]:
            return subprocess.CompletedProcess(command, 0, stdout="List of devices attached\nABC123\tdevice\n", stderr="")
        if command == ["tailscale", "version"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="not found")
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="package not found")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["setup-tailscale", "--android-apk", str(apk)])

    assert result.exit_code == 1
    assert "without --yes" in result.output


def test_setup_tailscale_opens_play_store_when_phone_app_is_missing(monkeypatch):
    runner = CliRunner()
    commands = []

    def fake_run(command, capture_output, text):
        import subprocess

        commands.append(command)
        if command == ["adb", "devices"]:
            return subprocess.CompletedProcess(command, 0, stdout="List of devices attached\nABC123\tdevice\n", stderr="")
        if command == ["tailscale", "version"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="not found")
        if command == ["adb", "-s", "ABC123", "shell", "pm", "path", "com.tailscale.ipn"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="package not found")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["setup-tailscale"])

    assert result.exit_code == 0
    assert [
        "adb",
        "-s",
        "ABC123",
        "shell",
        "am",
        "start",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        "market://details?id=com.tailscale.ipn",
    ] in commands
    assert "Opened" in result.output
