from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


VALID_MODES = {"usb", "lan", "tailscale"}
USB_OLLAMA_HOST = "127.0.0.1:11434"
NETWORK_OLLAMA_HOST = "0.0.0.0:11434"
DEFAULT_SCRIPT_DIR = Path("generated") / "termux"
WIDGET_SHORTCUT_PATH = Path(".shortcuts") / "Start Pro AI Server"
DEBIAN_OLLAMA_SETUP_SCRIPT = "setup-ollama-debian.sh"


@dataclass(frozen=True)
class TermuxScriptBundle:
    mode: str
    ollama_host: str
    files: Mapping[Path, str]


def ollama_host_for_mode(mode: str) -> str:
    normalized = mode.lower()
    if normalized not in VALID_MODES:
        modes = ", ".join(sorted(VALID_MODES))
        raise ValueError(f"Unsupported Termux mode '{mode}'. Expected one of: {modes}.")
    if normalized == "usb":
        return USB_OLLAMA_HOST
    return NETWORK_OLLAMA_HOST


def android_battery_optimization_checklist() -> list[str]:
    return [
        "Open Android Settings.",
        "Open Apps.",
        "Open Termux.",
        "Open Battery.",
        "Set battery usage to Unrestricted.",
        "OEM battery management can still vary; this checklist reduces interruptions but cannot guarantee background behavior on every phone.",
    ]


def termux_widget_instructions() -> str:
    return (
        "Install Termux:Widget, then place the generated shortcut at "
        "~/.shortcuts/Start Pro AI Server. Add the Termux:Widget shortcut "
        "manually to the Android home screen and choose Start Pro AI Server."
    )


def generate_bootstrap_script() -> str:
    return "\n".join(
        [
            "#!/data/data/com.termux/files/usr/bin/bash",
            "set -euo pipefail",
            "",
            "pkg update -y",
            "pkg install -y proot-distro curl termux-api",
            "proot-distro install debian",
            "",
            'echo "Debian is installed."',
            'echo "Next, install Ollama inside Debian with:"',
            f'echo "  proot-distro login debian -- bash /data/data/com.termux/files/home/{DEBIAN_OLLAMA_SETUP_SCRIPT}"',
            'echo "Then start the server with:"',
            'echo "  ~/start-pro-ai-server.sh"',
            "",
        ]
    )


def generate_debian_ollama_setup_script() -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "apt-get update",
            "apt-get install -y curl ca-certificates",
            "curl -fsSL https://ollama.com/install.sh | sh",
            "",
            'echo "Ollama installed inside Debian."',
            'echo "Exit Debian, then run ~/start-pro-ai-server.sh from Termux."',
            "",
        ]
    )


def generate_start_script(mode: str = "usb") -> str:
    ollama_host = ollama_host_for_mode(mode)
    return "\n".join(
        [
            "#!/data/data/com.termux/files/usr/bin/bash",
            "set -euo pipefail",
            "",
            "if ! command -v termux-wake-lock >/dev/null 2>&1; then",
            '  echo "Missing termux-wake-lock from Termux:API." >&2',
            '  echo "Install it in Termux with: pkg install termux-api" >&2',
            '  echo "Also install the Termux:API Android app from the same source as Termux." >&2',
            "  exit 1",
            "fi",
            "",
            "if ! termux-wake-lock; then",
            '  echo "Unable to acquire wake lock through Termux:API / termux-wake-lock." >&2',
            '  echo "Confirm the Termux:API Android app is installed and accessible." >&2',
            "  exit 1",
            "fi",
            "",
            f"proot-distro login debian -- bash -lc 'export OLLAMA_HOST={ollama_host}; ollama serve'",
            "",
        ]
    )


def generate_install_models_script(chat_model: str, autocomplete_model: str) -> str:
    models = list(dict.fromkeys([chat_model, autocomplete_model]))
    commands = [f"proot-distro login debian -- bash -lc 'ollama pull {model}'" for model in models]
    return "\n".join(
        [
            "#!/data/data/com.termux/files/usr/bin/bash",
            "set -euo pipefail",
            "",
            *commands,
            "",
        ]
    )


def generate_widget_shortcut_script() -> str:
    return "\n".join(
        [
            "#!/data/data/com.termux/files/usr/bin/bash",
            "set -euo pipefail",
            "",
            "~/start-pro-ai-server.sh",
            "",
        ]
    )


def generate_termux_scripts(
    chat_model: str,
    autocomplete_model: str,
    mode: str = "usb",
    script_dir: Path = DEFAULT_SCRIPT_DIR,
) -> TermuxScriptBundle:
    normalized = mode.lower()
    ollama_host = ollama_host_for_mode(normalized)
    files = {
        script_dir / "bootstrap.sh": generate_bootstrap_script(),
        script_dir / DEBIAN_OLLAMA_SETUP_SCRIPT: generate_debian_ollama_setup_script(),
        script_dir / "start-pro-ai-server.sh": generate_start_script(normalized),
        script_dir / "install-models.sh": generate_install_models_script(chat_model, autocomplete_model),
        script_dir / WIDGET_SHORTCUT_PATH: generate_widget_shortcut_script(),
        script_dir / "ANDROID_OPTIMIZATION_CHECKLIST.txt": "\n".join(android_battery_optimization_checklist()) + "\n",
        script_dir / "TERMUX_WIDGET_INSTRUCTIONS.txt": termux_widget_instructions() + "\n",
    }
    return TermuxScriptBundle(mode=normalized, ollama_host=ollama_host, files=files)


def write_termux_scripts(bundle: TermuxScriptBundle, root: Path = Path(".")) -> list[Path]:
    written: list[Path] = []
    for relative_path, content in bundle.files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    return written
