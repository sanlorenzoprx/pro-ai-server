from pathlib import Path

from pro_ai_server.termux_scripts import generate_termux_scripts, termux_widget_instructions


def test_termux_widget_shortcut_path_and_content():
    bundle = generate_termux_scripts("chat", "autocomplete")
    shortcut = bundle.files[Path("generated/termux/.shortcuts/Start Pro AI Server")]
    icon = bundle.files[Path("generated/termux/.shortcuts/icons/Start Pro AI Server.png")]

    assert shortcut.splitlines()[-1] == "~/start-pro-ai-server.sh"
    assert isinstance(icon, bytes)
    assert icon.startswith(b"\x89PNG")
    assert "Termux:Widget" in termux_widget_instructions()
    assert "~/.shortcuts/icons/Start Pro AI Server.png" in termux_widget_instructions()
    assert "manually" in termux_widget_instructions()
