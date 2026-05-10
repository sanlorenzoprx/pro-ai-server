from droidshield import web
from droidshield.ide import IdeCli, IdeExtensionStatus


def test_build_status_payload_reports_readiness(monkeypatch):
    monkeypatch.setattr(web, "detect_ide_clis", lambda: (IdeCli(command="cursor", path="C:/bin/cursor.cmd"),))
    monkeypatch.setattr(
        web,
        "detect_continue_extension_status",
        lambda ide: IdeExtensionStatus(ide=ide, extension_id="Continue.continue", installed=True),
    )

    from droidshield import cli

    def fake_run_optional(command):
        if command[-1] == "devices":
            return "List of devices attached\nABC123\tdevice\n"
        if command[-1] == "--list":
            return "ABC123 tcp:11434 tcp:11434\nABC123 tcp:8766 tcp:8766\n"
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
    from droidshield import cli

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
    assert (tmp_path / "generated" / "termux" / "start-droidshield.sh").exists()
    assert (tmp_path / "generated" / "termux" / "pro-ai-knowledge-server.py").exists()


def test_build_knowledge_payload_reports_unreachable_phone_server(monkeypatch):
    def fake_request(url, *, method="GET", body=None):
        raise OSError("connection refused")

    monkeypatch.setattr(web, "_request_phone_knowledge_json", fake_request)

    payload = web.build_knowledge_payload()

    assert payload["ok"] is False
    assert payload["hostedOn"] == "phone"
    assert "not reachable" in payload["message"]


def test_add_phone_knowledge_source_posts_markdown_to_phone(monkeypatch):
    calls = []

    def fake_request(url, *, method="GET", body=None):
        calls.append((url, method, body))
        return {"ok": True, "path": "raw/note.md"}

    monkeypatch.setattr(web, "_request_phone_knowledge_json", fake_request)

    payload = web.add_phone_knowledge_source("note.md", "# Note")

    assert payload["ok"] is True
    assert calls == [
        (
            "http://127.0.0.1:8766/api/knowledge/sources",
            "POST",
            {"filename": "note.md", "content": "# Note", "ingest": True},
        )
    ]


def test_add_phone_knowledge_source_rejects_non_markdown_file():
    payload = web.add_phone_knowledge_source("note.txt", "text")

    assert payload["ok"] is False
    assert ".md" in payload["message"]


def test_add_phone_quick_capture_posts_to_phone(monkeypatch):
    calls = []

    def fake_request(url, *, method="GET", body=None):
        calls.append((url, method, body))
        return {"ok": True, "path": "inbox/quick-capture.md"}

    monkeypatch.setattr(web, "_request_phone_knowledge_json", fake_request)

    payload = web.add_phone_quick_capture("remember this")

    assert payload["ok"] is True
    assert calls == [
        (
            "http://127.0.0.1:8766/api/knowledge/captures",
            "POST",
            {"content": "remember this"},
        )
    ]


def test_trigger_phone_knowledge_feedback_posts_known_kind(monkeypatch):
    calls = []

    def fake_request(url, *, method="GET", body=None):
        calls.append((url, method, body))
        return {"ok": True, "page": "wiki/daily/2026-05-08.md"}

    monkeypatch.setattr(web, "_request_phone_knowledge_json", fake_request)

    payload = web.trigger_phone_knowledge_feedback("daily")

    assert payload["ok"] is True
    assert calls == [("http://127.0.0.1:8766/api/knowledge/daily", "POST", None)]


def test_read_phone_knowledge_page_gets_encoded_markdown_page(monkeypatch):
    calls = []

    def fake_request(url, *, method="GET", body=None):
        calls.append((url, method, body))
        return {"ok": True, "path": "wiki/daily/2026-05-08.md", "content": "# Daily"}

    monkeypatch.setattr(web, "_request_phone_knowledge_json", fake_request)

    payload = web.read_phone_knowledge_page("wiki/daily/2026-05-08.md")

    assert payload["ok"] is True
    assert calls == [
        ("http://127.0.0.1:8766/api/knowledge/pages?path=wiki%2Fdaily%2F2026-05-08.md", "GET", None)
    ]
