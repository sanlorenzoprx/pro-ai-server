from pathlib import Path

from droidshield.tailscale import TAILSCALE_ANDROID_PACKAGE, TAILSCALE_WINGET_ID
from droidshield.tailscale import build_tailscale_install_plan
from droidshield.tailscale import tailscale_android_installed
from droidshield.tailscale import tailscale_host_installed


def test_build_tailscale_install_plan_uses_winget_and_adb_serial():
    apk = Path("tailscale.apk")

    plan = build_tailscale_install_plan("adb", serial="ABC123", android_apk=apk)

    assert plan.host_check_command == ("tailscale", "version")
    assert plan.host_install_command == ("winget", "install", "--id", TAILSCALE_WINGET_ID, "--exact")
    assert plan.android_check_command == ("adb", "-s", "ABC123", "shell", "pm", "path", TAILSCALE_ANDROID_PACKAGE)
    assert plan.android_install_command == ("adb", "-s", "ABC123", "install", "-r", str(apk))
    assert plan.android_open_store_command == (
        "adb",
        "-s",
        "ABC123",
        "shell",
        "am",
        "start",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        "market://details?id=com.tailscale.ipn",
    )


def test_tailscale_android_installed_detects_pm_path_output():
    assert tailscale_android_installed("package:/data/app/com.tailscale.ipn/base.apk")
    assert not tailscale_android_installed("Error: package not found")


def test_tailscale_host_installed_requires_version_output():
    assert tailscale_host_installed("1.96.4")
    assert not tailscale_host_installed("")
