from pathlib import Path

from pro_ai_server.continue_config import ContinueConfigWriteResult
from pro_ai_server.models import model_plan_for_profile
from pro_ai_server.script_delivery import build_script_delivery_plan
from pro_ai_server.setup_receipt import SetupReceipt, build_setup_receipt, render_setup_receipt
from pro_ai_server.setup_workflow import plan_setup_workflow
from pro_ai_server.termux_scripts import generate_termux_scripts


def test_builds_minimal_plan_only_receipt():
    plan = plan_setup_workflow(configure_continue=False, create_usb_tunnel=False)

    receipt = build_setup_receipt(workflow_plan=plan)

    assert receipt.mode == "usb"
    assert receipt.model_profile == "professional"
    assert receipt.generated_termux_paths == ()
    assert receipt.continue_config_path is None
    assert receipt.pushed_scripts is False
    assert receipt.tunnel_requested is False
    assert receipt.artifacts == ()


def test_receipt_captures_continue_config_backup():
    plan = plan_setup_workflow()
    result = ContinueConfigWriteResult(
        config_path=Path("home") / ".continue" / "config.yaml",
        backup_path=Path("home") / ".continue" / "config.yaml.pro-ai-server-backup-20260502-131415",
        api_base="http://localhost:11434",
    )

    receipt = build_setup_receipt(workflow_plan=plan, continue_result=result)

    assert receipt.continue_config_path == result.config_path
    assert receipt.continue_backup_path == result.backup_path
    assert ("Continue config", str(result.config_path)) in tuple((item.label, item.value) for item in receipt.artifacts)
    assert ("Continue config backup", str(result.backup_path)) in tuple(
        (item.label, item.value) for item in receipt.artifacts
    )


def test_receipt_captures_script_push_and_tunnel():
    model_plan = model_plan_for_profile("professional")
    bundle = generate_termux_scripts(
        model_plan.chat_model,
        model_plan.autocomplete_model,
        script_dir=Path("out") / "termux",
    )
    delivery_plan = build_script_delivery_plan(local_generated_termux_dir=Path("out") / "termux", serial="device-123")
    written_paths = (Path("out") / "termux" / "start-pro-ai-server.sh", Path("out") / "termux" / "bootstrap.sh")

    receipt = build_setup_receipt(
        termux_bundle=bundle,
        written_termux_paths=written_paths,
        delivery_plan=delivery_plan,
        model_plan=model_plan,
        tunnel_requested=True,
    )

    assert receipt.generated_termux_paths == tuple(sorted(written_paths, key=lambda path: path.as_posix()))
    assert receipt.selected_device_serial == "device-123"
    assert receipt.pushed_scripts is True
    assert receipt.tunnel_requested is True
    assert receipt.post_push_termux_commands == (
        "~/bootstrap.sh",
        "~/install-models.sh",
        "~/start-pro-ai-server.sh",
    )
    assert any(item.label == "Run in Termux" for item in receipt.next_steps)
    assert any("Termux:Widget" in note for note in receipt.notes)


def test_render_setup_receipt_is_deterministic_text():
    receipt = SetupReceipt(
        mode="usb",
        model_profile="professional",
        generated_termux_paths=(Path("generated") / "termux" / "bootstrap.sh",),
        continue_config_path=Path("home") / ".continue" / "config.yaml",
        selected_device_serial="device-123",
        pushed_scripts=True,
        tunnel_requested=True,
        post_push_termux_commands=("~/bootstrap.sh",),
        warnings=("check battery settings",),
        notes=("scripts were generated for inspection",),
    )
    receipt = build_setup_receipt(
        mode=receipt.mode,
        model_plan=model_plan_for_profile(receipt.model_profile),
        written_termux_paths=receipt.generated_termux_paths,
        selected_device_serial=receipt.selected_device_serial,
        pushed_scripts=receipt.pushed_scripts,
        tunnel_requested=receipt.tunnel_requested,
        warnings=receipt.warnings,
        notes=receipt.notes,
    )

    rendered = render_setup_receipt(receipt)

    assert rendered == (
        "Pro AI Server setup receipt\n"
        "\n"
        "Summary\n"
        "- Mode: usb\n"
        "- Model profile: professional\n"
        "- Selected device serial: device-123\n"
        "- Pushed scripts: yes\n"
        "- Tunnel requested: yes\n"
        "\n"
        "Artifacts\n"
        f"- Generated Termux files: {Path('generated') / 'termux' / 'bootstrap.sh'}\n"
        "\n"
        "Post-push Termux commands\n"
        "- none\n"
        "\n"
        "Next steps\n"
        "- USB tunnel: Keep adb reverse tcp:11434 active while using Continue.\n"
        "- Termux scripts: Run the delivered scripts from Termux.\n"
        "\n"
        "Warnings\n"
        "- check battery settings\n"
        "\n"
        "Notes\n"
        "- scripts were generated for inspection\n"
    )
    assert render_setup_receipt(receipt) == rendered


def test_render_setup_receipt_handles_absent_optional_fields():
    rendered = render_setup_receipt(SetupReceipt())

    assert "- Mode: not recorded" in rendered
    assert "- Model profile: not recorded" in rendered
    assert "- Selected device serial: not recorded" in rendered
    assert "Artifacts\n- none\n" in rendered
    assert "Warnings\n- none\n" in rendered
