from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pro_ai_server.continue_config import api_base_for_mode, exposure_warnings
from pro_ai_server.models import ModelPlan, model_plan_for_profile, model_plan_for_ram
from pro_ai_server.script_delivery import Command, build_script_delivery_plan
from pro_ai_server.termux_scripts import DEFAULT_SCRIPT_DIR, generate_termux_scripts


VALID_SETUP_MODES = {"usb", "lan", "tailscale"}


@dataclass(frozen=True)
class SetupStep:
    key: str
    title: str
    detail: str
    notes: tuple[str, ...] = ()
    commands: tuple[Command, ...] = ()


@dataclass(frozen=True)
class SetupWorkflowPlan:
    mode: str
    host: str | None
    steps: tuple[SetupStep, ...]
    warnings: tuple[str, ...]
    model_plan: ModelPlan
    requires_confirmation: bool
    summary: str


def plan_setup_workflow(
    mode: str = "usb",
    host: str | None = None,
    ram_gb: float | None = None,
    profile: str | None = None,
    configure_continue: bool = True,
    create_usb_tunnel: bool | None = None,
    push_scripts: bool = False,
    generated_termux_dir: Path = DEFAULT_SCRIPT_DIR,
    remote_termux_home: str = "/data/data/com.termux/files/home",
    serial: str | None = None,
) -> SetupWorkflowPlan:
    normalized_mode = _normalize_mode(mode)
    normalized_host = _normalize_host(host)
    selected_model_plan = _select_model_plan(ram_gb=ram_gb, profile=profile)
    include_tunnel = _include_tunnel(normalized_mode, create_usb_tunnel)
    warnings = tuple(exposure_warnings(normalized_mode))
    requires_confirmation = normalized_mode in {"lan", "tailscale"}

    termux_bundle = generate_termux_scripts(
        selected_model_plan.chat_model,
        selected_model_plan.autocomplete_model,
        mode=normalized_mode,
        script_dir=generated_termux_dir,
    )

    steps: list[SetupStep] = [
        SetupStep(
            key="select-models",
            title="Select model profile",
            detail=(
                f"Use the {selected_model_plan.profile} profile "
                f"({selected_model_plan.chat_model} chat, "
                f"{selected_model_plan.autocomplete_model} autocomplete)."
            ),
            notes=(f"Profile status: {selected_model_plan.status}.",),
        ),
        SetupStep(
            key="generate-termux-scripts",
            title="Plan Termux scripts",
            detail=(
                f"Generate {len(termux_bundle.files)} inspectable Termux files for "
                f"{normalized_mode} mode with OLLAMA_HOST={termux_bundle.ollama_host}."
            ),
            notes=(
                "This is a planning step only; no script files are written.",
                "Generated scripts include bootstrap, start, model install, widget, and Android optimization guidance.",
            ),
        ),
    ]

    if configure_continue:
        api_base = api_base_for_mode(normalized_mode, normalized_host)
        steps.append(
            SetupStep(
                key="configure-continue",
                title="Configure Continue",
                detail=f"Plan Continue config.yaml for API base {api_base}.",
                notes=(
                    "This step writes user Continue config when executed.",
                    "Existing config.yaml should be backed up before replacement.",
                ),
            )
        )

    if include_tunnel:
        steps.append(
            SetupStep(
                key="create-usb-tunnel",
                title="Create USB tunnel",
                detail="Plan adb reverse from host localhost:11434 to phone tcp:11434.",
                commands=(("adb", "reverse", "tcp:11434", "tcp:11434"),),
                notes=("USB tunnel keeps Ollama reachable on localhost without network exposure.",),
            )
        )

    if push_scripts:
        delivery_plan = build_script_delivery_plan(generated_termux_dir, remote_termux_home, serial)
        steps.append(
            SetupStep(
                key="push-scripts",
                title="Push Termux scripts",
                detail=f"Plan {len(delivery_plan.commands)} adb commands to deliver generated Termux files.",
                commands=delivery_plan.commands,
                notes=(
                    "Scripts are inspectable before delivery.",
                    "Delivery uses adb push plus chmod for executable scripts.",
                    *delivery_plan.instructions,
                ),
            )
        )

    return SetupWorkflowPlan(
        mode=normalized_mode,
        host=normalized_host,
        steps=tuple(steps),
        warnings=warnings,
        model_plan=selected_model_plan,
        requires_confirmation=requires_confirmation,
        summary=_summary(
            normalized_mode,
            normalized_host,
            selected_model_plan,
            configure_continue,
            include_tunnel,
            push_scripts,
            requires_confirmation,
        ),
    )


def _normalize_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in VALID_SETUP_MODES:
        modes = ", ".join(sorted(VALID_SETUP_MODES))
        raise ValueError(f"Unknown setup mode '{mode}'. Expected one of: {modes}.")
    return normalized


def _normalize_host(host: str | None) -> str | None:
    normalized = (host or "").strip()
    return normalized or None


def _select_model_plan(ram_gb: float | None, profile: str | None) -> ModelPlan:
    if profile:
        return model_plan_for_profile(profile)
    if ram_gb is not None:
        return model_plan_for_ram(ram_gb)
    return model_plan_for_profile("professional")


def _include_tunnel(mode: str, requested: bool | None) -> bool:
    if requested is not None:
        return requested
    return mode == "usb"


def _summary(
    mode: str,
    host: str | None,
    model_plan: ModelPlan,
    configure_continue: bool,
    include_tunnel: bool,
    push_scripts: bool,
    requires_confirmation: bool,
) -> str:
    target = mode if host is None else f"{mode} via {host}"
    options = [
        "Continue config" if configure_continue else "no Continue config",
        "USB tunnel" if include_tunnel else "no USB tunnel",
        "adb script push" if push_scripts else "no adb script push",
    ]
    confirmation = "requires explicit confirmation" if requires_confirmation else "does not require exposure confirmation"
    return f"Plan {target} setup with {model_plan.profile} profile, {', '.join(options)}; {confirmation}."
