from datetime import datetime

import yaml

from pro_ai_server.continue_config import (
    api_base_for_mode,
    exposure_warnings,
    render_continue_config_yaml,
    write_continue_config,
)
from pro_ai_server.models import model_plan_for_profile


def test_render_continue_config_yaml_uses_pyyaml_shape():
    plan = model_plan_for_profile("professional")

    rendered = render_continue_config_yaml(plan)
    parsed = yaml.safe_load(rendered)

    assert parsed["name"] == "Pro AI Server Local"
    assert parsed["schema"] == "v1"
    assert parsed["models"][0]["name"] == "Pro AI Chat"
    assert parsed["models"][0]["model"] == "qwen2.5-coder:3b"
    assert parsed["models"][0]["apiBase"] == "http://localhost:11434"
    assert parsed["models"][0]["roles"] == ["chat", "edit", "apply"]
    assert parsed["models"][1]["name"] == "Pro AI Autocomplete"
    assert parsed["models"][1]["model"] == "qwen2.5-coder:1.5b-base"
    assert parsed["models"][1]["roles"] == ["autocomplete"]
    assert rendered.startswith("name: Pro AI Server Local\n")


def test_write_continue_config_creates_directory(tmp_path):
    continue_dir = tmp_path / ".continue"
    plan = model_plan_for_profile("lightweight")

    result = write_continue_config(plan, continue_dir=continue_dir)

    assert result.config_path == continue_dir / "config.yaml"
    assert result.backup_path is None
    assert result.config_path.exists()
    assert continue_dir.exists()


def test_write_continue_config_backs_up_existing_config(tmp_path):
    continue_dir = tmp_path / ".continue"
    continue_dir.mkdir()
    config_path = continue_dir / "config.yaml"
    config_path.write_text("existing: true\n", encoding="utf-8")
    plan = model_plan_for_profile("professional")
    now = datetime(2026, 5, 2, 13, 14, 15)

    result = write_continue_config(plan, continue_dir=continue_dir, now=now)

    assert result.backup_path == continue_dir / "config.yaml.pro-ai-server-backup-20260502-131415"
    assert result.backup_path.read_text(encoding="utf-8") == "existing: true\n"
    assert "qwen2.5-coder:3b" in config_path.read_text(encoding="utf-8")


def test_api_base_for_usb_defaults_to_localhost():
    assert api_base_for_mode("usb") == "http://localhost:11434"


def test_lan_warning_is_pure_helper():
    assert exposure_warnings("lan") == ["LAN mode exposes Ollama to devices on the local network."]
    assert exposure_warnings("usb") == []
