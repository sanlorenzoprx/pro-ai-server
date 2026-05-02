import pytest

from pro_ai_server.models import ModelPlan, model_plan_for_profile, model_plan_for_ram


def test_lightweight_model_plan():
    plan = model_plan_for_profile("lightweight")

    assert plan.status == "experimental"
    assert plan.chat_model == "qwen2.5-coder:1.5b"
    assert plan.autocomplete_model == "qwen2.5-coder:0.5b"
    assert plan.chat_label == "Pro AI Chat"
    assert plan.autocomplete_label == "Pro AI Autocomplete"
    assert plan.ollama_pull_commands == (
        "ollama pull qwen2.5-coder:1.5b",
        "ollama pull qwen2.5-coder:0.5b",
    )


def test_professional_model_plan():
    plan = model_plan_for_profile("professional")

    assert plan.status == "recommended"
    assert plan.chat_model == "qwen2.5-coder:3b"
    assert plan.autocomplete_model == "qwen2.5-coder:1.5b-base"
    assert plan.ollama_pull_commands == (
        "ollama pull qwen2.5-coder:3b",
        "ollama pull qwen2.5-coder:1.5b-base",
    )


def test_max_model_plan():
    plan = model_plan_for_profile("max")

    assert plan.status == "high-memory"
    assert plan.chat_model == "qwen2.5-coder:7b"
    assert plan.autocomplete_model == "qwen2.5-coder:1.5b-base"


def test_model_plan_for_ram_thresholds():
    assert model_plan_for_ram(4.99).profile == "lightweight"
    assert model_plan_for_ram(5).profile == "professional"
    assert model_plan_for_ram(8.99).profile == "professional"
    assert model_plan_for_ram(9).profile == "max"


def test_ollama_pull_commands_are_deduplicated():
    plan = ModelPlan(
        profile="test",
        status="test",
        chat_model="qwen2.5-coder:1.5b",
        autocomplete_model="qwen2.5-coder:1.5b",
    )

    assert plan.ollama_pull_commands == ("ollama pull qwen2.5-coder:1.5b",)


def test_unknown_model_profile_is_rejected():
    with pytest.raises(ValueError, match="Unknown model profile"):
        model_plan_for_profile("tiny")
