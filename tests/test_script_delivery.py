from pathlib import Path

from droidshield.script_delivery import (
    EXPECTED_TERMUX_SCRIPT_PATHS,
    build_script_delivery_plan,
)


def test_builds_adb_push_commands_for_all_generated_termux_files():
    plan = build_script_delivery_plan(
        local_generated_termux_dir=Path("out") / "generated" / "termux",
        remote_termux_home="/data/data/com.termux/files/home",
    )

    push_commands = tuple(command for command in plan.commands if command[1] == "push")

    assert push_commands == tuple(
        (
            "adb",
            "push",
            str(Path("out") / "generated" / "termux" / relative_path),
            f"/sdcard/Download/droidshield/termux/{relative_path.as_posix()}",
        )
        for relative_path in EXPECTED_TERMUX_SCRIPT_PATHS
    )


def test_preserves_relative_paths_under_generated_termux_on_remote_device():
    plan = build_script_delivery_plan(
        local_generated_termux_dir=Path("generated") / "termux",
        remote_termux_home="/home",
    )

    assert (
        "adb",
        "push",
        str(Path("generated") / "termux" / ".shortcuts" / "Start DroidShield"),
        "/sdcard/Download/droidshield/termux/.shortcuts/Start DroidShield",
    ) in plan.commands
    assert (
        "adb",
        "push",
        str(Path("generated") / "termux" / ".shortcuts" / "icons" / "Start DroidShield.png"),
        "/sdcard/Download/droidshield/termux/.shortcuts/icons/Start DroidShield.png",
    ) in plan.commands


def test_includes_serial_in_every_adb_command_when_provided():
    plan = build_script_delivery_plan(
        local_generated_termux_dir=Path("generated") / "termux",
        remote_termux_home="/home",
        serial="device-123",
    )

    assert plan.commands
    assert all(command[:3] == ("adb", "-s", "device-123") for command in plan.commands)


def test_stages_files_in_android_downloads_without_private_termux_writes():
    plan = build_script_delivery_plan(
        local_generated_termux_dir=Path("generated") / "termux",
        remote_termux_home="/home",
        serial="device-123",
    )

    assert not any("/data/data/com.termux" in part for command in plan.commands for part in command)
    assert any(command[3:6] == ("shell", "mkdir", "-p") for command in plan.commands)
    assert any("chmod +x" in command for command in plan.post_push_termux_commands)


def test_delivery_plan_includes_inspectable_post_push_termux_steps():
    plan = build_script_delivery_plan()

    assert plan.post_push_termux_commands == (
        "termux-setup-storage",
        "mkdir -p ~/.shortcuts/icons",
        'cp -r "$HOME/storage/downloads/droidshield/termux/." "$HOME/"',
        'chmod +x "$HOME/bootstrap.sh" "$HOME/setup-ollama-debian.sh" "$HOME/pro-ai-knowledge-server.py" "$HOME/start-droidshield.sh" "$HOME/install-models.sh" "$HOME/.shortcuts/Start DroidShield"',
        "~/bootstrap.sh",
        "~/install-models.sh",
        "~/start-droidshield.sh",
    )
    assert any("Termux:Widget" in instruction for instruction in plan.instructions)
