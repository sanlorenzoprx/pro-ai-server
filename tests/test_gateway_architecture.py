from pathlib import Path

from droidshield.agentic import AgenticWorkItem, dry_run_agentic_workflow, plan_agentic_development_loop
from droidshield.gateway import SandboxGateway, SandboxTask
from droidshield.monitoring import AuditLog
from droidshield.node_runtime import AndroidSandboxNode


def test_gateway_accepts_allowed_task_and_writes_audit(tmp_path: Path) -> None:
    gateway = SandboxGateway(audit_log=AuditLog(tmp_path / "audit.jsonl"))

    receipt = gateway.submit(SandboxTask(agent="cursor", command="git status"))

    assert receipt.accepted is True
    assert receipt.status == "queued"
    assert receipt.node == "android-node-01"
    records = gateway.audit_log.tail()
    assert records[0]["event_type"] == "task.submitted"


def test_gateway_blocks_disallowed_task() -> None:
    gateway = SandboxGateway()

    receipt = gateway.submit(SandboxTask(agent="cursor", command="curl https://example.com"))

    assert receipt.accepted is False
    assert receipt.status == "blocked"
    assert "not allowlisted" in receipt.decision.reason


def test_gateway_respects_node_capabilities() -> None:
    node = AndroidSandboxNode(node_id="pixel-4a", capabilities=("files",))
    gateway = SandboxGateway(nodes=(node,))

    receipt = gateway.submit(SandboxTask(agent="codex", command="git status", required_capabilities=("shell",)))

    assert receipt.accepted is False
    assert receipt.decision.matched_rule == "node-unavailable"


def test_agentic_loop_runs_policy_gate() -> None:
    gateway = SandboxGateway()
    work_item = AgenticWorkItem(
        agent="codex",
        objective="Run tests safely",
        proposed_commands=("pytest", "sudo reboot"),
    )

    results = dry_run_agentic_workflow(work_item, gateway)

    assert plan_agentic_development_loop() == (
        "observe",
        "plan",
        "policy-check",
        "sandbox-execute",
        "verify",
        "report",
    )
    assert [result.status for result in results].count("accepted") == 1
    assert [result.status for result in results].count("blocked") == 1
