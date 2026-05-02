from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pro_ai_server.continue_config import ContinueConfigWriteResult
from pro_ai_server.models import ModelPlan
from pro_ai_server.script_delivery import ScriptDeliveryPlan
from pro_ai_server.setup_workflow import SetupWorkflowPlan
from pro_ai_server.termux_scripts import TermuxScriptBundle


@dataclass(frozen=True)
class SetupReceiptItem:
    label: str
    value: str
    detail: str | None = None


@dataclass(frozen=True)
class SetupReceipt:
    mode: str | None = None
    model_profile: str | None = None
    generated_termux_paths: tuple[Path, ...] = ()
    continue_config_path: Path | None = None
    continue_backup_path: Path | None = None
    selected_device_serial: str | None = None
    pushed_scripts: bool = False
    tunnel_requested: bool = False
    post_push_termux_commands: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    artifacts: tuple[SetupReceiptItem, ...] = ()
    next_steps: tuple[SetupReceiptItem, ...] = ()


def build_setup_receipt(
    *,
    workflow_plan: SetupWorkflowPlan | None = None,
    continue_result: ContinueConfigWriteResult | None = None,
    termux_bundle: TermuxScriptBundle | None = None,
    written_termux_paths: Iterable[Path] | None = None,
    delivery_plan: ScriptDeliveryPlan | None = None,
    model_plan: ModelPlan | None = None,
    mode: str | None = None,
    selected_device_serial: str | None = None,
    pushed_scripts: bool | None = None,
    tunnel_requested: bool | None = None,
    warnings: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> SetupReceipt:
    """Build a pure execution receipt from already-created plan/result objects."""

    selected_model_plan = model_plan or (workflow_plan.model_plan if workflow_plan else None)
    generated_paths = _generated_paths(written_termux_paths, termux_bundle)
    normalized_mode = mode or (workflow_plan.mode if workflow_plan else None) or (termux_bundle.mode if termux_bundle else None)
    resolved_tunnel_requested = (
        tunnel_requested if tunnel_requested is not None else _workflow_has_step(workflow_plan, "create-usb-tunnel")
    )
    resolved_pushed_scripts = pushed_scripts if pushed_scripts is not None else delivery_plan is not None
    resolved_serial = selected_device_serial or _serial_from_delivery_plan(delivery_plan)
    post_push_commands = delivery_plan.post_push_termux_commands if delivery_plan else ()
    resolved_warnings = tuple(dict.fromkeys((*((workflow_plan.warnings if workflow_plan else ())), *warnings)))
    resolved_notes = tuple(dict.fromkeys((*notes, *((delivery_plan.instructions if delivery_plan else ())))))

    artifacts = _artifact_items(
        generated_paths=generated_paths,
        continue_config_path=continue_result.config_path if continue_result else None,
        continue_backup_path=continue_result.backup_path if continue_result else None,
    )
    next_steps = _next_step_items(
        post_push_commands=post_push_commands,
        pushed_scripts=resolved_pushed_scripts,
        tunnel_requested=resolved_tunnel_requested,
    )

    return SetupReceipt(
        mode=normalized_mode,
        model_profile=selected_model_plan.profile if selected_model_plan else None,
        generated_termux_paths=generated_paths,
        continue_config_path=continue_result.config_path if continue_result else None,
        continue_backup_path=continue_result.backup_path if continue_result else None,
        selected_device_serial=resolved_serial,
        pushed_scripts=resolved_pushed_scripts,
        tunnel_requested=resolved_tunnel_requested,
        post_push_termux_commands=post_push_commands,
        warnings=resolved_warnings,
        notes=resolved_notes,
        artifacts=artifacts,
        next_steps=next_steps,
    )


def render_setup_receipt(receipt: SetupReceipt) -> str:
    """Render a deterministic text report for CLI output or diagnostics."""

    lines = [
        "Pro AI Server setup receipt",
        "",
        "Summary",
        f"- Mode: {_value(receipt.mode)}",
        f"- Model profile: {_value(receipt.model_profile)}",
        f"- Selected device serial: {_value(receipt.selected_device_serial)}",
        f"- Pushed scripts: {_yes_no(receipt.pushed_scripts)}",
        f"- Tunnel requested: {_yes_no(receipt.tunnel_requested)}",
        "",
        "Artifacts",
    ]
    lines.extend(_render_items(receipt.artifacts))
    lines.extend(["", "Post-push Termux commands"])
    lines.extend(f"- {command}" for command in receipt.post_push_termux_commands)
    if not receipt.post_push_termux_commands:
        lines.append("- none")
    lines.extend(["", "Next steps"])
    lines.extend(_render_items(receipt.next_steps))
    lines.extend(["", "Warnings"])
    lines.extend(f"- {warning}" for warning in receipt.warnings)
    if not receipt.warnings:
        lines.append("- none")
    lines.extend(["", "Notes"])
    lines.extend(f"- {note}" for note in receipt.notes)
    if not receipt.notes:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _generated_paths(
    written_termux_paths: Iterable[Path] | None,
    termux_bundle: TermuxScriptBundle | None,
) -> tuple[Path, ...]:
    if written_termux_paths is not None:
        return tuple(sorted((Path(path) for path in written_termux_paths), key=_path_sort_key))
    if termux_bundle is not None:
        return tuple(sorted(termux_bundle.files.keys(), key=_path_sort_key))
    return ()


def _artifact_items(
    *,
    generated_paths: tuple[Path, ...],
    continue_config_path: Path | None,
    continue_backup_path: Path | None,
) -> tuple[SetupReceiptItem, ...]:
    items = [SetupReceiptItem("Generated Termux files", str(path)) for path in generated_paths]
    if continue_config_path is not None:
        items.append(SetupReceiptItem("Continue config", str(continue_config_path)))
    if continue_backup_path is not None:
        items.append(SetupReceiptItem("Continue config backup", str(continue_backup_path)))
    return tuple(items)


def _next_step_items(
    *,
    post_push_commands: tuple[str, ...],
    pushed_scripts: bool,
    tunnel_requested: bool,
) -> tuple[SetupReceiptItem, ...]:
    items = [SetupReceiptItem("Run in Termux", command) for command in post_push_commands]
    if tunnel_requested:
        items.append(SetupReceiptItem("USB tunnel", "Keep adb reverse tcp:11434 active while using Continue."))
    if pushed_scripts and not post_push_commands:
        items.append(SetupReceiptItem("Termux scripts", "Run the delivered scripts from Termux."))
    return tuple(items)


def _render_items(items: tuple[SetupReceiptItem, ...]) -> list[str]:
    if not items:
        return ["- none"]
    rendered = []
    for item in items:
        suffix = f" ({item.detail})" if item.detail else ""
        rendered.append(f"- {item.label}: {item.value}{suffix}")
    return rendered


def _workflow_has_step(workflow_plan: SetupWorkflowPlan | None, key: str) -> bool:
    if workflow_plan is None:
        return False
    return any(step.key == key for step in workflow_plan.steps)


def _serial_from_delivery_plan(delivery_plan: ScriptDeliveryPlan | None) -> str | None:
    if delivery_plan is None:
        return None
    for command in delivery_plan.commands:
        if len(command) >= 3 and command[0] == "adb" and command[1] == "-s":
            return command[2]
    return None


def _path_sort_key(path: Path) -> str:
    return path.as_posix()


def _value(value: str | None) -> str:
    return value if value else "not recorded"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
