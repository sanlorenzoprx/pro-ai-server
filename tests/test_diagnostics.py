from pro_ai_server.diagnostics import build_diagnostics_report, redact_sensitive_paths


def test_diagnostics_report_includes_host_phone_and_server_sections():
    outputs = {
        ("C:\\Users\\Hector\\tools\\adb.exe", "devices"): "List of devices attached\nABC123\tdevice",
        (
            "C:\\Users\\Hector\\tools\\adb.exe",
            "shell",
            "getprop",
            "ro.product.manufacturer",
        ): "Google",
        ("C:\\Users\\Hector\\tools\\adb.exe", "shell", "getprop", "ro.product.model"): "Pixel 6",
        (
            "C:\\Users\\Hector\\tools\\adb.exe",
            "shell",
            "getprop",
            "ro.build.version.release",
        ): "15",
        ("C:\\Users\\Hector\\tools\\adb.exe", "shell", "getprop", "ro.product.cpu.abi"): "arm64-v8a",
        ("C:\\Users\\Hector\\tools\\adb.exe", "shell", "cat", "/proc/meminfo"): "MemTotal: 8023456 kB",
        ("C:\\Users\\Hector\\tools\\adb.exe", "shell", "df", "-k", "/data"): "/data 100 40 60",
        ("C:\\Users\\Hector\\tools\\adb.exe", "shell", "dumpsys", "battery"): "level: 88\nAC powered: true",
        ("C:\\Users\\Hector\\tools\\adb.exe", "reverse", "--list"): "ABC123 tcp:11434 tcp:11434",
        ("curl", "--silent", "--show-error", "http://localhost:11434/api/tags"): '{"models":[]}',
    }

    def runner(command):
        return outputs[tuple(command)]

    report = build_diagnostics_report(
        adb_path="C:\\Users\\Hector\\tools\\adb.exe",
        command_runner=runner,
        which=lambda command: f"C:\\Users\\Hector\\bin\\{command}.exe" if command == "code" else None,
    ).text

    assert "## Host" in report
    assert "## Phone" in report
    assert "## Server" in report
    assert "ADB path: %USERPROFILE%\\tools\\adb.exe" in report
    assert "- code: %USERPROFILE%\\bin\\code.exe" in report
    assert "- cursor: not found" in report
    assert "Google" in report
    assert "Pixel 6" in report
    assert "arm64-v8a" in report
    assert "ABC123 tcp:11434 tcp:11434" in report
    assert '{"models":[]}' in report
    assert "C:\\Users\\Hector" not in report


def test_diagnostics_report_handles_no_phone_connected():
    def runner(command):
        if command[-1] == "devices":
            return "List of devices attached\n"
        if command[:2] == ["adb", "reverse"]:
            return ""
        return '{"models":[]}'

    report = build_diagnostics_report(adb_path="adb", command_runner=runner, which=lambda _: None).text

    assert "No phone connected or authorized." in report
    assert "adb reverse --list:" in report


def test_diagnostics_report_handles_ollama_not_responding():
    def runner(command):
        if command == ["adb", "devices"]:
            return "List of devices attached\nABC123\tdevice"
        if command == ["curl", "--silent", "--show-error", "http://localhost:11434/api/tags"]:
            raise RuntimeError("Connection refused")
        return ""

    report = build_diagnostics_report(adb_path="adb", command_runner=runner, which=lambda _: None).text

    assert "Ollama tags:" in report
    assert "ERROR: Connection refused" in report


def test_diagnostics_report_handles_missing_adb_path():
    report = build_diagnostics_report(adb_path=None, command_runner=lambda _: "curl unavailable", which=lambda _: None).text

    assert "ADB path: not found" in report
    assert "No ADB path available" in report


def test_redact_sensitive_paths():
    assert redact_sensitive_paths("C:\\Users\\Ada\\tools\\adb.exe") == "%USERPROFILE%\\tools\\adb.exe"
