from typer.testing import CliRunner

from pro_ai_server import cli
from pro_ai_server.diagnostics import DiagnosticsReport


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
