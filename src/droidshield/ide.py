from dataclasses import dataclass
import subprocess
import shutil
from typing import Callable


IDE_CLIS: tuple[str, ...] = ("code", "cursor", "codium", "windsurf")
CONTINUE_EXTENSION_ID = "Continue.continue"


@dataclass(frozen=True)
class IdeCli:
    command: str
    path: str | None

    @property
    def installed(self) -> bool:
        return self.path is not None


@dataclass(frozen=True)
class IdeExtensionStatus:
    ide: IdeCli
    extension_id: str
    installed: bool | None
    error: str | None = None


def detect_ide_clis(
    commands: tuple[str, ...] = IDE_CLIS,
    which: Callable[[str], str | None] = shutil.which,
) -> tuple[IdeCli, ...]:
    detected: list[IdeCli] = []
    for command in commands:
        try:
            path = which(command)
        except OSError:
            path = None
        detected.append(IdeCli(command=command, path=path))
    return tuple(detected)


def installed_ide_clis(
    commands: tuple[str, ...] = IDE_CLIS,
    which: Callable[[str], str | None] = shutil.which,
) -> tuple[IdeCli, ...]:
    return tuple(cli for cli in detect_ide_clis(commands, which) if cli.installed)


def list_installed_extensions(
    ide: IdeCli,
    *,
    run: Callable[[list[str]], subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[str, ...]:
    if not ide.path:
        raise ValueError(f"{ide.command} is not installed.")

    result = run([ide.path, "--list-extensions"], capture_output=True, text=True)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "extension listing failed"
        raise OSError(message)

    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def detect_continue_extension_status(
    ide: IdeCli,
    *,
    run: Callable[[list[str]], subprocess.CompletedProcess[str]] = subprocess.run,
) -> IdeExtensionStatus:
    if not ide.installed:
        return IdeExtensionStatus(ide=ide, extension_id=CONTINUE_EXTENSION_ID, installed=None)

    try:
        extensions = list_installed_extensions(ide, run=run)
    except OSError as exc:
        return IdeExtensionStatus(
            ide=ide,
            extension_id=CONTINUE_EXTENSION_ID,
            installed=None,
            error=str(exc),
        )

    installed = any(extension.lower() == CONTINUE_EXTENSION_ID.lower() for extension in extensions)
    return IdeExtensionStatus(ide=ide, extension_id=CONTINUE_EXTENSION_ID, installed=installed)


def install_continue_extension(
    ide: IdeCli,
    *,
    run: Callable[[list[str]], subprocess.CompletedProcess[str]] = subprocess.run,
) -> IdeExtensionStatus:
    if not ide.path:
        raise ValueError(f"{ide.command} is not installed.")

    result = run(
        [ide.path, "--install-extension", CONTINUE_EXTENSION_ID],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "extension installation failed"
        raise OSError(message)

    return detect_continue_extension_status(ide, run=run)
