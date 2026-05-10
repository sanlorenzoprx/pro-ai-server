from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelProfile:
    name: str
    chat_model: str
    autocomplete_model: str
    status: str


@dataclass(frozen=True)
class DeviceProfile:
    serial: str
    manufacturer: str
    model: str
    android_version: str
    abi: str
    ram_gb: float
    free_storage_gb: float
    battery_level: int | None
    battery_temperature_c: float | None
    is_charging: bool | None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    recommended_profile: ModelProfile | None = None


LIGHTWEIGHT_PROFILE = ModelProfile(
    name="lightweight",
    chat_model="qwen2.5-coder:1.5b",
    autocomplete_model="qwen2.5-coder:0.5b",
    status="experimental",
)
PROFESSIONAL_PROFILE = ModelProfile(
    name="professional",
    chat_model="qwen2.5-coder:3b",
    autocomplete_model="qwen2.5-coder:1.5b-base",
    status="recommended",
)
MAX_PROFILE = ModelProfile(
    name="max",
    chat_model="qwen2.5-coder:7b",
    autocomplete_model="qwen2.5-coder:1.5b-base",
    status="high-memory",
)


def parse_meminfo_ram_gb(meminfo: str) -> float:
    for line in meminfo.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) / 1024 / 1024
    raise ValueError("MemTotal not found in /proc/meminfo output.")


def parse_data_free_storage_gb(df_output: str) -> float:
    for line in df_output.splitlines():
        parts = line.split()
        if not parts or parts[0].lower() == "filesystem":
            continue
        if parts[-1] == "/data" and len(parts) >= 4:
            return int(parts[3]) / 1024 / 1024
    raise ValueError("/data row not found in df output.")


def parse_battery_dump(dumpsys_battery: str) -> dict[str, int | float | bool | None]:
    values: dict[str, str] = {}
    for line in dumpsys_battery.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip().lower()] = value.strip()

    level = _parse_optional_int(values.get("level"))
    temperature_tenths_c = _parse_optional_int(values.get("temperature"))
    plugged = _parse_optional_int(values.get("plugged"))
    status = _parse_optional_int(values.get("status"))

    is_charging = None
    if plugged is not None or status is not None:
        is_charging = bool(plugged) or status in {2, 5}

    return {
        "battery_level": level,
        "battery_temperature_c": None if temperature_tenths_c is None else temperature_tenths_c / 10,
        "is_charging": is_charging,
    }


def select_model_profile(ram_gb: float) -> ModelProfile:
    if ram_gb < 5:
        return LIGHTWEIGHT_PROFILE
    if ram_gb < 9:
        return PROFESSIONAL_PROFILE
    return MAX_PROFILE


def assess_device_profile(
    *,
    serial: str,
    manufacturer: str,
    model: str,
    android_version: str,
    abi: str,
    ram_gb: float,
    free_storage_gb: float,
    battery_level: int | None = None,
    battery_temperature_c: float | None = None,
    is_charging: bool | None = None,
) -> DeviceProfile:
    warnings = tuple(build_hardware_warnings(abi=abi, free_storage_gb=free_storage_gb))
    return DeviceProfile(
        serial=serial,
        manufacturer=manufacturer,
        model=model,
        android_version=android_version,
        abi=abi,
        ram_gb=ram_gb,
        free_storage_gb=free_storage_gb,
        battery_level=battery_level,
        battery_temperature_c=battery_temperature_c,
        is_charging=is_charging,
        warnings=warnings,
        recommended_profile=select_model_profile(ram_gb),
    )


def build_hardware_warnings(*, abi: str, free_storage_gb: float) -> list[str]:
    warnings = []
    if free_storage_gb < 4:
        warnings.append(
            "Free storage is under 4 GB; block full install and use lightweight mode or manual cleanup."
        )
    elif free_storage_gb < 8:
        warnings.append("Free storage is under 8 GB; warn before downloading models.")

    if abi.lower() not in {"arm64-v8a", "aarch64"}:
        warnings.append("Non-arm64 ABI detected; 32-bit Android devices are not recommended.")

    return warnings


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
