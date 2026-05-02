import pytest

from pro_ai_server.device_scan import (
    DeviceScanOutputs,
    build_device_profile_from_scan_outputs,
    build_device_scan_commands,
    build_device_scan_summary_lines,
)


def test_build_device_scan_commands_without_serial():
    commands = build_device_scan_commands("adb")

    assert commands.meminfo == ("adb", "shell", "cat", "/proc/meminfo")
    assert commands.storage == ("adb", "shell", "df", "-k", "/data")
    assert commands.abi == ("adb", "shell", "getprop", "ro.product.cpu.abi")
    assert commands.android_version == ("adb", "shell", "getprop", "ro.build.version.release")
    assert commands.manufacturer == ("adb", "shell", "getprop", "ro.product.manufacturer")
    assert commands.model == ("adb", "shell", "getprop", "ro.product.model")
    assert commands.battery == ("adb", "shell", "dumpsys", "battery")


def test_build_device_scan_commands_with_serial():
    commands = build_device_scan_commands("adb", "ABC123")

    assert commands.meminfo == ("adb", "-s", "ABC123", "shell", "cat", "/proc/meminfo")
    assert commands.storage == ("adb", "-s", "ABC123", "shell", "df", "-k", "/data")
    assert commands.abi == ("adb", "-s", "ABC123", "shell", "getprop", "ro.product.cpu.abi")
    assert commands.android_version == (
        "adb",
        "-s",
        "ABC123",
        "shell",
        "getprop",
        "ro.build.version.release",
    )
    assert commands.manufacturer == (
        "adb",
        "-s",
        "ABC123",
        "shell",
        "getprop",
        "ro.product.manufacturer",
    )
    assert commands.model == ("adb", "-s", "ABC123", "shell", "getprop", "ro.product.model")
    assert commands.battery == ("adb", "-s", "ABC123", "shell", "dumpsys", "battery")


def test_build_device_profile_from_scan_outputs_uses_existing_hardware_assessment():
    profile = build_device_profile_from_scan_outputs(
        "ABC123",
        DeviceScanOutputs(
            meminfo="MemTotal: 6291456 kB",
            storage="Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/dm-2 100 1 7340032 1% /data",
            abi="arm64-v8a\n",
            android_version="15\n",
            manufacturer="Google\n",
            model="Pixel Test\n",
            battery="level: 55\ntemperature: 300\nplugged: 0\nstatus: 3",
        ),
    )

    assert profile.serial == "ABC123"
    assert profile.manufacturer == "Google"
    assert profile.model == "Pixel Test"
    assert profile.android_version == "15"
    assert profile.abi == "arm64-v8a"
    assert profile.ram_gb == 6
    assert profile.free_storage_gb == 7
    assert profile.battery_level == 55
    assert profile.battery_temperature_c == 30
    assert profile.is_charging is False
    assert profile.recommended_profile is not None
    assert profile.recommended_profile.name == "professional"
    assert profile.warnings == ("Free storage is under 8 GB; warn before downloading models.",)


def test_build_device_scan_summary_lines_include_model_recommendation_and_warnings():
    profile = build_device_profile_from_scan_outputs(
        "ABC123",
        DeviceScanOutputs(
            meminfo="MemTotal: 4194304 kB",
            storage="Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/dm-2 100 1 3145728 1% /data",
            abi="armeabi-v7a",
            android_version="12",
            manufacturer="Acme",
            model="Small Phone",
            battery="level: 87\ntemperature: 317\nplugged: 1\nstatus: 2",
        ),
    )

    lines = build_device_scan_summary_lines(profile)

    assert "Serial: ABC123" in lines
    assert "Device: Acme Small Phone" in lines
    assert "Recommended profile: lightweight (experimental)" in lines
    assert "Chat model: qwen2.5-coder:1.5b" in lines
    assert "Autocomplete model: qwen2.5-coder:0.5b" in lines
    assert "Warning: Free storage is under 4 GB; block full install and use lightweight mode or manual cleanup." in lines
    assert "Warning: Non-arm64 ABI detected; 32-bit Android devices are not recommended." in lines


def test_build_device_profile_from_scan_outputs_bad_meminfo_has_context():
    outputs = DeviceScanOutputs(
        meminfo="not meminfo",
        storage="Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/dm-2 100 1 7340032 1% /data",
        abi="arm64-v8a",
        android_version="15",
        manufacturer="Google",
        model="Pixel Test",
        battery="level: 55",
    )

    with pytest.raises(ValueError, match=r"Unable to parse RAM from /proc/meminfo scan output: MemTotal not found"):
        build_device_profile_from_scan_outputs("ABC123", outputs)


def test_build_device_profile_from_scan_outputs_bad_storage_has_context():
    outputs = DeviceScanOutputs(
        meminfo="MemTotal: 6291456 kB",
        storage="not df",
        abi="arm64-v8a",
        android_version="15",
        manufacturer="Google",
        model="Pixel Test",
        battery="level: 55",
    )

    with pytest.raises(ValueError, match=r"Unable to parse free storage from df /data scan output: /data row"):
        build_device_profile_from_scan_outputs("ABC123", outputs)
