from pathlib import Path
import shutil
import subprocess
from dataclasses import dataclass

import typer
from rich.console import Console

from pro_ai_server.adb import select_adb_device_from_output
from pro_ai_server.continue_config import exposure_warnings, write_continue_config
from pro_ai_server.device_scan import (
    DeviceScanOutputs,
    build_device_profile_from_scan_outputs,
    build_device_scan_commands,
    build_device_scan_summary_lines,
)
from pro_ai_server.diagnostics import build_diagnostics_report, write_diagnostics_report
from pro_ai_server.ide import detect_ide_clis
from pro_ai_server.models import model_plan_for_profile, model_plan_for_ram
from pro_ai_server.ollama import assess_model_inventory, build_ollama_tags_command
from pro_ai_server.packaging import validate_windows_platform_tools_layouts
from pro_ai_server.release_validation import validate_release_layout
from pro_ai_server.script_delivery import build_script_delivery_plan
from pro_ai_server.setup_receipt import build_setup_receipt, render_setup_receipt
from pro_ai_server.setup_workflow import plan_setup_workflow
from pro_ai_server.termux_readiness import (
    assess_termux_readiness,
    build_termux_package_info_command,
    build_termux_readiness_commands,
)
from pro_ai_server.termux_scripts import generate_termux_scripts, write_termux_scripts

app = typer.Typer(help="Pro AI Server: Android phone local AI server manager.")
console = Console()


@dataclass
class ModelProfile:
    name: str
    chat_model: str
    autocomplete_model: str
    note: str


