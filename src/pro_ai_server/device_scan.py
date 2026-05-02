from __future__ import annotations

from dataclasses import dataclass

from pro_ai_server import hardware


@dataclass(frozen=True)
class DeviceScanCommands:
    meminfo: tuple[str, ...]
    storage: tuple[str, ...]
    abi: tuple[str, ...]
    android_version: tuple[str, ...]
    manufacturer: tuple[str, ...]
    model: tuple[str, ...]
    battery: tuple[str, ...]


@dataclass(frozen=True)
class DeviceScanOutputs:
    meminfo: str
    storage: str
    abi: str
    android_version: str
    manufacturer: str
    model: str
    battery: str


def build_adb_shell_command(adb: str, args: tuple[str, ...], serial: str | None = None) -> tuple[str, ...]:
    if serial:
        return (adb, "-s", serial, "shell", *args)
    return (adb, "shell", *args)


def build_meminfo_scan_command(adb: str, serial: str | None = None) -> tuple[str, ...]:
    return build_adb_shell_command(adb, ("cat", "/proc/meminfo"), serial)


def build_storage_scan_command(adb: str, serial: str | None = None) -> tuple[str, ...]:
    return build_adb_shell_command(adb, ("df", "-k", "/data"), serial)


def build_abi_scan_command(adb: str, serial: str | None = None) -> tuple[str, ...]:
    return build_adb_shell_command(adb, ("getprop", "ro.product.cpu.abi"), serial)


def build_android_version_scan_command(adb: str, serial: str | None = None) -> tuple[str, ...]:
    return build_adb_shell_command(adb, ("getprop", "ro.build.version.release"), serial)


def build_manufacturer_scan_command(adb: str, serial: str | None = None) -> tuple[str, ...]:
    return build_adb_shell_command(adb, ("getprop", "ro.product.manufacturer"), serial)


def build_model_scan_command(adb: str, serial: str | None = None) -> tuple[str, ...]:
    return build_adb_shell_command(adb, ("getprop", "ro.product.model"), serial)


def build_battery_scan_command(adb: str, serial: str | None = None) -> tuple[str, ...]:
    return build_adb_shell_command(adb, ("dumpsys", "battery"), serial)


def build_device_scan_commands(adb: str, serial: str | None = None) -> DeviceScanCommands:
    return DeviceScanCommands(
        meminfo=build_meminfo_scan_command(adb, serial),
        storage=build_storage_scan_command(adb, serial),
        abi=build_abi_scan_command(adb, serial),
        android_version=build_android_version_scan_command(adb, serial),
        manufacturer=build_manufacturer_scan_command(adb, serial),
        model=build_model_scan_command(adb, serial),
        battery=build_battery_scan_command(adb, serial),
    )


def build_device_profile_from_scan_outputs(serial: str, outputs: DeviceScanOutputs) -> hardware.DeviceProfile:
    try:
        ram_gb = hardware.parse_meminfo_ram_gb(outputs.meminfo)
    except ValueError as exc:
        raise ValueError(f"Unable to parse RAM from /proc/meminfo scan output: {exc}") from exc

    try:
        free_storage_gb = hardware.parse_data_free_storage_gb(outputs.storage)
    except ValueError as exc:
        raise ValueError(f"Unable to parse free storage from df /data scan output: {exc}") from exc

    battery = hardware.parse_battery_dump(outputs.battery)
    return hardware.assess_device_profile(
        serial=serial.strip(),
        manufacturer=outputs.manufacturer.strip(),
        model=outputs.model.strip(),
        android_version=outputs.android_version.strip(),
        abi=outputs.abi.strip(),
        ram_gb=ram_gb,
        free_storage_gb=free_storage_gb,
        battery_level=_battery_int(battery["battery_level"], "battery_level"),
        battery_temperature_c=_battery_float(battery["battery_temperature_c"], "battery_temperature_c"),
        is_charging=_battery_bool(battery["is_charging"], "is_charging"),
    )


def build_device_scan_summary_lines(profile: hardware.DeviceProfile) -> tuple[str, ...]:
    lines = [
        f"Serial: {profile.serial}",
        f"Device: {profile.manufacturer} {profile.model}",
        f"Android: {profile.android_version}",
        f"ABI: {profile.abi}",
        f"RAM: {profile.ram_gb:.2f} GB",
        f"Free storage: {profile.free_storage_gb:.2f} GB",
        f"Battery: {_format_unknown(profile.battery_level, '%')}",
        f"Charging: {_format_unknown(profile.is_charging)}",
    ]

    if profile.recommended_profile:
        recommended = profile.recommended_profile
        lines.extend(
            [
                f"Recommended profile: {recommended.name} ({recommended.status})",
                f"Chat model: {recommended.chat_model}",
                f"Autocomplete model: {recommended.autocomplete_model}",
            ]
        )

    lines.extend(f"Warning: {warning}" for warning in profile.warnings)
    return tuple(lines)


def _format_unknown(value: object | None, suffix: str = "") -> str:
    if value is None:
        return "unknown"
    return f"{value}{suffix}"


def _battery_int(value: int | float | bool | None, field_name: str) -> int | None:
    if value is None or isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError(f"Unable to parse battery scan output: expected {field_name} to be an integer or unknown.")


def _battery_float(value: int | float | bool | None, field_name: str) -> float | None:
    if value is None or isinstance(value, int | float) and not isinstance(value, bool):
        return value
    raise ValueError(f"Unable to parse battery scan output: expected {field_name} to be a number or unknown.")


def _battery_bool(value: int | float | bool | None, field_name: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ValueError(f"Unable to parse battery scan output: expected {field_name} to be true, false, or unknown.")
