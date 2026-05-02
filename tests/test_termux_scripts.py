from pathlib import Path

import pytest

from pro_ai_server.termux_scripts import (
    generate_start_script,
    generate_termux_scripts,
    generate_widget_shortcut_script,
    write_termux_scripts,
)


def test_generates_deterministic_termux_scripts_for_usb_mode():
    bundle = generate_termux_scripts(
        "qwen2.5-coder:3b",
        "qwen2.5-coder:1.5b-base",
        mode="usb",
    )

    assert bundle.ollama_host == "127.0.0.1:11434"
    assert Path("generated/termux/bootstrap.sh") in bundle.files
    assert Path("generated/termux/start-pro-ai-server.sh") in bundle.files
    assert Path("generated/termux/install-models.sh") in bundle.files
    assert bundle.files[Path("generated/termux/bootstrap.sh")] == (
        "#!/data/data/com.termux/files/usr/bin/bash\n"
        "set -euo pipefail\n"
        "\n"
        "pkg update -y\n"
        "pkg install -y proot-distro curl termux-api\n"
        "proot-distro install debian\n"
    )
    assert "export OLLAMA_HOST=127.0.0.1:11434; ollama serve" in bundle.files[
        Path("generated/termux/start-pro-ai-server.sh")
    ]


def test_start_script_binds_lan_and_tailscale_to_all_interfaces():
    assert "export OLLAMA_HOST=0.0.0.0:11434; ollama serve" in generate_start_script("lan")
    assert "export OLLAMA_HOST=0.0.0.0:11434; ollama serve" in generate_start_script("tailscale")


def test_start_script_checks_termux_api_and_takes_wake_lock():
    script = generate_start_script("usb")

    assert "command -v termux-wake-lock" in script
    assert "Missing termux-api" in script
    assert "pkg install termux-api" in script
    assert "termux-wake-lock" in script


def test_install_models_deduplicates_model_pulls():
    bundle = generate_termux_scripts("qwen2.5-coder:3b", "qwen2.5-coder:3b")
    install_script = bundle.files[Path("generated/termux/install-models.sh")]

    assert install_script.count("ollama pull qwen2.5-coder:3b") == 1


def test_widget_shortcut_calls_start_script_and_instructions_are_generated():
    bundle = generate_termux_scripts("chat", "autocomplete")
    shortcut_path = Path("generated/termux/.shortcuts/Start Pro AI Server")

    assert bundle.files[shortcut_path] == generate_widget_shortcut_script()
    assert "~/start-pro-ai-server.sh" in bundle.files[shortcut_path]
    assert "Termux:Widget" in bundle.files[Path("generated/termux/TERMUX_WIDGET_INSTRUCTIONS.txt")]
    assert "manually" in bundle.files[Path("generated/termux/TERMUX_WIDGET_INSTRUCTIONS.txt")]


def test_android_optimization_checklist_does_not_guarantee_oem_behavior():
    bundle = generate_termux_scripts("chat", "autocomplete")
    checklist = bundle.files[Path("generated/termux/ANDROID_OPTIMIZATION_CHECKLIST.txt")]

    assert "Set battery usage to Unrestricted." in checklist
    assert "cannot guarantee" in checklist
    assert "OEM" in checklist


def test_write_termux_scripts_creates_files(tmp_path):
    bundle = generate_termux_scripts("chat", "autocomplete")

    written = write_termux_scripts(bundle, root=tmp_path)

    assert tmp_path / "generated" / "termux" / "bootstrap.sh" in written
    assert (tmp_path / "generated" / "termux" / "bootstrap.sh").read_text(encoding="utf-8").startswith("#!")


def test_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported Termux mode"):
        generate_start_script("bluetooth")
