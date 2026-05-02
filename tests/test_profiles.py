from pro_ai_server.cli import select_model_profile


def test_lightweight_profile():
    profile = select_model_profile(4)
    assert profile.name == "lightweight"
    assert profile.chat_model == "qwen2.5-coder:1.5b"


def test_professional_profile():
    profile = select_model_profile(8)
    assert profile.name == "professional"
    assert profile.chat_model == "qwen2.5-coder:3b"


def test_max_profile():
    profile = select_model_profile(12)
    assert profile.name == "max"
    assert profile.chat_model == "qwen2.5-coder:7b"
