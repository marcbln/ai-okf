import concurrent.futures
import json
import re
from pathlib import Path
from typing import Any

import typer
from git import Repo
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ai_okf.agent.kb_agent import build_agent
from ai_okf.config import DEFAULT_MODEL, DEFAULT_OUTPUT
from ai_okf.core.okf_bundle import (
    parse_okf_markdown,
    save_bundle_metadata,
    write_concept,
    write_index,
)
from ai_okf.core.scanner import scan_codebase
from ai_okf.models.plan import OKFConceptPlan

console = Console()

MAX_DRAFT_WORKERS = 4


def _draft_concept(
    plan: OKFConceptPlan,
    agent: Any,
    deps: dict[str, Any],
    output_dir: Path,
) -> Any:
    concept_prompt = (
        f"Generate a comprehensive OKF knowledge file of type '{plan.type}' for the concept:\n"
        f"ID: {plan.concept_id}\nTitle: {plan.title}\nDescription: {plan.description}\n\n"
        f"Inspect and extract structural knowledge from the following files: {', '.join(plan.files_to_read)}\n"
        f"Use read_file_content tool as needed to construct rich, precise, and verified documentation."
    )
    content_result = agent.run_sync(concept_prompt, deps=deps)
    concept = parse_okf_markdown(plan.concept_id, content_result.output)
    write_concept(output_dir, concept)
    return concept


def init_command(  # type: ignore[no-untyped-def]
    path: str = typer.Argument(".", help="Path to the codebase to analyze"),
    output: str = typer.Option(
        str(DEFAULT_OUTPUT),
        "--output",
        "-o",
        help="Output directory for the OKF bundle",
    ),
    model: str = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model (format: provider/model, default: opencode-zen/nemotron-3-ultra-free)",
    ),
    api_base: str = typer.Option(
        None,
        "--api-base",
        help="Override API base URL (provider default is inferred from model prefix)",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing OKF bundle"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show LLM requests and responses"
    ),
):
    root = Path(path).resolve()
    output_dir = Path(output).resolve()

    if not root.exists() or not root.is_dir():
        console.print(f"[red]Error:[/red] Path '{path}' does not exist.")
        raise typer.Exit(1)

    if output_dir.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] Output directory '{output}' exists. Use -f to force."
        )
        raise typer.Exit(1)

    resolved_model = model or DEFAULT_MODEL
    console.print(f"[dim]Using model:[/dim] [cyan]{resolved_model}[/cyan]")
    if verbose:
        console.print(
            "[dim]Verbose mode enabled — LLM requests and responses will be shown[/dim]"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        scan_task = progress.add_task(
            description="Scanning codebase structure...", total=None
        )
        files = scan_codebase(root)
        progress.remove_task(scan_task)
        files_summary = "\n".join(
            f"- `{f.path}` ({f.language or 'unknown'})" for f in files
        )

        plan_task = progress.add_task(
            description="Preparing agent and planning concepts...", total=None
        )
        agent = build_agent(model, api_base, verbose=verbose)
        deps: dict[str, Any] = {"root": str(root)}

        plan_prompt = (
            f"We are generating a codebase documentation wiki matching the OKF specification.\n"
            f"Here is the codebase file list:\n{files_summary}\n\n"
            f"Please identify key modules, classes, data models, entrypoints, configuration, or structural patterns. "
            f"Provide a structured plan containing the list of concept files to create."
        )

        try:
            plan_result = agent.run_sync(
                plan_prompt, deps=deps, output_type=list[OKFConceptPlan]
            )
            plans: list[OKFConceptPlan] = plan_result.output
        except Exception:
            console.print(
                "[yellow]Structured output not supported by model, falling back to text-based planning...[/yellow]"
            )
            fallback_prompt = (
                f"{plan_prompt}\n\n"
                f"Return ONLY a raw JSON array (no markdown, no code fences) "
                f"where each object has keys: concept_id, type, title, description, files_to_read. "
                f"Output nothing except the JSON array."
            )
            fallback_result = agent.run_sync(fallback_prompt, deps=deps)
            text = fallback_result.output
            json_match = re.search(r"```(?:json)?\n?(.*?)\n?```", text, re.DOTALL)
            raw = json_match.group(1) if json_match else text.strip()
            data = json.loads(raw)
            plans = [OKFConceptPlan(**item) for item in data]

        progress.remove_task(plan_task)

        concepts = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=MAX_DRAFT_WORKERS
        ) as pool:
            fut_to_task: dict[concurrent.futures.Future[Any], int] = {}
            for plan in plans:
                task_id = progress.add_task(
                    description=f"Drafting concept: {plan.concept_id}...", total=None
                )
                future = pool.submit(_draft_concept, plan, agent, deps, output_dir)
                fut_to_task[future] = task_id

            for future in concurrent.futures.as_completed(fut_to_task):
                task_id = fut_to_task[future]
                progress.remove_task(task_id)
                try:
                    concept = future.result()
                    concepts.append(concept)
                except Exception as e:
                    console.print(
                        f"[yellow]Skipping concept drafting due to generation failure:[/yellow] {e}"
                    )

        write_index(output_dir, concepts)

        current_sha = ""
        try:
            repo = Repo(root)
            if not repo.bare and repo.head.is_valid():
                current_sha = repo.head.commit.hexsha
        except Exception:
            pass

        save_bundle_metadata(output_dir, {"last_ingested_commit": current_sha})

    console.print(
        f"[green]OKF bundle successfully initialized with {len(concepts)} concepts at:[/green] {output_dir}"
    )
