from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import typer
from rich.console import Console
from rich.table import Table

from ai_okf.config import (
    DEFAULT_MODEL,
    DEFAULT_OUTPUT,
    DEFAULT_WORKERS,
    MAX_FILE_BYTES,
    PROTECTED_NAME_GLOBS,
    is_loopback_url,
    resolve_api_base,
)
from ai_okf.project_config import ConfigError, load_project_config, resolve_value

console = Console()

config_app = typer.Typer(
    help="Inspect the effective configuration.",
    no_args_is_help=True,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ConfigEntry:
    name: str
    value: str
    source: str


def collect_effective_config(
    root: Path,
    env: Mapping[str, str] | None = None,
) -> list[ConfigEntry]:
    project, _ = load_project_config(root)

    profile, profile_src = resolve_value(
        None, "OKF_PROFILE", project.profile, "code", env=env
    )
    model, model_src = resolve_value(
        None, "OKF_MODEL", project.model, DEFAULT_MODEL, env=env
    )
    api_base, api_src = resolve_value(
        None, "OKF_API_BASE", project.api_base, None, env=env
    )
    output, output_src = resolve_value(
        None, "OKF_OUTPUT", project.output, str(DEFAULT_OUTPUT), env=env
    )
    workers, workers_src = resolve_value(
        None, "OKF_WORKERS", project.workers, None, env=env
    )

    base_url = resolve_api_base(
        str(model), api_base if isinstance(api_base, str) else None
    )
    if workers is None:
        workers = 1 if is_loopback_url(base_url) else DEFAULT_WORKERS
        workers_src = "default"
    else:
        workers = int(workers)

    return [
        ConfigEntry("profile", str(profile), profile_src),
        ConfigEntry("model", str(model), model_src),
        ConfigEntry("api_base", base_url, api_src),
        ConfigEntry("output", str(output), output_src),
        ConfigEntry("workers", str(workers), workers_src),
        ConfigEntry("privacy", "local-only (cloud blocked)", "built-in"),
        ConfigEntry("max_file_bytes", str(MAX_FILE_BYTES), "built-in"),
        ConfigEntry("protected_patterns", str(len(PROTECTED_NAME_GLOBS)), "built-in"),
    ]


def config_file_paths(root: Path) -> list[tuple[Path, bool]]:
    paths = [
        root / ".okf.yaml",
        PROJECT_ROOT / ".env.local",
    ]
    return [(path, path.exists()) for path in paths]


@config_app.command("show")
def show(
    path: str = typer.Argument(".", help="Project root to read .okf.yaml from"),
) -> None:
    """Print effective configuration and every config path that was parsed."""
    root = Path(path).resolve()
    try:
        entries = collect_effective_config(root)
    except ConfigError as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(2) from exc

    table = Table(title="Effective configuration")
    table.add_column("Key")
    table.add_column("Value")
    table.add_column("Source")
    for entry in entries:
        table.add_row(entry.name, entry.value, entry.source)
    console.print(table)

    console.print("\n[bold]Config files[/bold]")
    for config_path, exists in config_file_paths(root):
        state = "present" if exists else "missing (built-in defaults)"
        console.print(f"  {config_path} — {state}")
