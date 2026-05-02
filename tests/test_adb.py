import subprocess

from typer.testing import CliRunner

from pro_ai_server import cli


def test_resolve_adb_prefers_packaged_bundled_adb(tmp_path, monkeypatch):
    package_dir = tmp_path / "site-packages" / "pro_ai_server"
    adb_path = package_dir / "embedded-tools" / "windows" / "platform-tools" / "adb.exe"
    adb_path.parent.mkdir(parents=True)
    adb_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(cli, "__file__", str(package_dir / "cli.py"))
    monkeypatch.setattr(cli.shutil, "which", lambda _: "system-adb")

    assert cli.resolve_adb() == str(adb_path)


def test_resolve_adb_falls_back_to_source_tree_bundled_adb(tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo"
    module_path = repo_dir / "src" / "pro_ai_server" / "cli.py"
    adb_path = repo_dir / "embedded-tools" / "windows" / "platform-tools" / "adb.exe"
    module_path.parent.mkdir(parents=True)
    adb_path.parent.mkdir(parents=True)
    adb_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(cli, "__file__", str(module_path))
    monkeypatch.setattr(cli.shutil, "which", lambda _: "system-adb")

    assert cli.resolve_adb() == str(adb_path)


def test_resolve_adb_falls_back_to_system_adb(tmp_path, monkeypatch):
    package_dir = tmp_path / "site-packages" / "pro_ai_server"
    package_dir.mkdir(parents=True)

    monkeypatch.setattr(cli, "__file__", str(package_dir / "cli.py"))
    monkeypatch.setattr(cli.shutil, "which", lambda command: "system-adb" if command == "adb" else None)

    assert cli.resolve_adb() == "system-adb"


def test_resolve_adb_returns_none_when_bundled_and_system_adb_are_missing(tmp_path, monkeypatch):
    package_dir = tmp_path / "site-packages" / "pro_ai_server"
    package_dir.mkdir(parents=True)

    monkeypatch.setattr(cli, "__file__", str(package_dir / "cli.py"))
    monkeypatch.setattr(cli.shutil, "which", lambda _: None)

    assert cli.resolve_adb() is None


def test_cli_behavior_does_not_reference_fastboot():
    assert "fastboot" not in cli.Path(cli.__file__).read_text(encoding="utf-8")


def test_tunnel_reports_failure_when_adb_reverse_fails(monkeypatch):
    runner = CliRunner()

    def fake_run(command, capture_output, text):
        if command == ["adb", "devices"]:
            return subprocess.CompletedProcess(command, 0, stdout="List of devices attached\nABC123\tdevice\n", stderr="")
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="no devices/emulators found")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["tunnel"])

    assert result.exit_code == 1
    assert "ADB reverse tunnel failed" in result.output
    assert "no devices/emulators found" in result.output
    assert "ADB reverse tunnel requested" not in result.output


def test_tunnel_uses_requested_serial(monkeypatch):
    runner = CliRunner()
    commands = []

    def fake_run(command, capture_output, text):
        commands.append(command)
        if command == ["adb", "devices"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="List of devices attached\nABC123\tdevice\nDEF456\tdevice\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["tunnel", "--serial", "DEF456"])

    assert result.exit_code == 0
    assert ["adb", "-s", "DEF456", "reverse", "tcp:11434", "tcp:11434"] in commands


def test_tunnel_requires_serial_when_multiple_devices_are_connected(monkeypatch):
    runner = CliRunner()

    def fake_run(command, capture_output, text):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="List of devices attached\nABC123\tdevice\nDEF456\tdevice\n",
            stderr="",
        )

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["tunnel"])

    assert result.exit_code == 1
    assert "Multiple authorized ADB devices found" in result.output


def test_push_scripts_executes_delivery_plan_with_selected_serial(monkeypatch, tmp_path):
    runner = CliRunner()
    commands = []

    def fake_run(command, capture_output, text):
        commands.append(command)
        if command == ["adb", "devices"]:
            return subprocess.CompletedProcess(command, 0, stdout="List of devices attached\nABC123\tdevice\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["push-scripts", "--generated-termux-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert ["adb", "-s", "ABC123", "shell", "mkdir", "-p", "/data/data/com.termux/files/home/.shortcuts"] in commands
    assert ["adb", "-s", "ABC123", "push", str(tmp_path / "bootstrap.sh"), "/data/data/com.termux/files/home/bootstrap.sh"] in commands
    assert ["adb", "-s", "ABC123", "shell", "chmod", "+x", "/data/data/com.termux/files/home/bootstrap.sh"] in commands
    assert "~/bootstrap.sh" in result.output
