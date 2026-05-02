import pytest
import yaml

from pro_ai_server.continue_config import api_base_for_mode, render_continue_config_yaml
from pro_ai_server.models import model_plan_for_profile


def test_tailscale_hostname_is_accepted_for_api_base():
    assert api_base_for_mode("tailscale", "pro-ai-phone") == "http://pro-ai-phone:11434"


def test_tailscale_ip_is_accepted_for_api_base():
    assert api_base_for_mode("tailscale", "100.101.102.103") == "http://100.101.102.103:11434"


def test_tailscale_mode_requires_host():
    with pytest.raises(ValueError, match="requires a host"):
        api_base_for_mode("tailscale")


def test_lan_mode_requires_host():
    with pytest.raises(ValueError, match="requires a host"):
        api_base_for_mode("lan")


def test_tailscale_continue_config_changes_api_base():
    plan = model_plan_for_profile("professional")
    rendered = render_continue_config_yaml(plan, mode="tailscale", host="pro-ai-phone")
    parsed = yaml.safe_load(rendered)

    assert parsed["models"][0]["apiBase"] == "http://pro-ai-phone:11434"
    assert parsed["models"][1]["apiBase"] == "http://pro-ai-phone:11434"
