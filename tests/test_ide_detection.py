from pro_ai_server.ide import IDE_CLIS, detect_ide_clis, installed_ide_clis


def test_detects_known_ide_clis_without_crashing_when_missing():
    found = {"code": "C:/bin/code.cmd", "windsurf": "C:/bin/windsurf.cmd"}

    detected = detect_ide_clis(which=lambda command: found.get(command))

    assert tuple(cli.command for cli in detected) == IDE_CLIS
    assert {cli.command: cli.path for cli in detected} == {
        "code": "C:/bin/code.cmd",
        "cursor": None,
        "codium": None,
        "windsurf": "C:/bin/windsurf.cmd",
    }


def test_missing_cli_lookup_errors_do_not_crash():
    def broken_which(command):
        if command == "cursor":
            raise OSError("lookup failed")
        return None

    detected = detect_ide_clis(which=broken_which)

    assert len(detected) == 4
    assert all(cli.path is None for cli in detected)


def test_installed_ide_clis_filters_missing_entries():
    found = {"codium": "C:/bin/codium.cmd"}

    detected = installed_ide_clis(which=lambda command: found.get(command))

    assert tuple(cli.command for cli in detected) == ("codium",)
