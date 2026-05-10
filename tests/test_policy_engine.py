from pathlib import Path

from droidshield.policy import default_policy, load_policy, write_default_policy


def test_default_policy_allows_known_safe_command() -> None:
    decision = default_policy().evaluate_command("git status")

    assert decision.allowed is True
    assert decision.matched_rule == "allowed-command:git"


def test_default_policy_blocks_sensitive_command_pattern() -> None:
    decision = default_policy().evaluate_command("sudo rm -rf /")

    assert decision.allowed is False
    assert "sudo" in decision.reason


def test_default_policy_blocks_sensitive_path() -> None:
    decision = default_policy().evaluate_command("python read.py ~/.ssh/id_rsa")

    assert decision.allowed is False
    assert "~/.ssh" in decision.reason


def test_policy_file_round_trip(tmp_path: Path) -> None:
    path = write_default_policy(tmp_path / "policy.json")
    policy = load_policy(path)

    assert policy.name == "default"
    assert "git" in policy.allowed_commands
    assert "/etc/passwd" in policy.blocked_paths
    assert "github.com" in policy.network_allowlist
    assert policy.network_whitelist == policy.network_allowlist


def test_policy_loader_accepts_handoff_network_allowlist(tmp_path: Path) -> None:
    path = tmp_path / "strict.policy.json"
    path.write_text(
        """
{
  "name": "strict",
  "allowed_commands": ["git"],
  "blocked_commands": ["sudo"],
  "blocked_paths": ["~/.ssh"],
  "network_allowlist": ["github.com"],
  "max_runtime_seconds": 60,
  "max_output_bytes": 1000,
  "allow_shell": true,
  "require_working_directory": true
}
""".strip(),
        encoding="utf-8",
    )

    policy = load_policy(path)

    assert policy.name == "strict"
    assert policy.network_allowlist == ("github.com",)
    assert policy.max_runtime_seconds == 60
