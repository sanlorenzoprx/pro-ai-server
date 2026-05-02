from pro_ai_server.hardware import assess_device_profile, select_model_profile


def test_lightweight_profile_under_5gb():
    profile = select_model_profile(4.99)

    assert profile.name == "lightweight"
    assert profile.chat_model == "qwen2.5-coder:1.5b"
    assert profile.autocomplete_model == "qwen2.5-coder:0.5b"
    assert profile.status == "experimental"


def test_professional_profile_from_5gb_to_under_9gb():
    profile = select_model_profile(5)

    assert profile.name == "professional"
    assert profile.chat_model == "qwen2.5-coder:3b"
    assert profile.autocomplete_model == "qwen2.5-coder:1.5b-base"
    assert profile.status == "recommended"


def test_max_profile_at_9gb_and_above():
    profile = select_model_profile(9)

    assert profile.name == "max"
    assert profile.chat_model == "qwen2.5-coder:7b"
    assert profile.autocomplete_model == "qwen2.5-coder:1.5b-base"
    assert profile.status == "high-memory"


def test_storage_under_8gb_warns_before_download():
    device = assess_device_profile(
        serial="serial",
        manufacturer="maker",
        model="model",
        android_version="14",
        abi="arm64-v8a",
        ram_gb=8,
        free_storage_gb=7.99,
    )

    assert device.warnings == ("Free storage is under 8 GB; warn before downloading models.",)


def test_storage_under_4gb_blocks_full_install_warning():
    device = assess_device_profile(
        serial="serial",
        manufacturer="maker",
        model="model",
        android_version="14",
        abi="arm64-v8a",
        ram_gb=8,
        free_storage_gb=3.99,
    )

    assert device.warnings == (
        "Free storage is under 4 GB; block full install and use lightweight mode or manual cleanup.",
    )


def test_non_arm64_abi_warns():
    device = assess_device_profile(
        serial="serial",
        manufacturer="maker",
        model="model",
        android_version="14",
        abi="armeabi-v7a",
        ram_gb=8,
        free_storage_gb=10,
    )

    assert device.warnings == ("Non-arm64 ABI detected; 32-bit Android devices are not recommended.",)
