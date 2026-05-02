from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pro_ai_server.termux_scripts import DEFAULT_SCRIPT_DIR, DEBIAN_OLLAMA_SETUP_SCRIPT, WIDGET_SHORTCUT_PATH


Command = tuple[str, ...]

EXPECTED_TERMUX_SCRIPT_PATHS: tuple[Path, ...] = (
    Path("bootstrap.sh"),
    Path(DEBIAN_OLLAMA_SETUP_SCRIPT),
    Path("start-pro-ai-server.sh"),
    Path("install-models.sh"),
    WIDGET_SHORTCUT_PATH,
    Path("ANDROID_OPTIMIZATION_CHECKLIST.txt"),
    Path("TERMUX_WIDGET_INSTRUCTIONS.txt"),
)

EXECUTABLE_TERMUX_SCRIPT_PATHS: tuple[Path, ...] = (
    Path("bootstrap.sh"),
    Path(DEBIAN_OLLAMA_SETUP_SCRIPT),
    Path("start-pro-ai-server.sh"),
    Path("install-models.sh"),
    WIDGET_SHORTCUT_PATH,
)


@dataclass(frozen=True)
class ScriptDeliveryPlan:
    commands: tuple[Command, ...]
    post_push_termux_commands: tuple[str, ...]
    instructions: tuple[str, ...]


def build_script_delivery_plan(
    local_generated_termux_dir: Path = DEFAULT_SCRIPT_DIR,
    remote_termux_home: str = "/data/data/com.termux/files/home",
    serial: str | None = None,
) -> ScriptDeliveryPlan:
    remote_home = _remote_path(remote_termux_home)
    push_commands = tuple(
        _adb_command(
            (
                "push",
                str(local_generated_termux_dir / relative_path),
                str(remote_home / _posix_relative(relative_path)),
            ),
            serial,
        )
        for relative_path in EXPECTED_TERMUX_SCRIPT_PATHS
    )
    chmod_commands = tuple(
        _adb_command(("shell", "chmod", "+x", str(remote_home / _posix_relative(relative_path))), serial)
        for relative_path in EXECUTABLE_TERMUX_SCRIPT_PATHS
    )

    return ScriptDeliveryPlan(
        commands=push_commands + chmod_commands,
        post_push_termux_commands=(
            "~/bootstrap.sh",
            "~/install-models.sh",
            "~/start-pro-ai-server.sh",
        ),
        instructions=(
            "Run the post-push commands inside Termux after the files are pushed.",
            "Install Termux:Widget and add the Start Pro AI Server shortcut from the Android home screen.",
            "Review ANDROID_OPTIMIZATION_CHECKLIST.txt on the device to reduce background interruptions.",
        ),
    )


def build_adb_push_commands(
    local_generated_termux_dir: Path = DEFAULT_SCRIPT_DIR,
    remote_termux_home: str = "/data/data/com.termux/files/home",
    serial: str | None = None,
) -> tuple[Command, ...]:
    return build_script_delivery_plan(local_generated_termux_dir, remote_termux_home, serial).commands


def _adb_command(args: tuple[str, ...], serial: str | None) -> Command:
    if serial:
        return ("adb", "-s", serial, *args)
    return ("adb", *args)


def _remote_path(path: str) -> PurePosixPath:
    return PurePosixPath(path.rstrip("/"))


def _posix_relative(path: Path) -> PurePosixPath:
    return PurePosixPath(*path.parts)
