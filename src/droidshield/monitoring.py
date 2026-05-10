from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    task_id: str
    agent: str
    node: str
    message: str
    severity: str = "info"
    timestamp: str = ""
    details: dict[str, Any] | None = None

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        if not record["timestamp"]:
            record["timestamp"] = datetime.now(timezone.utc).isoformat()
        if record["details"] is None:
            record["details"] = {}
        return record


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: AuditEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_record(), sort_keys=True) + "\n")

    def tail(self, limit: int = 50) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        lines = self.path.read_text(encoding="utf-8").splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
        return tuple(records)
