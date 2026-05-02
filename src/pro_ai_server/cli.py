from pathlib import Path
import shutil
import subprocess
from dataclasses import dataclass

import typer
from rich.console import Console

from pro_ai_server.continue_config import exposure_warnings, write_continue_config
from pro_ai_server.diagnostics import build_diagnostics_report
from pro_ai_server.hardware import (
    assess_device_profile,
    parse_battery_dump,
    parse_data_free_storage_gb,
    parse_meminfo_ram_gb,
)
from pro_ai_server.ide import detect_ide_clis
from pro_ai_server.models import model_plan_for_profile, model_plan_for_ram
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


def connected_device_serial(devices_output: str) -> str | None:
    for line in devices_output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("List of devices"):
            continue
        parts = stripped.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0]
    return None


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
def scan() -> None:
    """Scan connected Android phone over ADB."""
    adb = resolve_adb()
    if not adb:
        console.print("[red]adb not found. Release builds should include bundled platform-tools.[/red]")
        raise typer.Exit(code=1)

    try:
        devices = run_command([adb, "devices"])
        serial = connected_device_serial(devices)
        if not serial:
            console.print(devices)
            console.print("[red]No connected authorized Android device found.[/red]")
            raise typer.Exit(code=1)

        meminfo = run_command([adb, "shell", "cat", "/proc/meminfo"])
        storage = run_command([adb, "shell", "df", "-k", "/data"])
        abi = run_command([adb, "shell", "getprop", "ro.product.cpu.abi"])
        android_version = run_command([adb, "shell", "getprop", "ro.build.version.release"])
        manufacturer = run_command([adb, "shell", "getprop", "ro.product.manufacturer"])
        model = run_command([adb, "shell", "getprop", "ro.product.model"])
        battery = parse_battery_dump(run_command([adb, "shell", "dumpsys", "battery"]))

        profile = assess_device_profile(
            serial=serial,
            manufacturer=manufacturer,
            model=model,
            android_version=android_version,
            abi=abi,
            ram_gb=parse_meminfo_ram_gb(meminfo),
            free_storage_gb=parse_data_free_storage_gb(storage),
            battery_level=battery["battery_level"],
            battery_temperature_c=battery["battery_temperature_c"],
            is_charging=battery["is_charging"],
        )
    except CommandError as exc:
        console.print("[red]ADB scan failed.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print("[red]Unable to parse device scan output.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc

    recommended = profile.recommended_profile
    console.print(f"Serial: {profile.serial}")
    console.print(f"Device: {profile.manufacturer} {profile.model}")
    console.print(f"Android: {profile.android_version}")
    console.print(f"ABI: {profile.abi}")
    console.print(f"RAM: {profile.ram_gb:.2f} GB")
    console.print(f"Free storage: {profile.free_storage_gb:.2f} GB")
    console.print(f"Battery: {profile.battery_level if profile.battery_level is not None else 'unknown'}%")
    console.print(f"Charging: {profile.is_charging if profile.is_charging is not None else 'unknown'}")
    if recommended:
        console.print(f"Recommended profile: [bold]{recommended.name}[/bold] ({recommended.status})")
        console.print(f"Chat model: {recommended.chat_model}")
        console.print(f"Autocomplete model: {recommended.autocomplete_model}")
    for warning in profile.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")


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
def tunnel() -> None:
    """Create USB tunnel from host localhost:11434 to phone Ollama port."""
    adb = resolve_adb()
    if not adb:
        console.print("[red]adb not found. Release builds should include bundled platform-tools.[/red]")
        raise typer.Exit(code=1)

    try:
        output = run_command([adb, "reverse", "tcp:11434", "tcp:11434"])
    except CommandError as exc:
        console.print("[red]ADB reverse tunnel failed.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc

    console.print("[green]ADB reverse tunnel requested for port 11434.[/green]")
    if output:
        console.print(output)


@app.command()
def diagnose() -> None:
    """Print host, phone, and local Ollama diagnostics."""
    report = build_diagnostics_report(resolve_adb()).text
    console.print(report)


if __name__ == "__main__":
    app()
