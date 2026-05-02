import pytest

from pro_ai_server.setup_workflow import plan_setup_workflow


def step_keys(plan):
    return tuple(step.key for step in plan.steps)


def test_usb_default_flow_uses_local_mode_without_confirmation():
    plan = plan_setup_workflow()

    assert plan.mode == "usb"
    assert plan.host is None
    assert plan.model_plan.profile == "professional"
    assert plan.requires_confirmation is False
    assert plan.warnings == ()
    assert step_keys(plan) == (
        "select-models",
        "generate-termux-scripts",
        "configure-continue",
        "create-usb-tunnel",
    )
    assert "does not require exposure confirmation" in plan.summary


def test_lan_requires_confirmation_and_exposure_warning():
    plan = plan_setup_workflow(mode="lan", host="192.168.1.50")

    assert plan.requires_confirmation is True
    assert plan.warnings == ("LAN mode exposes Ollama to devices on the local network.",)
    assert "create-usb-tunnel" not in step_keys(plan)
    assert "requires explicit confirmation" in plan.summary


def test_tailscale_requires_confirmation_without_default_tunnel():
    plan = plan_setup_workflow(mode="tailscale", host="pro-ai-phone")

    assert plan.requires_confirmation is True
    assert plan.warnings == ("Tailscale mode should use a private Tailscale hostname or 100.x.x.x IP address.",)
    assert "create-usb-tunnel" not in step_keys(plan)


def test_lan_and_tailscale_continue_steps_require_host():
    with pytest.raises(ValueError, match="requires a host"):
        plan_setup_workflow(mode="lan")

    with pytest.raises(ValueError, match="requires a host"):
        plan_setup_workflow(mode="tailscale")


def test_continue_config_step_is_optional_and_marks_user_config_backup():
    disabled = plan_setup_workflow(configure_continue=False)
    enabled = plan_setup_workflow(configure_continue=True)

    assert "configure-continue" not in step_keys(disabled)

    continue_step = next(step for step in enabled.steps if step.key == "configure-continue")
    assert "config.yaml" in continue_step.detail
    assert any("writes user Continue config" in note for note in continue_step.notes)
    assert any("backed up" in note for note in continue_step.notes)


def test_tunnel_step_defaults_to_usb_and_can_be_overridden():
    usb_without_tunnel = plan_setup_workflow(mode="usb", create_usb_tunnel=False)
    lan_with_tunnel = plan_setup_workflow(mode="lan", host="192.168.1.50", create_usb_tunnel=True)

    assert "create-usb-tunnel" not in step_keys(usb_without_tunnel)

    tunnel_step = next(step for step in lan_with_tunnel.steps if step.key == "create-usb-tunnel")
    assert tunnel_step.commands == (("adb", "reverse", "tcp:11434", "tcp:11434"),)


def test_push_scripts_step_notes_inspectable_adb_push_delivery():
    plan = plan_setup_workflow(push_scripts=True, serial="device-123")

    push_step = next(step for step in plan.steps if step.key == "push-scripts")

    assert push_step.commands
    assert all(command[:3] == ("adb", "-s", "device-123") for command in push_step.commands)
    assert any("Scripts are inspectable" in note for note in push_step.notes)
    assert any("adb push" in note for note in push_step.notes)


def test_model_profile_can_be_selected_by_ram_or_explicit_profile():
    by_ram = plan_setup_workflow(ram_gb=4.5)
    by_profile = plan_setup_workflow(ram_gb=4.5, profile="max")

    assert by_ram.model_plan.profile == "lightweight"
    assert by_profile.model_plan.profile == "max"


def test_unknown_setup_mode_is_rejected():
    with pytest.raises(ValueError, match="Unknown setup mode"):
        plan_setup_workflow(mode="bluetooth")
