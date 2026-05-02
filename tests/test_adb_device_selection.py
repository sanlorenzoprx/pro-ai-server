from pro_ai_server.adb import (
    AdbDeviceState,
    parse_adb_devices,
    parse_adb_device_state,
    select_adb_device_from_output,
)


def test_parse_adb_devices_output_records_known_and_other_states():
    devices = parse_adb_devices(
        "\n".join(
            [
                "List of devices attached",
                "ABC123\tdevice product:foo model:Pixel",
                "DEF456\tunauthorized",
                "GHI789\toffline",
                "JKL000\trecovery",
            ]
        )
    )

    assert [device.serial for device in devices] == ["ABC123", "DEF456", "GHI789", "JKL000"]
    assert [device.state for device in devices] == [
        AdbDeviceState.DEVICE,
        AdbDeviceState.UNAUTHORIZED,
        AdbDeviceState.OFFLINE,
        AdbDeviceState.OTHER,
    ]
    assert devices[3].raw_state == "recovery"


def test_parse_adb_device_state_is_case_insensitive_and_tracks_other_states():
    assert parse_adb_device_state("device") == AdbDeviceState.DEVICE
    assert parse_adb_device_state("UNAUTHORIZED") == AdbDeviceState.UNAUTHORIZED
    assert parse_adb_device_state("offline") == AdbDeviceState.OFFLINE
    assert parse_adb_device_state("recovery") == AdbDeviceState.OTHER


def test_no_devices_returns_clear_error():
    result = select_adb_device_from_output("List of devices attached\n")

    assert not result.ok
    assert result.selected is None
    assert result.error == "No ADB devices found. Connect a phone and enable USB debugging."


def test_one_authorized_device_is_selected():
    result = select_adb_device_from_output("List of devices attached\nABC123\tdevice\n")

    assert result.ok
    assert result.selected is not None
    assert result.selected.serial == "ABC123"
    assert result.error is None


def test_one_authorized_device_is_selected_when_other_devices_are_unavailable():
    result = select_adb_device_from_output(
        "List of devices attached\nABC123\tdevice\nDEF456\tunauthorized\nGHI789\toffline\n"
    )

    assert result.ok
    assert result.selected is not None
    assert result.selected.serial == "ABC123"


def test_multiple_authorized_devices_without_serial_requires_serial():
    result = select_adb_device_from_output("List of devices attached\nABC123\tdevice\nDEF456\tdevice\n")

    assert not result.ok
    assert result.error == "Multiple authorized ADB devices found; pass --serial with one of: ABC123, DEF456."


def test_requested_serial_found_and_authorized_is_selected():
    result = select_adb_device_from_output("List of devices attached\nABC123\tdevice\nDEF456\tdevice\n", serial="DEF456")

    assert result.ok
    assert result.selected is not None
    assert result.selected.serial == "DEF456"


def test_requested_serial_unauthorized_returns_state_error():
    result = select_adb_device_from_output("List of devices attached\nABC123\tunauthorized\n", serial="ABC123")

    assert not result.ok
    assert result.error == "Requested ADB device ABC123 is unauthorized; it is not authorized for commands."


def test_requested_serial_offline_returns_state_error():
    result = select_adb_device_from_output("List of devices attached\nABC123\toffline\n", serial="ABC123")

    assert not result.ok
    assert result.error == "Requested ADB device ABC123 is offline; it is not authorized for commands."


def test_requested_serial_missing_lists_known_devices():
    result = select_adb_device_from_output("List of devices attached\nABC123\tdevice\nDEF456\toffline\n", serial="ZZZ999")

    assert not result.ok
    assert result.error == "Requested ADB device ZZZ999 was not found. Known devices: ABC123 (device), DEF456 (offline)."


def test_requested_serial_missing_with_no_devices_returns_clear_error():
    result = select_adb_device_from_output("List of devices attached\n", serial="ZZZ999")

    assert not result.ok
    assert result.error == "Requested ADB device ZZZ999 was not found. No ADB devices are connected."


def test_unauthorized_only_explains_authorization():
    result = select_adb_device_from_output("List of devices attached\nABC123\tunauthorized\n")

    assert not result.ok
    assert result.error == "ADB device is unauthorized. Unlock the phone and approve the USB debugging prompt."


def test_offline_only_explains_state():
    result = select_adb_device_from_output("List of devices attached\nABC123\toffline\n")

    assert not result.ok
    assert result.error == "ADB device is offline. Reconnect the phone or restart ADB, then try again."


def test_unavailable_mixed_states_list_all_states():
    result = select_adb_device_from_output("List of devices attached\nABC123\tunauthorized\nDEF456\toffline\n")

    assert not result.ok
    assert result.error == "No authorized ADB devices found. Device states: ABC123 (unauthorized), DEF456 (offline)."
