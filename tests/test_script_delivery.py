from pathlib import Path

from pro_ai_server.script_delivery import (
    EXECUTABLE_TERMUX_SCRIPT_PATHS,
    EXPECTED_TERMUX_SCRIPT_PATHS,
    build_script_delivery_plan,
)


def test_builds_adb_push_commands_for_all_generated_termux_files():
    plan = build_script_delivery_plan(
        local_generated_termux_dir=Path("out") / "generated" / "termux",
        remote_termux_home="/data/data/com.termux/files/home",
    )

    push_commands = plan.commands[: len(EXPECTED_TERMUX_SCRIPT_PATHS)]

    assert push_commands == tuple(
        (
            "adb",
            "push",
            str(Path("out") / "generated" / "termux" / relative_path),
            f"/data/data/com.termux/files/home/{relative_path.as_posix()}",
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
        str(Path("generated") / "termux" / ".shortcuts" / "Start Pro AI Server"),
        "/home/.shortcuts/Start Pro AI Server",
    ) in plan.commands


def test_includes_serial_in_every_adb_command_when_provided():
    plan = build_script_delivery_plan(
        local_generated_termux_dir=Path("generated") / "termux",
        remote_termux_home="/home",
        serial="device-123",
    )

    assert plan.commands
    assert all(command[:3] == ("adb", "-s", "device-123") for command in plan.commands)


def test_adds_chmod_commands_for_executable_termux_scripts():
    plan = build_script_delivery_plan(
        local_generated_termux_dir=Path("generated") / "termux",
        remote_termux_home="/home",
        serial="device-123",
    )

    chmod_commands = plan.commands[len(EXPECTED_TERMUX_SCRIPT_PATHS) :]

    assert chmod_commands == tuple(
        ("adb", "-s", "device-123", "shell", "chmod", "+x", f"/home/{relative_path.as_posix()}")
        for relative_path in EXECUTABLE_TERMUX_SCRIPT_PATHS
    )


def test_delivery_plan_includes_inspectable_post_push_termux_steps():
    plan = build_script_delivery_plan()

    assert plan.post_push_termux_commands == (
        "~/bootstrap.sh",
        "~/install-models.sh",
        "~/start-pro-ai-server.sh",
    )
    assert any("Termux:Widget" in instruction for instruction in plan.instructions)
