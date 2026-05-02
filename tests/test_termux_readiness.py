from pro_ai_server.termux_readiness import (
    TERMUX_API_PACKAGE,
    TERMUX_HOME,
    TERMUX_PACKAGE,
    assess_termux_readiness,
    build_termux_package_info_command,
    build_termux_readiness_commands,
)


def test_assesses_all_ok_with_version_hint():
    result = assess_termux_readiness(
        "package:/data/app/~~abc/com.termux/base.apk\n",
        "package:/data/app/~~abc/com.termux.api/base.apk\n",
        "yes\n",
        "Package [com.termux]\n  versionName=0.118.1\n",
    )

    assert result.ok is True
    assert result.version_hint == "0.118.1"
    assert result.warnings == ()
    assert result.instructions == ()
    assert [check.name for check in result.checks] == [
        "Termux installed",
        "Termux:API installed",
        "Termux home initialized",
    ]


def test_missing_termux_instructs_fdroid_or_github_install():
    result = assess_termux_readiness("", "package:/data/app/com.termux.api/base.apk\n", "yes\n")

    assert result.ok is False
    assert result.termux_installed.ok is False
    assert "F-Droid or GitHub" in result.termux_installed.instruction
    assert "Play Store" not in " ".join(result.instructions)


def test_missing_termux_api_instructs_install_and_bootstrap_afterward():
    result = assess_termux_readiness("package:/data/app/com.termux/base.apk\n", "", "yes\n")

    assert result.ok is False
    assert result.termux_api_installed.ok is False
    assert "Install Termux:API" in result.termux_api_installed.instruction
    assert "bootstrap script afterward" in result.termux_api_installed.instruction


def test_home_not_initialized_instructs_opening_termux_once():
    result = assess_termux_readiness(
        "package:/data/app/com.termux/base.apk\n",
        "package:/data/app/com.termux.api/base.apk\n",
        "no\n",
    )

    assert result.ok is False
    assert result.home_initialized.ok is False
    assert "Open Termux once on the phone" in result.home_initialized.instruction


def test_builds_readiness_commands_without_serial():
    assert build_termux_readiness_commands() == (
        ("adb", "shell", "pm", "path", TERMUX_PACKAGE),
        ("adb", "shell", "pm", "path", TERMUX_API_PACKAGE),
        ("adb", "shell", "test", "-d", TERMUX_HOME, "&&", "echo", "yes", "||", "echo", "no"),
    )
    assert build_termux_package_info_command() == ("adb", "shell", "dumpsys", "package", TERMUX_PACKAGE)


def test_builds_readiness_commands_with_serial():
    assert build_termux_readiness_commands(serial="ABC123") == (
        ("adb", "-s", "ABC123", "shell", "pm", "path", TERMUX_PACKAGE),
        ("adb", "-s", "ABC123", "shell", "pm", "path", TERMUX_API_PACKAGE),
        ("adb", "-s", "ABC123", "shell", "test", "-d", TERMUX_HOME, "&&", "echo", "yes", "||", "echo", "no"),
    )
    assert build_termux_package_info_command(serial="ABC123") == (
        "adb",
        "-s",
        "ABC123",
        "shell",
        "dumpsys",
        "package",
        TERMUX_PACKAGE,
    )
