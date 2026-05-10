from pathlib import Path

from droidshield.termux_scripts import generate_termux_scripts, termux_widget_instructions


def test_termux_widget_shortcut_path_and_content():
    bundle = generate_termux_scripts("chat", "autocomplete")
    shortcut = bundle.files[Path("generated/termux/.shortcuts/Start DroidShield")]
    icon = bundle.files[Path("generated/termux/.shortcuts/icons/Start DroidShield.png")]

    assert shortcut.splitlines()[-1] == "~/start-droidshield.sh"
    assert isinstance(icon, bytes)
    assert icon.startswith(b"\x89PNG")
    assert "Termux:Widget" in termux_widget_instructions()
    assert "~/.shortcuts/icons/Start DroidShield.png" in termux_widget_instructions()
    assert "manually" in termux_widget_instructions()
