from __future__ import annotations

from dataclasses import dataclass


Command = tuple[str, ...]

TERMUX_PACKAGE = "com.termux"
TERMUX_API_PACKAGE = "com.termux.api"
TERMUX_HOME = "/data/data/com.termux/files/home"


@dataclass(frozen=True)
class TermuxReadinessCheck:
    name: str
    ok: bool
    warning: str | None = None
    instruction: str | None = None


@dataclass(frozen=True)
class TermuxReadinessResult:
    termux_installed: TermuxReadinessCheck
    termux_api_installed: TermuxReadinessCheck
    home_initialized: TermuxReadinessCheck
    version_hint: str | None = None

    @property
    def checks(self) -> tuple[TermuxReadinessCheck, ...]:
        return (
            self.termux_installed,
            self.termux_api_installed,
            self.home_initialized,
        )

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(check.warning for check in self.checks if check.warning)

    @property
    def instructions(self) -> tuple[str, ...]:
        return tuple(check.instruction for check in self.checks if check.instruction)


def assess_termux_readiness(
    termux_pm_path_output: str,
    termux_api_pm_path_output: str,
    home_initialized_output: str,
    package_info_output: str | None = None,
) -> TermuxReadinessResult:
    termux_installed = _termux_installed_check(termux_pm_path_output)
    termux_api_installed = _termux_api_installed_check(termux_api_pm_path_output)
    home_initialized = _home_initialized_check(home_initialized_output)

    return TermuxReadinessResult(
        termux_installed=termux_installed,
        termux_api_installed=termux_api_installed,
        home_initialized=home_initialized,
        version_hint=parse_termux_version_hint(package_info_output or ""),
    )


def build_termux_readiness_commands(serial: str | None = None) -> tuple[Command, ...]:
    return (
        build_pm_path_command(TERMUX_PACKAGE, serial=serial),
        build_pm_path_command(TERMUX_API_PACKAGE, serial=serial),
        build_termux_home_check_command(serial=serial),
    )


def build_termux_package_info_command(serial: str | None = None) -> Command:
    return _adb_command(("shell", "dumpsys", "package", TERMUX_PACKAGE), serial=serial)


def build_pm_path_command(package_name: str, serial: str | None = None) -> Command:
    return _adb_command(("shell", "pm", "path", package_name), serial=serial)


def build_termux_home_check_command(serial: str | None = None) -> Command:
    return _adb_command(
        ("shell", "test", "-d", TERMUX_HOME, "&&", "echo", "yes", "||", "echo", "no"),
        serial=serial,
    )


def parse_pm_path_installed(output: str) -> bool:
    return any(line.strip().startswith("package:") for line in output.splitlines())


def parse_home_initialized(output: str) -> bool:
    return any(line.strip().lower() == "yes" for line in output.splitlines())


def parse_termux_version_hint(package_info_output: str) -> str | None:
    for line in package_info_output.splitlines():
        stripped = line.strip()
        if stripped.startswith("versionName="):
            return stripped.removeprefix("versionName=").strip() or None
    return None


def _termux_installed_check(output: str) -> TermuxReadinessCheck:
    if parse_pm_path_installed(output):
        return TermuxReadinessCheck(name="Termux installed", ok=True)
    return TermuxReadinessCheck(
        name="Termux installed",
        ok=False,
        warning="Termux is not installed.",
        instruction="Install Termux from F-Droid or GitHub, then open it once before continuing.",
    )


def _termux_api_installed_check(output: str) -> TermuxReadinessCheck:
    if parse_pm_path_installed(output):
        return TermuxReadinessCheck(name="Termux:API installed", ok=True)
    return TermuxReadinessCheck(
        name="Termux:API installed",
        ok=False,
        warning="Termux:API is not installed.",
        instruction="Install Termux:API, then run the bootstrap script afterward.",
    )


def _home_initialized_check(output: str) -> TermuxReadinessCheck:
    if parse_home_initialized(output):
        return TermuxReadinessCheck(name="Termux home initialized", ok=True)
    return TermuxReadinessCheck(
        name="Termux home initialized",
        ok=False,
        warning="Termux home is not initialized.",
        instruction="Open Termux once on the phone, then rerun the readiness check.",
    )


def _adb_command(args: tuple[str, ...], serial: str | None) -> Command:
    if serial:
        return ("adb", "-s", serial, *args)
    return ("adb", *args)
