from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pro_ai_server import __version__
from pro_ai_server.hardware import parse_battery_dump, parse_data_free_storage_gb, parse_meminfo_ram_gb


IDE_COMMANDS = ("code", "cursor", "codium", "windsurf")
CommandRunner = Callable[[list[str]], str]
Which = Callable[[str], str | None]


@dataclass(frozen=True)
class DiagnosticsReport:
    text: str


def default_command_runner(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        raise RuntimeError(stderr or stdout or f"Command failed with exit code {result.returncode}.")
    return result.stdout.strip()


def redact_sensitive_paths(value: str) -> str:
    redacted = value
    home = str(os.path.expanduser("~"))
    if home and home != "~":
        redacted = redacted.replace(home, "~")

    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        redacted = redacted.replace(user_profile, "%USERPROFILE%")

    redacted = re.sub(r"C:\\Users\\[^\\\r\n]+", r"%USERPROFILE%", redacted)
    redacted = re.sub(r"/home/[^/\r\n]+", "~", redacted)
    redacted = re.sub(r"/Users/[^/\r\n]+", "~", redacted)
    return redacted


def detect_ide_clis(which: Which = shutil.which) -> dict[str, str | None]:
    return {command: which(command) for command in IDE_COMMANDS}


def _run_or_message(command: list[str], runner: CommandRunner) -> str:
    try:
        return runner(command).strip()
    except Exception as exc:  # noqa: BLE001 - diagnostics should report failures, not fail.
        return f"ERROR: {exc}"


def _format_gb(value: float) -> str:
    return f"{value:.2f} GB"


def summarize_ram_diagnostic(meminfo: str) -> str:
    try:
        return f"RAM: {_format_gb(parse_meminfo_ram_gb(meminfo))}"
    except ValueError:
        return f"RAM: {meminfo}"


def summarize_free_storage_diagnostic(df_output: str) -> str:
    try:
        return f"Free storage: {_format_gb(parse_data_free_storage_gb(df_output))}"
    except ValueError:
        return f"Free storage: {df_output}"


def summarize_battery_diagnostic(dumpsys_battery: str) -> str:
    battery = parse_battery_dump(dumpsys_battery)
    if all(value is None for value in battery.values()):
        return f"Battery: {dumpsys_battery}"

    level = _format_optional(battery["battery_level"], suffix="%")
    temperature = _format_optional(battery["battery_temperature_c"], suffix=" C")
    charging = _format_charging(battery["is_charging"])
    return f"Battery: level {level}; temperature {temperature}; charging {charging}"


def _format_optional(value: int | float | bool | None, *, suffix: str) -> str:
    if value is None:
        return "unknown"
    return f"{value}{suffix}"


def _format_charging(value: object) -> str:
    if value is None:
        return "unknown"
    return "yes" if value is True else "no"


def _connected_phone_present(adb_devices_output: str) -> bool:
    for line in adb_devices_output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("List of devices"):
            continue
        parts = stripped.split()
        if len(parts) >= 2 and parts[1] == "device":
            return True
    return False


def _section(title: str, lines: list[str]) -> str:
    return "\n".join([f"## {title}", *lines])


def write_diagnostics_report(report: DiagnosticsReport, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.write_text(report.text, encoding="utf-8")
    return path


def build_diagnostics_report(
    adb_path: str | None,
    command_runner: CommandRunner = default_command_runner,
    which: Which = shutil.which,
) -> DiagnosticsReport:
    ide_results = detect_ide_clis(which)
    host_lines = [
        f"Python: {sys.version.split()[0]}",
        f"OS: {platform.platform()}",
        f"Pro AI Server: {__version__}",
        f"ADB path: {redact_sensitive_paths(adb_path) if adb_path else 'not found'}",
        "IDE CLIs:",
    ]
    for name, path in ide_results.items():
        host_lines.append(f"- {name}: {redact_sensitive_paths(path) if path else 'not found'}")

    phone_lines: list[str] = []
    server_lines: list[str] = []
    if not adb_path:
        phone_lines.append("No ADB path available; phone diagnostics were not run.")
        server_lines.append("ADB reverse list skipped because ADB is unavailable.")
        server_lines.append(
            "Ollama tags: "
            + _run_or_message(["curl", "--silent", "--show-error", "http://localhost:11434/api/tags"], command_runner)
        )
    else:
        devices = _run_or_message([adb_path, "devices"], command_runner)
        phone_lines.append("adb devices:")
        phone_lines.extend(devices.splitlines() or ["<no output>"])

        if _connected_phone_present(devices):
            simple_probes = [
                ("Manufacturer", [adb_path, "shell", "getprop", "ro.product.manufacturer"]),
                ("Model", [adb_path, "shell", "getprop", "ro.product.model"]),
                ("Android version", [adb_path, "shell", "getprop", "ro.build.version.release"]),
                ("ABI", [adb_path, "shell", "getprop", "ro.product.cpu.abi"]),
            ]
            for label, command in simple_probes:
                phone_lines.append(f"{label}: {redact_sensitive_paths(_run_or_message(command, command_runner))}")

            meminfo = _run_or_message([adb_path, "shell", "cat", "/proc/meminfo"], command_runner)
            storage = _run_or_message([adb_path, "shell", "df", "-k", "/data"], command_runner)
            battery = _run_or_message([adb_path, "shell", "dumpsys", "battery"], command_runner)
            phone_lines.append(summarize_ram_diagnostic(redact_sensitive_paths(meminfo)))
            phone_lines.append(summarize_free_storage_diagnostic(redact_sensitive_paths(storage)))
            phone_lines.append(summarize_battery_diagnostic(redact_sensitive_paths(battery)))
        else:
            phone_lines.append("No phone connected or authorized.")

        server_lines.append("adb reverse --list:")
        reverse_list = _run_or_message([adb_path, "reverse", "--list"], command_runner)
        server_lines.extend(redact_sensitive_paths(reverse_list).splitlines() or ["<no output>"])
        server_lines.append("Ollama tags:")
        server_lines.extend(
            redact_sensitive_paths(
                _run_or_message(["curl", "--silent", "--show-error", "http://localhost:11434/api/tags"], command_runner)
            ).splitlines()
            or ["<no output>"]
        )

    report = "\n\n".join(
        [
            "# Pro AI Server Diagnostics",
            _section("Host", host_lines),
            _section("Phone", phone_lines),
            _section("Server", server_lines),
        ]
    )
    return DiagnosticsReport(text=redact_sensitive_paths(report))
