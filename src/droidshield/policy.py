from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_ALLOWED_COMMANDS = (
    "git",
    "npm",
    "pnpm",
    "python",
    "pytest",
    "pip",
    "ruff",
    "node",
    "adb",
)

DEFAULT_BLOCKED_COMMANDS = (
    "sudo",
    "su",
    "rm -rf /",
    "mkfs",
    "dd",
    "shutdown",
    "reboot",
)

DEFAULT_BLOCKED_PATHS = (
    "~/.ssh",
    "~/.aws",
    "~/.config/gcloud",
    "/etc/passwd",
    "/data/data",
    "/data/data/com.termux/files/home/.ssh",
)


@dataclass(frozen=True)
class CommandDecision:
    allowed: bool
    reason: str
    matched_rule: str | None = None


@dataclass(frozen=True)
class DroidShieldPolicy:
    name: str = "default"
    allowed_commands: tuple[str, ...] = DEFAULT_ALLOWED_COMMANDS
    blocked_commands: tuple[str, ...] = DEFAULT_BLOCKED_COMMANDS
    blocked_paths: tuple[str, ...] = DEFAULT_BLOCKED_PATHS
    network_allowlist: tuple[str, ...] = ("github.com", "registry.npmjs.org", "pypi.org", "files.pythonhosted.org")
    max_runtime_seconds: int = 900
    max_output_bytes: int = 250_000
    allow_shell: bool = True
    require_working_directory: bool = True
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def network_whitelist(self) -> tuple[str, ...]:
        return self.network_allowlist

    def evaluate_command(self, command: str) -> CommandDecision:
        normalized = " ".join(command.strip().split())
        if not normalized:
            return CommandDecision(False, "Command is empty.", "empty-command")

        lowered = normalized.lower()
        for blocked in self.blocked_commands:
            if blocked.lower() in lowered:
                return CommandDecision(False, f"Blocked command pattern: {blocked}", f"blocked-command:{blocked}")

        for path in self.blocked_paths:
            if path.lower() in lowered:
                return CommandDecision(False, f"Blocked sensitive path: {path}", f"blocked-path:{path}")

        first_token = normalized.split()[0]
        if first_token not in self.allowed_commands:
            return CommandDecision(False, f"Command is not allowlisted: {first_token}", f"not-allowlisted:{first_token}")

        return CommandDecision(True, "Command allowed by policy.", f"allowed-command:{first_token}")


def default_policy() -> DroidShieldPolicy:
    return DroidShieldPolicy(metadata={"profile": "mvp-default"})


def load_policy(path: Path) -> DroidShieldPolicy:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Policy file must contain a JSON object.")

    network_allowlist = payload.get("network_allowlist", payload.get("network_whitelist", ()))
    return DroidShieldPolicy(
        name=str(payload.get("name", path.stem)),
        allowed_commands=tuple(payload.get("allowed_commands", DEFAULT_ALLOWED_COMMANDS)),
        blocked_commands=tuple(payload.get("blocked_commands", DEFAULT_BLOCKED_COMMANDS)),
        blocked_paths=tuple(payload.get("blocked_paths", DEFAULT_BLOCKED_PATHS)),
        network_allowlist=tuple(network_allowlist),
        max_runtime_seconds=int(payload.get("max_runtime_seconds", 900)),
        max_output_bytes=int(payload.get("max_output_bytes", 250_000)),
        allow_shell=bool(payload.get("allow_shell", True)),
        require_working_directory=bool(payload.get("require_working_directory", True)),
        metadata={str(key): str(value) for key, value in dict(payload.get("metadata", {})).items()},
    )


def write_default_policy(path: Path) -> Path:
    policy = default_policy()
    payload = {
        "name": policy.name,
        "allowed_commands": list(policy.allowed_commands),
        "blocked_commands": list(policy.blocked_commands),
        "blocked_paths": list(policy.blocked_paths),
        "network_allowlist": list(policy.network_allowlist),
        "max_runtime_seconds": policy.max_runtime_seconds,
        "max_output_bytes": policy.max_output_bytes,
        "allow_shell": policy.allow_shell,
        "require_working_directory": policy.require_working_directory,
        "metadata": policy.metadata,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
