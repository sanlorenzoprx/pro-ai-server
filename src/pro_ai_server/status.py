from __future__ import annotations

from dataclasses import dataclass

from pro_ai_server.adb import select_adb_device_from_output
from pro_ai_server.ide import IdeExtensionStatus
from pro_ai_server.ollama import OllamaServerStatus


USB_FORWARD_PORT = "tcp:11434"


@dataclass(frozen=True)
class StatusItem:
    label: str
    ok: bool | None
    detail: str


@dataclass(frozen=True)
class ProAiStatus:
    items: tuple[StatusItem, ...]

    @property
    def ok(self) -> bool:
        return all(item.ok is not False for item in self.items)


def build_status_report(
    adb_devices_output: str | None,
    adb_forward_output: str | None,
    ollama_status: OllamaServerStatus,
    ide_statuses: tuple[IdeExtensionStatus, ...],
    *,
    adb_path: str | None,
) -> ProAiStatus:
    return ProAiStatus(
        items=(
            _adb_item(adb_devices_output, adb_path=adb_path),
            _tunnel_item(adb_forward_output, adb_path=adb_path),
            _server_item(ollama_status),
            _ide_item(ide_statuses),
        )
    )


def render_status_report(report: ProAiStatus) -> tuple[str, ...]:
    lines = ["Pro AI Server Status"]
    for item in report.items:
        lines.append(f"{_status_label(item.ok)} {item.label}: {item.detail}")
    return tuple(lines)


def _adb_item(adb_devices_output: str | None, *, adb_path: str | None) -> StatusItem:
    if not adb_path:
        return StatusItem("Phone", False, "adb not found")
    selection = select_adb_device_from_output(adb_devices_output or "")
    if selection.ok and selection.selected:
        return StatusItem("Phone", True, f"connected ({selection.selected.serial})")
    return StatusItem("Phone", False, selection.error or "no authorized phone detected")


def _tunnel_item(adb_forward_output: str | None, *, adb_path: str | None) -> StatusItem:
    if not adb_path:
        return StatusItem("USB tunnel", None, "skipped because adb is unavailable")
    if not adb_forward_output:
        return StatusItem("USB tunnel", False, "adb forward tcp:11434 is not active")
    if USB_FORWARD_PORT in adb_forward_output:
        return StatusItem("USB tunnel", True, "adb forward tcp:11434 is active")
    return StatusItem("USB tunnel", False, "adb forward tcp:11434 is not active")


def _server_item(ollama_status: OllamaServerStatus) -> StatusItem:
    if ollama_status.ok:
        model_count = len(ollama_status.model_names)
        suffix = "model" if model_count == 1 else "models"
        return StatusItem("Ollama", True, f"responding on /api/tags ({model_count} {suffix})")
    warning = ollama_status.warnings[0] if ollama_status.warnings else "not responding"
    return StatusItem("Ollama", False, warning)


def _ide_item(ide_statuses: tuple[IdeExtensionStatus, ...]) -> StatusItem:
    ready = tuple(status.ide.command for status in ide_statuses if status.installed is True)
    if ready:
        return StatusItem("IDE", True, "Continue ready in " + ", ".join(ready))

    installed_ides = tuple(status.ide.command for status in ide_statuses if status.ide.installed)
    if installed_ides:
        return StatusItem(
            "IDE",
            False,
            "Continue extension missing in " + ", ".join(installed_ides),
        )

    return StatusItem("IDE", False, "no supported IDE CLI found")


def _status_label(ok: bool | None) -> str:
    if ok is True:
        return "OK"
    if ok is False:
        return "Needs attention"
    return "Unknown"
