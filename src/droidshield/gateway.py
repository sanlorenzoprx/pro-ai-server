from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from droidshield.monitoring import AuditEvent, AuditLog
from droidshield.node_runtime import AndroidSandboxNode, default_node
from droidshield.policy import CommandDecision, DroidShieldPolicy, default_policy


@dataclass(frozen=True)
class SandboxTask:
    agent: str
    command: str
    objective: str = ""
    node: str | None = None
    required_capabilities: tuple[str, ...] = ("shell",)
    task_id: str = ""

    def with_id(self) -> SandboxTask:
        if self.task_id:
            return self
        return SandboxTask(
            agent=self.agent,
            command=self.command,
            objective=self.objective,
            node=self.node,
            required_capabilities=self.required_capabilities,
            task_id=f"task-{uuid4().hex[:12]}",
        )


@dataclass(frozen=True)
class SandboxReceipt:
    task_id: str
    accepted: bool
    status: str
    agent: str
    node: str
    command: str
    decision: CommandDecision
    created_at: str


@dataclass(frozen=True)
class NodeRegistration:
    node_id: str
    device_model: str
    runtime: str
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class GatewayJob:
    job_id: str
    status: str
    agent: str
    command: str
    node: str
    repo: str = ""
    task_type: str = "shell"
    working_dir: str = ""
    policy: str = "default"
    timeout_seconds: int = 120
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    policy_violations: tuple[str, ...] = ()
    kill_reason: str = ""
    created_at: str = ""

    def to_api_response(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "policy_violations": list(self.policy_violations),
        }


class SandboxGateway:
    def __init__(
        self,
        *,
        policy: DroidShieldPolicy | None = None,
        nodes: tuple[AndroidSandboxNode, ...] | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self.policy = policy or default_policy()
        self.nodes = nodes or (default_node(),)
        self.audit_log = audit_log or AuditLog(Path("logs") / "droidshield-audit.jsonl")
        self.jobs: dict[str, GatewayJob] = {}

    def register_node(self, registration: NodeRegistration) -> AndroidSandboxNode:
        node = AndroidSandboxNode(
            node_id=registration.node_id,
            labels=(registration.runtime, registration.device_model),
            capabilities=registration.capabilities,
        )
        existing = tuple(candidate for candidate in self.nodes if candidate.node_id != node.node_id)
        self.nodes = (*existing, node)
        self.audit_log.append(
            AuditEvent(
                event_type="node.registered",
                task_id="",
                agent="node",
                node=node.node_id,
                message=f"Registered {registration.device_model} node.",
                details={"runtime": registration.runtime, "capabilities": list(registration.capabilities)},
            )
        )
        return node

    def submit(self, task: SandboxTask) -> SandboxReceipt:
        task = task.with_id()
        node = self._select_node(task)
        if node is None:
            decision = CommandDecision(False, "No available Android sandbox node.", "node-unavailable")
            return self._receipt(task, "rejected", "", decision)

        decision = self.policy.evaluate_command(task.command)
        status = "queued" if decision.allowed else "blocked"
        receipt = self._receipt(task, status, node.node_id, decision)
        self.audit_log.append(
            AuditEvent(
                event_type="task.submitted",
                task_id=receipt.task_id,
                agent=receipt.agent,
                node=receipt.node,
                message=receipt.decision.reason,
                severity="info" if receipt.accepted else "warning",
                details={"command": receipt.command, "status": receipt.status},
            )
        )
        return receipt

    def submit_api_task(self, payload: dict[str, Any]) -> GatewayJob:
        command = str(payload.get("command") or "")
        agent = str(payload.get("agent") or "unknown")
        required_capabilities = ("shell",) if str(payload.get("task_type") or "shell") == "shell" else ()
        task = SandboxTask(
            agent=agent,
            command=command,
            objective=str(payload.get("objective") or ""),
            node=payload.get("node_id") if isinstance(payload.get("node_id"), str) else None,
            required_capabilities=required_capabilities,
            task_id=f"job_{uuid4().hex[:12]}",
        )
        receipt = self.submit(task)
        violations = () if receipt.accepted else (receipt.decision.reason,)
        job = GatewayJob(
            job_id=receipt.task_id,
            status=receipt.status,
            agent=agent,
            command=command,
            node=receipt.node,
            repo=str(payload.get("repo") or ""),
            task_type=str(payload.get("task_type") or "shell"),
            working_dir=str(payload.get("working_dir") or ""),
            policy=str(payload.get("policy") or "default"),
            timeout_seconds=int(payload.get("timeout_seconds") or self.policy.max_runtime_seconds),
            policy_violations=violations,
            created_at=receipt.created_at,
        )
        self.jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> GatewayJob | None:
        return self.jobs.get(job_id)

    def kill_job(self, job_id: str, reason: str) -> GatewayJob | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        killed = GatewayJob(
            job_id=job.job_id,
            status="killed",
            agent=job.agent,
            command=job.command,
            node=job.node,
            repo=job.repo,
            task_type=job.task_type,
            working_dir=job.working_dir,
            policy=job.policy,
            timeout_seconds=job.timeout_seconds,
            exit_code=job.exit_code,
            stdout=job.stdout,
            stderr=job.stderr,
            policy_violations=job.policy_violations,
            kill_reason=reason,
            created_at=job.created_at,
        )
        self.jobs[job_id] = killed
        self.audit_log.append(
            AuditEvent(
                event_type="job.killed",
                task_id=job_id,
                agent=job.agent,
                node=job.node,
                message=reason,
                severity="warning",
                details={"command": job.command},
            )
        )
        return killed

    def _select_node(self, task: SandboxTask) -> AndroidSandboxNode | None:
        for node in self.nodes:
            if task.node and task.node != node.node_id:
                continue
            if node.can_run(task.required_capabilities):
                return node
        return None

    def _receipt(self, task: SandboxTask, status: str, node_id: str, decision: CommandDecision) -> SandboxReceipt:
        return SandboxReceipt(
            task_id=task.task_id,
            accepted=status == "queued",
            status=status,
            agent=task.agent,
            node=node_id,
            command=task.command,
            decision=decision,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
