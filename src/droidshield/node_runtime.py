from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AndroidSandboxNode:
    node_id: str
    serial: str | None = None
    transport: str = "usb"
    labels: tuple[str, ...] = ("termux", "proot-debian")
    capabilities: tuple[str, ...] = ("shell", "files", "git", "python", "node")
    quarantined: bool = False

    def can_run(self, required_capabilities: tuple[str, ...]) -> bool:
        if self.quarantined:
            return False
        return all(capability in self.capabilities for capability in required_capabilities)


def default_node(serial: str | None = None) -> AndroidSandboxNode:
    node_id = serial or "android-node-01"
    return AndroidSandboxNode(node_id=node_id, serial=serial)
