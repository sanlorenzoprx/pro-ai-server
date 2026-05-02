from pro_ai_server.packaging import (
    PACKAGED_WINDOWS_PLATFORM_TOOLS,
    REQUIRED_WINDOWS_PLATFORM_TOOL_FILES,
    SOURCE_TREE_WINDOWS_PLATFORM_TOOLS,
    validate_windows_platform_tools_dir,
    validate_windows_platform_tools_layouts,
)


def touch_files(directory, file_names):
    directory.mkdir(parents=True, exist_ok=True)
    for file_name in file_names:
        (directory / file_name).write_text("", encoding="utf-8")


def test_windows_platform_tools_validation_accepts_required_files(tmp_path):
    touch_files(tmp_path, REQUIRED_WINDOWS_PLATFORM_TOOL_FILES)

    result = validate_windows_platform_tools_dir(tmp_path)

    assert result.ok is True
    assert result.present_files == REQUIRED_WINDOWS_PLATFORM_TOOL_FILES
    assert result.missing_files == ()
    assert "ADB runtime is ready" in result.message
    assert "adb.exe" in result.message
    assert "AdbWinApi.dll" in result.message
    assert "AdbWinUsbApi.dll" in result.message


def test_windows_platform_tools_validation_reports_missing_files(tmp_path):
    touch_files(tmp_path, ("adb.exe",))

    result = validate_windows_platform_tools_dir(tmp_path)

    assert result.ok is False
    assert result.present_files == ("adb.exe",)
    assert result.missing_files == ("AdbWinApi.dll", "AdbWinUsbApi.dll")
    assert "ADB runtime is incomplete" in result.message
    assert "missing AdbWinApi.dll and AdbWinUsbApi.dll" in result.message


def test_windows_platform_tools_validation_does_not_require_fastboot(tmp_path):
    touch_files(tmp_path, REQUIRED_WINDOWS_PLATFORM_TOOL_FILES + ("fastboot.exe",))

    result = validate_windows_platform_tools_dir(tmp_path)

    assert result.ok is True
    assert "fastboot" not in result.present_files
    assert "fastboot" not in result.missing_files
    assert "fastboot" not in result.message.lower()


def test_windows_platform_tools_layout_validation_checks_source_and_packaged_layouts(tmp_path):
    touch_files(tmp_path / SOURCE_TREE_WINDOWS_PLATFORM_TOOLS, REQUIRED_WINDOWS_PLATFORM_TOOL_FILES)
    touch_files(tmp_path / PACKAGED_WINDOWS_PLATFORM_TOOLS, ("adb.exe",))

    result = validate_windows_platform_tools_layouts(tmp_path)

    assert result.ok is False
    assert result.source_tree.ok is True
    assert result.packaged.ok is False
    assert result.packaged.missing_files == ("AdbWinApi.dll", "AdbWinUsbApi.dll")
    assert "one or more layouts" in result.message


def test_windows_platform_tools_layout_validation_message_when_both_layouts_are_valid(tmp_path):
    touch_files(tmp_path / SOURCE_TREE_WINDOWS_PLATFORM_TOOLS, REQUIRED_WINDOWS_PLATFORM_TOOL_FILES)
    touch_files(tmp_path / PACKAGED_WINDOWS_PLATFORM_TOOLS, REQUIRED_WINDOWS_PLATFORM_TOOL_FILES)

    result = validate_windows_platform_tools_layouts(tmp_path)

    assert result.ok is True
    assert "both layouts" in result.message
