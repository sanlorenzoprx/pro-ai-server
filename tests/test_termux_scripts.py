from pathlib import Path

import pytest

from pro_ai_server.termux_scripts import (
    generate_debian_ollama_setup_script,
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
    assert list(bundle.files) == [
        Path("generated/termux/bootstrap.sh"),
        Path("generated/termux/setup-ollama-debian.sh"),
        Path("generated/termux/start-pro-ai-server.sh"),
        Path("generated/termux/install-models.sh"),
        Path("generated/termux/.shortcuts/Start Pro AI Server"),
        Path("generated/termux/ANDROID_OPTIMIZATION_CHECKLIST.txt"),
        Path("generated/termux/TERMUX_WIDGET_INSTRUCTIONS.txt"),
    ]
    assert bundle.files[Path("generated/termux/bootstrap.sh")] == (
        "#!/data/data/com.termux/files/usr/bin/bash\n"
        "set -euo pipefail\n"
        "\n"
        "pkg update -y\n"
        "pkg install -y proot-distro curl termux-api\n"
        "proot-distro install debian\n"
        "\n"
        'echo "Debian is installed."\n'
        'echo "Next, install Ollama inside Debian with:"\n'
        'echo "  proot-distro login debian -- bash /data/data/com.termux/files/home/setup-ollama-debian.sh"\n'
        'echo "Then start the server with:"\n'
        'echo "  ~/start-pro-ai-server.sh"\n'
    )
    assert bundle.files[Path("generated/termux/setup-ollama-debian.sh")] == generate_debian_ollama_setup_script()
    assert "export OLLAMA_HOST=127.0.0.1:11434; ollama serve" in bundle.files[
        Path("generated/termux/start-pro-ai-server.sh")
    ]


def test_bootstrap_and_debian_setup_include_real_ollama_install_path():
    bundle = generate_termux_scripts("chat", "autocomplete")
    bootstrap = bundle.files[Path("generated/termux/bootstrap.sh")]
    debian_setup = bundle.files[Path("generated/termux/setup-ollama-debian.sh")]

    assert "pkg install -y proot-distro curl termux-api" in bootstrap
    assert "proot-distro install debian" in bootstrap
    assert "proot-distro login debian -- bash /data/data/com.termux/files/home/setup-ollama-debian.sh" in bootstrap
    assert "apt-get install -y curl ca-certificates" in debian_setup
    assert "curl -fsSL https://ollama.com/install.sh | sh" in debian_setup


def test_start_script_binds_lan_and_tailscale_to_all_interfaces():
    assert "export OLLAMA_HOST=0.0.0.0:11434; ollama serve" in generate_start_script("lan")
    assert "export OLLAMA_HOST=0.0.0.0:11434; ollama serve" in generate_start_script("tailscale")


def test_start_script_checks_termux_api_and_takes_wake_lock():
    script = generate_start_script("usb")

    assert "command -v termux-wake-lock" in script
    assert "Missing termux-wake-lock from Termux:API." in script
    assert "pkg install termux-api" in script
    assert "Termux:API Android app" in script
    assert "termux-wake-lock" in script
    assert "Unable to acquire wake lock" in script


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


def test_generated_scripts_do_not_claim_to_automate_oem_battery_restrictions():
    bundle = generate_termux_scripts("chat", "autocomplete")
    generated_text = "\n".join(bundle.files.values()).lower()

    assert "disable battery optimization" not in generated_text
    assert "automatically set battery" not in generated_text
    assert "bypass oem" not in generated_text


def test_write_termux_scripts_creates_files(tmp_path):
    bundle = generate_termux_scripts("chat", "autocomplete")

    written = write_termux_scripts(bundle, root=tmp_path)

    assert tmp_path / "generated" / "termux" / "bootstrap.sh" in written
    assert (tmp_path / "generated" / "termux" / "bootstrap.sh").read_text(encoding="utf-8").startswith("#!")


def test_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported Termux mode"):
        generate_start_script("bluetooth")
