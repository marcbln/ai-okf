from pathlib import Path
from typing import Any

import typer
from git import Repo
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ai_okf.agent.kb_agent import build_agent
from ai_okf.config import DEFAULT_OUTPUT
from ai_okf.core.okf_bundle import (
    parse_okf_markdown,
    save_bundle_metadata,
    write_concept,
    write_index,
)
from ai_okf.core.scanner import scan_codebase
from ai_okf.models.plan import OKFConceptPlan

console = Console()


def init_command(  # type: ignore[no-untyped-def]
    path: str = typer.Argument(".", help="Path to the codebase to analyze"),
    output: str = typer.Option(
        str(DEFAULT_OUTPUT),
        "--output",
        "-o",
        help="Output directory for the OKF bundle",
    ),
    model: str = typer.Option(
        None, "--model", "-m", help="LLM model to use (default: deepseek-v4-flash-free)"
    ),
    api_base: str = typer.Option(
        None, "--api-base", help="OpenAI-compatible API base URL"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing OKF bundle"
    ),
):
    root = Path(path).resolve()
    output_dir = Path(output).resolve()

    if not root.exists() or not root.is_dir():
        console.print(f"[red]Error:[/red] Path '{path}' does not exist.")
        raise typer.Exit(1)

    if output_dir.exists() and not force:
        console.print(f"[yellow]Warning:[/yellow] Output directory '{output}' exists. Use -f to force.")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Scanning codebase structure...", total=None)
        files = scan_codebase(root)
        files_summary = "\n".join(f"- `{f.path}` ({f.language or 'unknown'})" for f in files)

        progress.add_task(description="Preparing agent and planning concepts...", total=None)
        agent = build_agent(model, api_base)
        deps: dict[str, Any] = {"root": str(root)}

        plan_prompt = (
            f"We are generating a codebase documentation wiki matching the OKF specification.\n"
            f"Here is the codebase file list:\n{files_summary}\n\n"
            f"Please identify key modules, classes, data models, entrypoints, configuration, or structural patterns. "
            f"Provide a structured plan containing the list of concept files to create."
        )

        try:
            plan_result = agent.run_sync(plan_prompt, deps=deps, output_type=list[OKFConceptPlan])
            plans: list[OKFConceptPlan] = plan_result.output
        except Exception as e:
            console.print(f"[red]Error generating plan via LLM:[/red] {e}")
            raise typer.Exit(1)

        concepts = []
        for plan in plans:
            progress.add_task(description=f"Drafting concept: {plan.concept_id}...", total=None)
            concept_prompt = (
                f"Generate a comprehensive OKF knowledge file of type '{plan.type}' for the concept:\n"
                f"ID: {plan.concept_id}\nTitle: {plan.title}\nDescription: {plan.description}\n\n"
                f"Inspect and extract structural knowledge from the following files: {', '.join(plan.files_to_read)}\n"
                f"Use read_file_content tool as needed to construct rich, precise, and verified documentation."
            )

            try:
                content_result = agent.run_sync(concept_prompt, deps=deps)
                concept = parse_okf_markdown(plan.concept_id, content_result.output)
                write_concept(output_dir, concept)
                concepts.append(concept)
            except Exception as e:
                console.print(f"[yellow]Skipping {plan.concept_id} due to generation failure:[/yellow] {e}")

        write_index(output_dir, concepts)

        current_sha = ""
        try:
            repo = Repo(root)
            if not repo.bare and repo.head.is_valid():
                current_sha = repo.head.commit.hexsha
        except Exception:
            pass

        save_bundle_metadata(output_dir, {"last_ingested_commit": current_sha})

    console.print(f"[green]OKF bundle successfully initialized with {len(concepts)} concepts at:[/green] {output_dir}")
