from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ai_okf.config import DEFAULT_OUTPUT
from ai_okf.core.git_scanner import get_changes_since

console = Console()


def update_command(  # type: ignore[no-untyped-def]
    path: str = typer.Argument(".", help="Path to the codebase to analyze"),
    output: str = typer.Option(
        str(DEFAULT_OUTPUT),
        "--output",
        "-o",
        help="Output directory for the OKF bundle",
    ),
    model: str = typer.Option(None, "--model", "-m", help="LLM model to use"),
    api_base: str = typer.Option(
        None, "--api-base", help="OpenAI-compatible API base URL"
    ),
):
    root = Path(path).resolve()
    output_dir = Path(output).resolve()

    if not output_dir.exists():
        console.print(
            f"[red]Error:[/red] OKF bundle not found at '{output}'. "
            f"Run 'okf init' first."
        )
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Checking git changes...", total=None)
        changes = get_changes_since(root)

        progress.add_task(description="Analyzing incremental changes...", total=None)

        if changes:
            console.print(
                f"[dim]{changes[:500] if changes else 'No changes detected.'}[/dim]"
            )
        else:
            console.print("[yellow]No changes detected since last update.[/yellow]")
