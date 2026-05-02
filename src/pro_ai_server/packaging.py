from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REQUIRED_WINDOWS_PLATFORM_TOOL_FILES: tuple[str, ...] = (
    "adb.exe",
    "AdbWinApi.dll",
    "AdbWinUsbApi.dll",
)

SOURCE_TREE_WINDOWS_PLATFORM_TOOLS = Path("embedded-tools") / "windows" / "platform-tools"
PACKAGED_WINDOWS_PLATFORM_TOOLS = (
    Path("src") / "pro_ai_server" / "embedded-tools" / "windows" / "platform-tools"
)


@dataclass(frozen=True)
class PlatformToolsValidationResult:
    platform_tools_dir: Path
    present_files: tuple[str, ...]
    missing_files: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_files

    @property
    def message(self) -> str:
        if self.ok:
            return (
                "Windows Platform Tools ADB runtime is ready at "
                f"{self.platform_tools_dir}; found {format_file_list(self.present_files)}."
            )
        return (
            "Windows Platform Tools ADB runtime is incomplete at "
            f"{self.platform_tools_dir}; missing {format_file_list(self.missing_files)}."
        )


@dataclass(frozen=True)
class PlatformToolsLayoutValidation:
    source_tree: PlatformToolsValidationResult
    packaged: PlatformToolsValidationResult

    @property
    def ok(self) -> bool:
        return self.source_tree.ok and self.packaged.ok

    @property
    def message(self) -> str:
        if self.ok:
            return "Bundled Windows Platform Tools ADB runtime files are present in both layouts."
        return "Bundled Windows Platform Tools ADB runtime files are missing from one or more layouts."


def validate_windows_platform_tools_dir(platform_tools_dir: str | Path) -> PlatformToolsValidationResult:
    directory = Path(platform_tools_dir)
    present_files = tuple(
        file_name for file_name in REQUIRED_WINDOWS_PLATFORM_TOOL_FILES if (directory / file_name).is_file()
    )
    missing_files = tuple(
        file_name for file_name in REQUIRED_WINDOWS_PLATFORM_TOOL_FILES if file_name not in present_files
    )
    return PlatformToolsValidationResult(
        platform_tools_dir=directory,
        present_files=present_files,
        missing_files=missing_files,
    )


def validate_windows_platform_tools_layouts(base_path: str | Path) -> PlatformToolsLayoutValidation:
    base = Path(base_path)
    return PlatformToolsLayoutValidation(
        source_tree=validate_windows_platform_tools_dir(base / SOURCE_TREE_WINDOWS_PLATFORM_TOOLS),
        packaged=validate_windows_platform_tools_dir(base / PACKAGED_WINDOWS_PLATFORM_TOOLS),
    )


def format_file_list(file_names: tuple[str, ...]) -> str:
    if not file_names:
        return "no files"
    if len(file_names) == 1:
        return file_names[0]
    if len(file_names) == 2:
        return f"{file_names[0]} and {file_names[1]}"
    return ", ".join(file_names[:-1]) + f", and {file_names[-1]}"