class CommandError(RuntimeError):
    def __init__(self, command: list[str], returncode: int, stdout: str, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stdout = stdout.strip()
        self.stderr = stderr.strip()
        message = self.stderr or self.stdout or f"Command failed with exit code {returncode}."
        super().__init__(message)


def package_root() -> Path:
    return Path(__file__).resolve().parent


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def bundled_adb_candidates() -> tuple[Path, ...]:
    relative_path = Path("embedded-tools") / "windows" / "platform-tools" / "adb.exe"
    return (
        package_root() / relative_path,
        project_root() / relative_path,
    )


def bundled_adb_path() -> Path:
    return bundled_adb_candidates()[0]


def resolve_adb() -> str | None:
    for bundled in bundled_adb_candidates():
        if bundled.exists():
            return str(bundled)

    system_adb = shutil.which("adb")
    if system_adb:
        return system_adb

    return None


def run_command(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise CommandError(command, result.returncode, result.stdout, result.stderr)
    return result.stdout.strip()


def run_optional_command(command: list[str]) -> str:
    try:
        return run_command(command)
    except CommandError as exc:
        return exc.stdout or exc.stderr


def adb_command(adb: str, args: list[str], serial: str | None = None) -> list[str]:
    if serial:
        return [adb, "-s", serial, *args]
    return [adb, *args]


def select_device_serial(adb: str, requested_serial: str | None = None) -> str:
    devices = run_command([adb, "devices"])
    selection = select_adb_device_from_output(devices, serial=requested_serial)
    if selection.ok and selection.selected:
        return selection.selected.serial

    raise ValueError(selection.error or "Unable to select an ADB device.")


def select_model_profile(ram_gb: float) -> ModelProfile:
    if ram_gb < 5:
        return ModelProfile(
            name="lightweight",
            chat_model="qwen2.5-coder:1.5b",
            autocomplete_model="qwen2.5-coder:0.5b",
            note="Experimental profile for low-memory phones.",
        )
    if ram_gb < 9:
        return ModelProfile(
            name="professional",
            chat_model="qwen2.5-coder:3b",
            autocomplete_model="qwen2.5-coder:1.5b-base",
            note="Recommended profile for 6GB-8GB Android phones.",
        )
    return ModelProfile(
        name="max",
        chat_model="qwen2.5-coder:7b",
        autocomplete_model="qwen2.5-coder:1.5b-base",
        note="High-memory profile for 10GB+ Android phones.",
    )


@app.command()
def doctor() -> None:
    """Check host computer requirements."""
    console.print("[bold]Pro AI Server Doctor[/bold]")

    adb_path = resolve_adb()
    if adb_path:
        if "embedded-tools" in adb_path:
            console.print(f"[green]OK[/green] bundled adb found: {adb_path}")
        else:
            console.print(f"[green]OK[/green] system adb found: {adb_path}")
    else:
        console.print("[yellow]Missing[/yellow] adb not found. App should bundle platform-tools for release builds.")

    python_path = shutil.which("python")
    if python_path:
        console.print(f"[green]OK[/green] python found: {python_path}")

    for ide in detect_ide_clis():
        if ide.installed:
            console.print(f"[green]OK[/green] IDE CLI found: {ide.command} -> {ide.path}")


@app.command()
def scan(serial: str | None = typer.Option(None, help="ADB device serial to use when multiple phones are connected.")) -> None:
    """Scan connected Android phone over ADB."""
    adb = resolve_adb()
    if not adb:
        console.print("[red]adb not found. Release builds should include bundled platform-tools.[/red]")
        raise typer.Exit(code=1)

    try:
        selected_serial = select_device_serial(adb, serial)
        commands = build_device_scan_commands(adb, selected_serial)
        profile = build_device_profile_from_scan_outputs(
            selected_serial,
            DeviceScanOutputs(
                meminfo=run_command(list(commands.meminfo)),
                storage=run_command(list(commands.storage)),
                abi=run_command(list(commands.abi)),
                android_version=run_command(list(commands.android_version)),
                manufacturer=run_command(list(commands.manufacturer)),
                model=run_command(list(commands.model)),
                battery=run_command(list(commands.battery)),
            ),
        )
    except CommandError as exc:
        console.print("[red]ADB scan failed.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print("[red]Unable to parse device scan output.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc

    for line in build_device_scan_summary_lines(profile):
        if line.startswith("Warning: "):
            console.print(f"[yellow]{line}[/yellow]")
        else:
            console.print(line)


@app.command()
def profile(ram_gb: float = typer.Argument(..., help="Detected phone RAM in GB.")) -> None:
    """Show recommended model profile for a RAM amount."""
    selected = select_model_profile(ram_gb)
    plan = model_plan_for_ram(ram_gb)
    console.print(f"Profile: [bold]{selected.name}[/bold]")
    console.print(f"Chat model: {selected.chat_model}")
    console.print(f"Autocomplete model: {selected.autocomplete_model}")
    console.print(f"Status: {plan.status}")
    console.print(selected.note)


@app.command()
def generate_scripts(
    mode: str = typer.Option("usb", help="Connection mode: usb, lan, or tailscale."),
    profile_name: str = typer.Option("professional", "--profile", help="Model profile to use."),
    ram_gb: float | None = typer.Option(None, help="Optional RAM value used to select a profile."),
    output_dir: Path = typer.Option(Path("."), help="Directory where generated/termux will be written."),
) -> None:
    """Generate inspectable Termux setup/start/model scripts."""
    try:
        plan = model_plan_for_ram(ram_gb) if ram_gb is not None else model_plan_for_profile(profile_name)
        bundle = generate_termux_scripts(plan.chat_model, plan.autocomplete_model, mode=mode)
        written = write_termux_scripts(bundle, root=output_dir)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Generated Termux scripts for {bundle.mode} mode.[/green]")
    console.print(f"Ollama host binding: {bundle.ollama_host}")
    for path in written:
        console.print(str(path))


@app.command()
def configure_continue(
    mode: str = typer.Option("usb", help="Connection mode: usb, lan, or tailscale."),
    host: str | None = typer.Option(None, help="Host or IP for lan/tailscale modes."),
    profile_name: str = typer.Option("professional", "--profile", help="Model profile to use."),
    ram_gb: float | None = typer.Option(None, help="Optional RAM value used to select a profile."),
) -> None:
    """Generate Continue config.yaml with backup protection."""
    try:
        plan = model_plan_for_ram(ram_gb) if ram_gb is not None else model_plan_for_profile(profile_name)
        result = write_continue_config(plan, mode=mode, host=host)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Wrote Continue config:[/green] {result.config_path}")
    console.print(f"API base: {result.api_base}")
    if result.backup_path:
        console.print(f"Backup: {result.backup_path}")
    for warning in exposure_warnings(mode):
        console.print(f"[yellow]Warning:[/yellow] {warning}")


@app.command()
def termux_check(
    serial: str | None = typer.Option(None, help="ADB device serial to use when multiple phones are connected."),
) -> None:
    """Check Termux, Termux:API, and Termux home readiness on the phone."""
    adb = resolve_adb()
    if not adb:
        console.print("[red]adb not found. Release builds should include bundled platform-tools.[/red]")
        raise typer.Exit(code=1)

    try:
        selected_serial = select_device_serial(adb, serial)
        readiness_outputs = [
            run_optional_command([adb, *list(command[1:])])
            for command in build_termux_readiness_commands(selected_serial)
        ]
        package_info = run_optional_command([adb, *list(build_termux_package_info_command(selected_serial)[1:])])
    except CommandError as exc:
        console.print("[red]ADB Termux readiness check failed.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    result = assess_termux_readiness(*readiness_outputs, package_info_output=package_info)
    console.print(f"Device: {selected_serial}")
    if result.version_hint:
        console.print(f"Termux version: {result.version_hint}")
    for check in result.checks:
        status = "[green]OK[/green]" if check.ok else "[yellow]Needs attention[/yellow]"
        console.print(f"{status} {check.name}")
        if check.warning:
            console.print(f"  Warning: {check.warning}")
        if check.instruction:
            console.print(f"  Next: {check.instruction}")
    if not result.ok:
        raise typer.Exit(code=1)


@app.command()
def server_check(
    api_base: str = typer.Option("http://localhost:11434", help="Ollama API base URL."),
    profile_name: str = typer.Option("professional", "--profile", help="Model profile to verify."),
    ram_gb: float | None = typer.Option(None, help="Optional RAM value used to select a profile."),
) -> None:
    """Check Ollama /api/tags and required model inventory."""
    plan = model_plan_for_ram(ram_gb) if ram_gb is not None else model_plan_for_profile(profile_name)
    command = build_ollama_tags_command(api_base)
    tags_output = run_optional_command(list(command))
    inventory = assess_model_inventory(plan, tags_output)

    console.print(f"Ollama API: {api_base.rstrip('/')}")
    console.print(f"Profile: {plan.profile}")
    if inventory.model_names:
        console.print("Models:")
        for model in inventory.model_names:
            console.print(f"  {model}")
    else:
        console.print("Models: none detected")

    for warning in inventory.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")
    for instruction in inventory.instructions:
        console.print(f"Next: {instruction}")
    if not inventory.ok:
        raise typer.Exit(code=1)


@app.command()
def setup(
    mode: str = typer.Option("usb", help="Connection mode: usb, lan, or tailscale."),
    host: str | None = typer.Option(None, help="Host or IP for lan/tailscale modes."),
    profile_name: str | None = typer.Option(None, "--profile", help="Model profile to use."),
    ram_gb: float | None = typer.Option(None, help="Optional RAM value used to select a profile."),
    configure_continue_config: bool = typer.Option(True, "--continue/--no-continue", help="Plan/write Continue config."),
    create_usb_tunnel: bool | None = typer.Option(None, "--tunnel/--no-tunnel", help="Plan/create USB tunnel."),
    push: bool = typer.Option(False, "--push-scripts", help="Plan/push generated scripts to the phone."),
    execute: bool = typer.Option(False, help="Execute the planned local/device actions."),
    yes: bool = typer.Option(False, "--yes", help="Confirm setup actions that write config or expose network mode."),
    output_dir: Path = typer.Option(Path("."), help="Directory where generated/termux will be written."),
    remote_home: str = typer.Option("/data/data/com.termux/files/home", help="Remote Termux home directory."),
    serial: str | None = typer.Option(None, help="ADB device serial to use when multiple phones are connected."),
) -> None:
    """Plan or execute the guided MVP setup workflow."""
    try:
        plan = plan_setup_workflow(
            mode=mode,
            host=host,
            ram_gb=ram_gb,
            profile=profile_name,
            configure_continue=configure_continue_config,
            create_usb_tunnel=create_usb_tunnel,
            push_scripts=push,
            generated_termux_dir=output_dir / "generated" / "termux",
            remote_termux_home=remote_home,
            serial=serial,
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold]Setup plan[/bold]: {plan.summary}")
    for warning in plan.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")
    for index, step in enumerate(plan.steps, start=1):
        console.print(f"{index}. [bold]{step.title}[/bold] - {step.detail}")
        for note in step.notes:
            console.print(f"   Note: {note}")

    if not execute:
        console.print("Plan only. Re-run with --execute --yes to perform write/device actions.")
        return

    if (plan.requires_confirmation or configure_continue_config) and not yes:
        console.print("[red]Refusing to execute without --yes because setup writes config or changes exposure mode.[/red]")
        raise typer.Exit(code=1)

    try:
        continue_result = None
        selected_serial = None
        delivery_plan = None
        tunnel_requested = False

        bundle = generate_termux_scripts(
            plan.model_plan.chat_model,
            plan.model_plan.autocomplete_model,
            mode=plan.mode,
        )
        written = write_termux_scripts(bundle, root=output_dir)
        console.print(f"[green]Generated {len(written)} Termux files.[/green]")

        if configure_continue_config:
            continue_result = write_continue_config(plan.model_plan, mode=plan.mode, host=plan.host)
            console.print(f"[green]Wrote Continue config:[/green] {continue_result.config_path}")
            if continue_result.backup_path:
                console.print(f"Backup: {continue_result.backup_path}")

        if push or (create_usb_tunnel is not False and plan.mode == "usb"):
            adb = resolve_adb()
            if not adb:
                console.print("[red]adb not found. Release builds should include bundled platform-tools.[/red]")
                raise typer.Exit(code=1)
            selected_serial = select_device_serial(adb, serial)

            if push:
                delivery_plan = build_script_delivery_plan(output_dir / "generated" / "termux", remote_home, selected_serial)
                run_command(
                    adb_command(adb, ["shell", "mkdir", "-p", f"{remote_home.rstrip('/')}/.shortcuts"], selected_serial)
                )
                for command in delivery_plan.commands:
                    run_command([adb, *list(command[1:])])
                console.print(f"[green]Pushed Termux scripts to device {selected_serial}.[/green]")
                console.print("Run these inside Termux:")
                for command in delivery_plan.post_push_termux_commands:
                    console.print(f"  {command}")

            if create_usb_tunnel is not False and plan.mode == "usb":
                run_command(adb_command(adb, ["reverse", "tcp:11434", "tcp:11434"], selected_serial))
                tunnel_requested = True
                console.print(f"[green]ADB reverse tunnel requested for device {selected_serial}.[/green]")
        receipt = build_setup_receipt(
            workflow_plan=plan,
            continue_result=continue_result,
            termux_bundle=bundle,
            written_termux_paths=written,
            delivery_plan=delivery_plan,
            selected_device_serial=selected_serial,
            pushed_scripts=push,
            tunnel_requested=tunnel_requested,
        )
        console.print(render_setup_receipt(receipt))
    except CommandError as exc:
        console.print("[red]Setup failed while running an external command.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc


@app.command()
def push_scripts(
    generated_termux_dir: Path = typer.Option(
        Path("generated") / "termux",
        help="Local generated Termux script directory to push.",
    ),
    remote_home: str = typer.Option(
        "/data/data/com.termux/files/home",
        help="Remote Termux home directory.",
    ),
    serial: str | None = typer.Option(None, help="ADB device serial to use when multiple phones are connected."),
) -> None:
    """Push generated Termux scripts to the selected phone with adb push."""
    adb = resolve_adb()
    if not adb:
        console.print("[red]adb not found. Release builds should include bundled platform-tools.[/red]")
        raise typer.Exit(code=1)

    try:
        selected_serial = select_device_serial(adb, serial)
        plan = build_script_delivery_plan(generated_termux_dir, remote_home, selected_serial)
        run_command(adb_command(adb, ["shell", "mkdir", "-p", f"{remote_home.rstrip('/')}/.shortcuts"], selected_serial))
        for command in plan.commands:
            run_command([adb, *list(command[1:])])
    except CommandError as exc:
        console.print("[red]ADB script push failed.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]Pushed Termux scripts to device {selected_serial}.[/green]")
    console.print("Run these inside Termux:")
    for command in plan.post_push_termux_commands:
        console.print(f"  {command}")
    for instruction in plan.instructions:
        console.print(f"[yellow]Note:[/yellow] {instruction}")


@app.command()
def tunnel(serial: str | None = typer.Option(None, help="ADB device serial to use when multiple phones are connected.")) -> None:
    """Create USB tunnel from host localhost:11434 to phone Ollama port."""
    adb = resolve_adb()
    if not adb:
        console.print("[red]adb not found. Release builds should include bundled platform-tools.[/red]")
        raise typer.Exit(code=1)

    try:
        selected_serial = select_device_serial(adb, serial)
        output = run_command(adb_command(adb, ["reverse", "tcp:11434", "tcp:11434"], selected_serial))
    except CommandError as exc:
        console.print("[red]ADB reverse tunnel failed.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    console.print(f"[green]ADB reverse tunnel requested for device {selected_serial} on port 11434.[/green]")
    if output:
        console.print(output)


@app.command()
def diagnose(output: Path | None = typer.Option(None, help="Optional file path for the diagnostics report.")) -> None:
    """Print host, phone, and local Ollama diagnostics."""
    report = build_diagnostics_report(resolve_adb())
    console.print(report.text)
    if output:
        written = write_diagnostics_report(report, output)
        console.print(f"[green]Wrote diagnostics report:[/green] {written}")


@app.command()
def validate_platform_tools(root: Path = typer.Option(Path("."), help="Repository root to validate.")) -> None:
    """Validate bundled Windows Platform Tools ADB runtime files."""
    result = validate_windows_platform_tools_layouts(root)
    console.print(result.message)
    console.print(f"Source tree: {result.source_tree.message}")
    console.print(f"Packaged: {result.packaged.message}")
    if not result.ok:
        raise typer.Exit(code=1)


@app.command()
def validate_release(root: Path = typer.Option(Path("."), help="Repository root to validate.")) -> None:
    """Validate release readiness: ADB files, package data, and CI gates."""
    result = validate_release_layout(root)
    console.print(result.summary)
    for issue in result.issues:
        path = f" ({issue.path})" if issue.path else ""
        console.print(f"[red]{issue.code}[/red]: {issue.message}{path}")
    if not result.ok:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
