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


def test_tunnel_reports_failure_when_adb_reverse_fails(monkeypatch):
    runner = CliRunner()

    def fake_run(command, capture_output, text):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="no devices/emulators found")

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(cli.app, ["tunnel"])

    assert result.exit_code == 1
    assert "ADB reverse tunnel failed" in result.output
    assert "no devices/emulators found" in result.output
    assert "ADB reverse tunnel requested" not in result.output
