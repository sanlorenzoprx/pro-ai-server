from __future__ import annotations

from dataclasses import dataclass

from droidshield.gateway import SandboxGateway, SandboxTask


AGENTIC_PHASES = (
    "observe",
    "plan",
    "policy-check",
    "sandbox-execute",
    "verify",
    "report",
)


@dataclass(frozen=True)
class AgenticWorkItem:
    agent: str
    objective: str
    proposed_commands: tuple[str, ...]
    node: str | None = None


@dataclass(frozen=True)
class AgenticStepResult:
    phase: str
    status: str
    message: str
    task_id: str | None = None


def plan_agentic_development_loop() -> tuple[str, ...]:
    return AGENTIC_PHASES


def dry_run_agentic_workflow(work_item: AgenticWorkItem, gateway: SandboxGateway) -> tuple[AgenticStepResult, ...]:
    results: list[AgenticStepResult] = [
        AgenticStepResult("observe", "ready", f"Objective captured for {work_item.agent}."),
        AgenticStepResult("plan", "ready", f"{len(work_item.proposed_commands)} command(s) proposed."),
    ]
    for command in work_item.proposed_commands:
        receipt = gateway.submit(
            SandboxTask(
                agent=work_item.agent,
                objective=work_item.objective,
                command=command,
                node=work_item.node,
            )
        )
        results.append(
            AgenticStepResult(
                "policy-check",
                "accepted" if receipt.accepted else "blocked",
                receipt.decision.reason,
                receipt.task_id,
            )
        )
    results.append(AgenticStepResult("verify", "pending", "Verification runs after sandbox execution."))
    results.append(AgenticStepResult("report", "pending", "Agent returns logs, diff, tests, and policy receipts."))
    return tuple(results)
