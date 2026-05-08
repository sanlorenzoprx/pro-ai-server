from pro_ai_server import web
from pro_ai_server.ide import IdeCli, IdeExtensionStatus


def test_build_status_payload_reports_readiness(monkeypatch):
    monkeypatch.setattr(web, "detect_ide_clis", lambda: (IdeCli(command="cursor", path="C:/bin/cursor.cmd"),))
    monkeypatch.setattr(
        web,
        "detect_continue_extension_status",
        lambda ide: IdeExtensionStatus(ide=ide, extension_id="Continue.continue", installed=True),
    )

    from pro_ai_server import cli

    def fake_run_optional(command):
        if command[-1] == "devices":
            return "List of devices attached\nABC123\tdevice\n"
        if command[-1] == "--list":
            return "ABC123 tcp:11434 tcp:11434\n"
        if command[-1].endswith("/api/tags"):
            return '{"models":[{"name":"qwen2.5-coder:1.5b"}]}'
        return ""

    monkeypatch.setattr(cli, "resolve_adb", lambda: "adb")
    monkeypatch.setattr(cli, "run_optional_command", fake_run_optional)

    payload = web.build_status_payload()

    assert payload["ok"] is True
    assert payload["models"] == ["qwen2.5-coder:1.5b"]
    assert payload["items"][0]["label"] == "Phone"
    assert payload["items"][0]["ok"] is True


def test_build_endpoints_payload_keeps_native_optional(monkeypatch):
    from pro_ai_server import cli

    commands = []

    def fake_run_optional(command):
        commands.append(command)
        if command[-1].endswith("/api/tags"):
            return '{"models":[]}'
        return ""

    monkeypatch.setattr(cli, "run_optional_command", fake_run_optional)

    payload = web.build_endpoints_payload()

    assert payload["ollama"]["base"] == "http://127.0.0.1:11434"
    assert payload["native"] is None
    assert any(command[-1].endswith("/api/tags") for command in commands)
    assert not any(command[-1].endswith("/health") for command in commands)


def test_generate_scripts_action_returns_written_paths(tmp_path):
    result = web.generate_scripts_action("usb", "lightweight", str(tmp_path))

    assert result.ok is True
    assert "Generated" in result.message
    assert (tmp_path / "generated" / "termux" / "start-pro-ai-server.sh").exists()
