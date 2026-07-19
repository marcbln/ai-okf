from pathlib import Path
from typing import Any

import typer
from git import Repo
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ai_okf.agent.kb_agent import build_agent
from ai_okf.config import DEFAULT_OUTPUT
from ai_okf.core.git_scanner import get_changes_since
from ai_okf.core.okf_bundle import (
    load_bundle_metadata,
    save_bundle_metadata,
)

console = Console()


def update_command(  # type: ignore[no-untyped-def]
    path: str = typer.Argument(".", help="Path to the codebase to analyze"),
    output: str = typer.Option(
        str(DEFAULT_OUTPUT),
        "--output",
        "-o",
        help="Output directory for the OKF bundle",
    ),
    model: str = typer.Option(None, "--model", "-m", help="LLM model (format: provider/model)"),
    api_base: str = typer.Option(
        None, "--api-base", help="Override API base URL (provider default is inferred from model prefix)"
    ),
):
    root = Path(path).resolve()
    output_dir = Path(output).resolve()

    if not output_dir.exists():
        console.print(f"[red]Error:[/red] OKF bundle not found at '{output}'. Run 'okf init' first.")
        raise typer.Exit(1)

    metadata = load_bundle_metadata(output_dir)
    since_ref = metadata.get("last_ingested_commit", "HEAD")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Checking git changes...", total=None)
        changes = get_changes_since(root, since_ref)

        if not changes:
            console.print("[yellow]No git changes detected since last update.[/yellow]")
            return

        progress.add_task(description="Updating OKF bundle via LLM...", total=None)
        agent = build_agent(model, api_base)
        deps: dict[str, Any] = {"root": str(root)}

        prompt = (
            f"The codebase has evolved since the last documentation generation.\n"
            f"Here are the modifications:\n{changes}\n\n"
            f"Inspect the changed files using read_file_content and identify which existing OKF files in '{output}' "
            f"must be rewritten to match the new codebase structure, or if new concepts must be authored.\n"
            f"Return a summary of actions taken."
        )

        try:
            result = agent.run_sync(prompt, deps=deps)
            console.print(f"[green]Incremental analysis completed:[/green]\n{result.output}")

            try:
                repo = Repo(root)
                if not repo.bare and repo.head.is_valid():
                    metadata["last_ingested_commit"] = repo.head.commit.hexsha
                    save_bundle_metadata(output_dir, metadata)
            except Exception:
                pass

        except Exception as e:
            console.print(f"[red]Failed to run incremental update:[/red] {e}")
