from pro_ai_server.termux_scripts import android_battery_optimization_checklist


def test_android_battery_optimization_checklist_contains_manual_steps():
    checklist = android_battery_optimization_checklist()

    assert checklist[:5] == [
        "Open Android Settings.",
        "Open Apps.",
        "Open Termux.",
        "Open Battery.",
        "Set battery usage to Unrestricted.",
    ]
    assert any("cannot guarantee" in item for item in checklist)
    assert not any("automatically" in item.lower() for item in checklist)
    assert not any("disable battery optimization" in item.lower() for item in checklist)
