from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil

import yaml

from pro_ai_server.models import ModelPlan


CONTINUE_CONFIG_NAME = "config.yaml"
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"
VALID_CONNECTION_MODES = {"usb", "lan", "tailscale"}


@dataclass(frozen=True)
class ContinueConfigWriteResult:
    config_path: Path
    backup_path: Path | None
    api_base: str


def api_base_for_mode(mode: str = "usb", host: str | None = None) -> str:
    normalized_mode = mode.strip().lower()
    if normalized_mode not in VALID_CONNECTION_MODES:
        valid_modes = ", ".join(sorted(VALID_CONNECTION_MODES))
        raise ValueError(f"Unknown Continue connection mode '{mode}'. Expected one of: {valid_modes}.")

    if normalized_mode == "usb":
        return "http://localhost:11434"

    normalized_host = (host or "").strip()
    if not normalized_host:
        raise ValueError(f"{normalized_mode} mode requires a host or IP address.")
    return f"http://{normalized_host}:11434"


def exposure_warnings(mode: str) -> list[str]:
    normalized_mode = mode.strip().lower()
    if normalized_mode == "lan":
        return ["LAN mode exposes Ollama to devices on the local network."]
    if normalized_mode == "tailscale":
        return ["Tailscale mode should use a private Tailscale hostname or 100.x.x.x IP address."]
    return []


def continue_config_data(plan: ModelPlan, mode: str = "usb", host: str | None = None) -> dict[str, object]:
    api_base = api_base_for_mode(mode, host)
    return {
        "name": "Pro AI Server Local",
        "version": "0.0.1",
        "schema": "v1",
        "models": [
            {
                "name": plan.chat_label,
                "provider": "ollama",
                "model": plan.chat_model,
                "apiBase": api_base,
                "roles": ["chat", "edit", "apply"],
            },
            {
                "name": plan.autocomplete_label,
                "provider": "ollama",
                "model": plan.autocomplete_model,
                "apiBase": api_base,
                "roles": ["autocomplete"],
            },
        ],
    }


def render_continue_config_yaml(plan: ModelPlan, mode: str = "usb", host: str | None = None) -> str:
    return yaml.safe_dump(
        continue_config_data(plan, mode, host),
        sort_keys=False,
        allow_unicode=False,
    )


def default_continue_dir(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".continue"


def backup_path_for_config(config_path: Path, now: datetime | None = None) -> Path:
    timestamp = (now or datetime.now()).strftime(BACKUP_TIMESTAMP_FORMAT)
    return config_path.with_name(f"{config_path.name}.pro-ai-server-backup-{timestamp}")


def write_continue_config(
    plan: ModelPlan,
    mode: str = "usb",
    host: str | None = None,
    continue_dir: Path | None = None,
    now: datetime | None = None,
) -> ContinueConfigWriteResult:
    target_dir = continue_dir or default_continue_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    config_path = target_dir / CONTINUE_CONFIG_NAME
    backup_path = None
    if config_path.exists():
        backup_path = backup_path_for_config(config_path, now)
        shutil.copy2(config_path, backup_path)

    config_path.write_text(render_continue_config_yaml(plan, mode, host), encoding="utf-8")
    return ContinueConfigWriteResult(
        config_path=config_path,
        backup_path=backup_path,
        api_base=api_base_for_mode(mode, host),
    )
