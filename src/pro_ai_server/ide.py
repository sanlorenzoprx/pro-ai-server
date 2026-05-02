from dataclasses import dataclass
import shutil
from typing import Callable


IDE_CLIS: tuple[str, ...] = ("code", "cursor", "codium", "windsurf")


@dataclass(frozen=True)
class IdeCli:
    command: str
    path: str | None

    @property
    def installed(self) -> bool:
        return self.path is not None


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
