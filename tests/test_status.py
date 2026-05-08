from pro_ai_server.ide import IdeCli, IdeExtensionStatus
from pro_ai_server.ollama import OllamaServerStatus
from pro_ai_server.status import build_status_report, render_status_report


def test_status_report_marks_ready_phone_tunnel_server_and_ide():
    report = build_status_report(
        "List of devices attached\nABC123\tdevice\n",
        "ABC123 tcp:11434 tcp:11434\n",
        OllamaServerStatus(ok=True, model_names=("qwen2.5-coder:3b",)),
        (
            IdeExtensionStatus(
                ide=IdeCli(command="cursor", path="C:/bin/cursor.cmd"),
                extension_id="Continue.continue",
                installed=True,
            ),
        ),
        adb_path="adb",
    )

    rendered = "\n".join(render_status_report(report))

    assert report.ok
    assert "OK Phone: connected (ABC123)" in rendered
    assert "OK USB tunnel: adb forward tcp:11434 is active" in rendered
    assert "OK Ollama: responding on /api/tags (1 model)" in rendered
    assert "OK IDE: Continue ready in cursor" in rendered


def test_status_report_marks_missing_pieces():
    report = build_status_report(
        "",
        "",
        OllamaServerStatus(ok=False, warnings=("Ollama did not return a response.",)),
        (
            IdeExtensionStatus(
                ide=IdeCli(command="cursor", path="C:/bin/cursor.cmd"),
                extension_id="Continue.continue",
                installed=False,
            ),
        ),
        adb_path="adb",
    )

    rendered = "\n".join(render_status_report(report))

    assert not report.ok
    assert "Needs attention Phone: No ADB devices found" in rendered
    assert "Needs attention USB tunnel: adb forward tcp:11434 is not active" in rendered
    assert "Needs attention Ollama: Ollama did not return a response." in rendered
    assert "Needs attention IDE: Continue extension missing in cursor" in rendered
