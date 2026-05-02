from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AdbDeviceState(str, Enum):
    DEVICE = "device"
    UNAUTHORIZED = "unauthorized"
    OFFLINE = "offline"
    OTHER = "other"


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: AdbDeviceState
    raw_state: str

    @property
    def authorized(self) -> bool:
        return self.state == AdbDeviceState.DEVICE


@dataclass(frozen=True)
class AdbDeviceSelection:
    selected: AdbDevice | None
    error: str | None

    @property
    def ok(self) -> bool:
        return self.selected is not None and self.error is None


def parse_adb_device_state(raw_state: str) -> AdbDeviceState:
    normalized = raw_state.strip().lower()
    if normalized == AdbDeviceState.DEVICE.value:
        return AdbDeviceState.DEVICE
    if normalized == AdbDeviceState.UNAUTHORIZED.value:
        return AdbDeviceState.UNAUTHORIZED
    if normalized == AdbDeviceState.OFFLINE.value:
        return AdbDeviceState.OFFLINE
    return AdbDeviceState.OTHER


def parse_adb_devices(output: str) -> tuple[AdbDevice, ...]:
    devices: list[AdbDevice] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("List of devices"):
            continue
        if stripped.startswith("* "):
            continue

        parts = stripped.split()
        if len(parts) < 2:
            continue

        raw_state = parts[1]
        devices.append(
            AdbDevice(
                serial=parts[0],
                state=parse_adb_device_state(raw_state),
                raw_state=raw_state,
            )
        )
    return tuple(devices)


def select_adb_device_from_output(output: str, serial: str | None = None) -> AdbDeviceSelection:
    return select_adb_device(parse_adb_devices(output), serial=serial)


def select_adb_device(devices: tuple[AdbDevice, ...], serial: str | None = None) -> AdbDeviceSelection:
    if serial:
        return _select_requested_device(devices, serial)

    authorized = tuple(device for device in devices if device.authorized)
    if len(authorized) == 1:
        return AdbDeviceSelection(selected=authorized[0], error=None)
    if len(authorized) > 1:
        return _error(
            "Multiple authorized ADB devices found; pass --serial with one of: "
            + _format_device_serials(authorized)
            + "."
        )
    if not devices:
        return _error("No ADB devices found. Connect a phone and enable USB debugging.")

    return _error(_no_authorized_devices_message(devices))


def _select_requested_device(devices: tuple[AdbDevice, ...], serial: str) -> AdbDeviceSelection:
    for device in devices:
        if device.serial != serial:
            continue
        if device.authorized:
            return AdbDeviceSelection(selected=device, error=None)
        return _error(f"Requested ADB device {serial} is {device.raw_state}; it is not authorized for commands.")

    if devices:
        return _error(
            f"Requested ADB device {serial} was not found. Known devices: " + _format_known_devices(devices) + "."
        )
    return _error(f"Requested ADB device {serial} was not found. No ADB devices are connected.")


def _no_authorized_devices_message(devices: tuple[AdbDevice, ...]) -> str:
    states = {device.state for device in devices}
    if states == {AdbDeviceState.UNAUTHORIZED}:
        return "ADB device is unauthorized. Unlock the phone and approve the USB debugging prompt."
    if states == {AdbDeviceState.OFFLINE}:
        return "ADB device is offline. Reconnect the phone or restart ADB, then try again."
    return "No authorized ADB devices found. Device states: " + _format_known_devices(devices) + "."


def _format_device_serials(devices: tuple[AdbDevice, ...]) -> str:
    return ", ".join(device.serial for device in devices)


def _format_known_devices(devices: tuple[AdbDevice, ...]) -> str:
    return ", ".join(f"{device.serial} ({device.raw_state})" for device in devices)


def _error(message: str) -> AdbDeviceSelection:
    return AdbDeviceSelection(selected=None, error=message)
