from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


TAILSCALE_ANDROID_PACKAGE = "com.tailscale.ipn"
TAILSCALE_WINGET_ID = "Tailscale.Tailscale"
TAILSCALE_PLAY_STORE_URI = f"market://details?id={TAILSCALE_ANDROID_PACKAGE}"


Command = tuple[str, ...]


@dataclass(frozen=True)
class TailscaleInstallPlan:
    host_check_command: Command
    host_install_command: Command
    android_check_command: Command
    android_install_command: Command | None
    android_open_store_command: Command
    package_name: str = TAILSCALE_ANDROID_PACKAGE
    winget_id: str = TAILSCALE_WINGET_ID


def build_tailscale_install_plan(
    adb: str,
    *,
    serial: str | None = None,
    android_apk: Path | None = None,
) -> TailscaleInstallPlan:
    adb_prefix = (adb, "-s", serial) if serial else (adb,)
    return TailscaleInstallPlan(
        host_check_command=("tailscale", "version"),
        host_install_command=("winget", "install", "--id", TAILSCALE_WINGET_ID, "--exact"),
        android_check_command=(*adb_prefix, "shell", "pm", "path", TAILSCALE_ANDROID_PACKAGE),
        android_install_command=(*adb_prefix, "install", "-r", str(android_apk)) if android_apk else None,
        android_open_store_command=(
            *adb_prefix,
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            TAILSCALE_PLAY_STORE_URI,
        ),
    )


def tailscale_android_installed(pm_path_output: str) -> bool:
    return any(line.strip().startswith("package:") for line in pm_path_output.splitlines())


def tailscale_host_installed(version_output: str) -> bool:
    return bool(version_output.strip())
