from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pro_ai_server.packaging import validate_windows_platform_tools_layouts


PYPROJECT_PATH = Path("pyproject.toml")
CI_WORKFLOW_PATH = Path(".github") / "workflows" / "ci.yml"
PACKAGE_DATA_PATTERN = "embedded-tools/**"
REQUIRED_CI_COMMANDS: tuple[str, ...] = ("ruff check .", "pytest")


@dataclass(frozen=True)
class ReleaseValidationIssue:
    code: str
    message: str
    path: Path | None = None


@dataclass(frozen=True)
class ReleaseValidationResult:
    issues: tuple[ReleaseValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues

    @property
    def summary(self) -> str:
        if self.ok:
            return "Release validation passed: ADB runtime files, package data, and CI gates are present."

        issue_count = len(self.issues)
        issue_word = "issue" if issue_count == 1 else "issues"
        issue_messages = "; ".join(issue.message for issue in self.issues)
        return f"Release validation failed with {issue_count} {issue_word}: {issue_messages}."


def pyproject_includes_embedded_tools_package_data(pyproject_text: str) -> bool:
    package_data_section = _read_toml_section(pyproject_text, "tool.setuptools.package-data")
    if not package_data_section:
        return False

    current_key: str | None = None
    for line in package_data_section:
        stripped = _strip_toml_comment(line).strip()
        if not stripped:
            continue

        if "=" in stripped:
            current_key, value = (part.strip() for part in stripped.split("=", maxsplit=1))
            if current_key == "pro_ai_server" and PACKAGE_DATA_PATTERN in value:
                return True
            if "]" in value:
                current_key = None
            continue

        if current_key == "pro_ai_server" and PACKAGE_DATA_PATTERN in stripped:
            return True
        if current_key == "pro_ai_server" and "]" in stripped:
            current_key = None

    return False


def ci_includes_required_commands(ci_text: str) -> bool:
    return all(command in ci_text for command in REQUIRED_CI_COMMANDS)


def validate_release_layout(repo_root: str | Path) -> ReleaseValidationResult:
    root = Path(repo_root)
    issues: list[ReleaseValidationIssue] = []

    platform_tools_validation = validate_windows_platform_tools_layouts(root)
    for layout_name, layout_result in (
        ("source tree", platform_tools_validation.source_tree),
        ("packaged", platform_tools_validation.packaged),
    ):
        if not layout_result.ok:
            issues.append(
                ReleaseValidationIssue(
                    code=f"missing-{layout_name.replace(' ', '-')}-adb-runtime",
                    message=(
                        f"Missing required ADB runtime files in {layout_name} layout at "
                        f"{layout_result.platform_tools_dir}: {', '.join(layout_result.missing_files)}"
                    ),
                    path=layout_result.platform_tools_dir,
                )
            )

    pyproject_path = root / PYPROJECT_PATH
    if not pyproject_path.is_file():
        issues.append(
            ReleaseValidationIssue(
                code="missing-pyproject",
                message=f"Missing {PYPROJECT_PATH}.",
                path=pyproject_path,
            )
        )
    elif not pyproject_includes_embedded_tools_package_data(pyproject_path.read_text(encoding="utf-8")):
        issues.append(
            ReleaseValidationIssue(
                code="missing-embedded-tools-package-data",
                message=f"{PYPROJECT_PATH} must include package data for {PACKAGE_DATA_PATTERN}.",
                path=pyproject_path,
            )
        )

    ci_path = root / CI_WORKFLOW_PATH
    if not ci_path.is_file():
        issues.append(
            ReleaseValidationIssue(
                code="missing-ci-workflow",
                message=f"Missing GitHub Actions workflow at {CI_WORKFLOW_PATH}.",
                path=ci_path,
            )
        )
    else:
        ci_text = ci_path.read_text(encoding="utf-8")
        for command in REQUIRED_CI_COMMANDS:
            if command not in ci_text:
                issues.append(
                    ReleaseValidationIssue(
                        code=f"missing-ci-command-{command.split()[0]}",
                        message=f"{CI_WORKFLOW_PATH} must run `{command}`.",
                        path=ci_path,
                    )
                )

    return ReleaseValidationResult(issues=tuple(issues))


def _read_toml_section(toml_text: str, section_name: str) -> tuple[str, ...]:
    section_header = f"[{section_name}]"
    in_section = False
    section_lines: list[str] = []

    for line in toml_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_section:
                break
            in_section = stripped == section_header
            continue
        if in_section:
            section_lines.append(line)

    return tuple(section_lines)


def _strip_toml_comment(line: str) -> str:
    return line.split("#", maxsplit=1)[0]
