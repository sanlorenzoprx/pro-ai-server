from pathlib import Path

from pro_ai_server.termux_scripts import generate_termux_scripts, termux_widget_instructions


def test_termux_widget_shortcut_path_and_content():
    bundle = generate_termux_scripts("chat", "autocomplete")
    shortcut = bundle.files[Path("generated/termux/.shortcuts/Start Pro AI Server")]

    assert shortcut.splitlines()[-1] == "~/start-pro-ai-server.sh"
    assert "Termux:Widget" in termux_widget_instructions()
    assert "manually" in termux_widget_instructions()
