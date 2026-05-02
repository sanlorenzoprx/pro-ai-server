from pathlib import Path

from pro_ai_server.packaging import REQUIRED_WINDOWS_PLATFORM_TOOL_FILES
from pro_ai_server.release_validation import (
    ci_includes_required_commands,
    pyproject_includes_embedded_tools_package_data,
    validate_release_layout,
)


def test_release_validation_passes_for_repo_shaped_tree(tmp_path):
    write_valid_repo_tree(tmp_path)

    result = validate_release_layout(tmp_path)

    assert result.ok
    assert result.issues == ()
    assert "passed" in result.summary


def test_release_validation_reports_missing_package_data_entry(tmp_path):
    write_valid_repo_tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.setuptools.package-data]
pro_ai_server = ["py.typed"]
""".strip(),
        encoding="utf-8",
    )

    result = validate_release_layout(tmp_path)

    assert not result.ok
    assert [issue.code for issue in result.issues] == ["missing-embedded-tools-package-data"]
    assert "embedded-tools/**" in result.summary


def test_release_validation_reports_missing_ci_gate(tmp_path):
    write_valid_repo_tree(tmp_path)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        """
name: CI
jobs:
  test:
    steps:
      - run: ruff check .
""".strip(),
        encoding="utf-8",
    )

    result = validate_release_layout(tmp_path)

    assert not result.ok
    assert [issue.code for issue in result.issues] == ["missing-ci-command-pytest"]
    assert "pytest" in result.summary


def test_release_validation_reports_missing_adb_file(tmp_path):
    write_valid_repo_tree(tmp_path)
    missing_file = tmp_path / "embedded-tools" / "windows" / "platform-tools" / "adb.exe"
    missing_file.unlink()

    result = validate_release_layout(tmp_path)

    assert not result.ok
    assert [issue.code for issue in result.issues] == ["missing-source-tree-adb-runtime"]
    assert "adb.exe" in result.summary


def test_fastboot_is_not_required_by_release_validation(tmp_path):
    write_valid_repo_tree(tmp_path)

    result = validate_release_layout(tmp_path)

    assert result.ok
    assert "fastboot" not in result.summary.lower()
    assert "fastboot" not in " ".join(issue.message for issue in result.issues).lower()


def test_pyproject_package_data_helper_finds_embedded_tools_entry():
    pyproject_text = """
[tool.setuptools.package-data]
pro_ai_server = [
  "embedded-tools/**",
]
"""

    assert pyproject_includes_embedded_tools_package_data(pyproject_text)


def test_ci_helper_requires_ruff_and_pytest():
    assert ci_includes_required_commands("run: ruff check .\nrun: pytest")
    assert not ci_includes_required_commands("run: ruff check .")


def write_valid_repo_tree(root: Path) -> None:
    for platform_tools_dir in (
        root / "embedded-tools" / "windows" / "platform-tools",
        root / "src" / "pro_ai_server" / "embedded-tools" / "windows" / "platform-tools",
    ):
        platform_tools_dir.mkdir(parents=True)
        for file_name in REQUIRED_WINDOWS_PLATFORM_TOOL_FILES:
            (platform_tools_dir / file_name).write_text("", encoding="utf-8")

    (root / "pyproject.toml").write_text(
        """
[tool.setuptools.package-data]
pro_ai_server = ["embedded-tools/**"]
""".strip(),
        encoding="utf-8",
    )

    ci_path = root / ".github" / "workflows" / "ci.yml"
    ci_path.parent.mkdir(parents=True)
    ci_path.write_text(
        """
name: CI
jobs:
  test:
    steps:
      - run: ruff check .
      - run: pytest
""".strip(),
        encoding="utf-8",
    )
