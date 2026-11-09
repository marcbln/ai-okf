from pathlib import Path
from typing import Any

import typer
from git import Repo
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ai_okf.agent.kb_agent import build_agent
from ai_okf.commands.init_cmd import _draft_concept, _fallback_plans
from ai_okf.config import (
    DEFAULT_MODEL,
    DEFAULT_OUTPUT,
    PrivacyError,
)
from ai_okf.core.git_scanner import get_changed_files
from ai_okf.core.okf_bundle import (
    load_bundle_metadata,
    read_concepts,
    save_bundle_metadata,
    write_index,
)
from ai_okf.models.okf import CodebaseFile
from ai_okf.models.plan import OKFConceptPlan
from ai_okf.project_config import ConfigError, load_project_config, resolve_value

console = Console()


def update_command(  # type: ignore[no-untyped-def]
    path: str = typer.Argument(".", help="Path to the notes or codebase to analyze"),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for the OKF bundle (default: .okf-bundle)",
    ),
    model: str | None = typer.Option(
        None, "--model", "-m", help="LLM model (format: provider/model)"
    ),
    api_base: str | None = typer.Option(
        None,
        "--api-base",
        help="Override API base URL (provider default is inferred from model prefix)",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Prompt profile: 'code' or 'notes' (default: code)",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show LLM requests and responses"
    ),
    cloud: bool = typer.Option(
        False,
        "--cloud",
        help="Allow a non-local LLM endpoint (sends code/notes off this machine).",
    ),
):
    root = Path(path).resolve()

    try:
        project, config_path = load_project_config(root)
    except ConfigError as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        raise typer.Exit(2) from exc
    if config_path is not None:
        console.print(f"[dim]Config:[/dim] [cyan]{config_path}[/cyan]")

    resolved_profile, _ = resolve_value(profile, "OKF_PROFILE", project.profile, "code")
    if resolved_profile not in ("code", "notes"):
        console.print("[red]Error:[/red] --profile must be 'code' or 'notes'.")
        raise typer.Exit(2)

    resolved_model, _ = resolve_value(model, "OKF_MODEL", project.model, DEFAULT_MODEL)
    resolved_api_base, _ = resolve_value(
        api_base, "OKF_API_BASE", project.api_base, None
    )
    resolved_output, _ = resolve_value(
        output, "OKF_OUTPUT", project.output, str(DEFAULT_OUTPUT)
    )

    output_path = Path(str(resolved_output))
    if not output_path.is_absolute():
        output_path = root / output_path
    output_dir = output_path.resolve()

    console.print(f"[dim]Profile:[/dim] [cyan]{resolved_profile}[/cyan]")
    console.print(f"[dim]Using model:[/dim] [cyan]{resolved_model}[/cyan]")
    if verbose:
        console.print(
            "[dim]Verbose mode enabled — LLM requests and responses will be shown[/dim]"
        )

    if not output_dir.exists():
        console.print(
            f"[red]Error:[/red] OKF bundle not found at '{output_dir}'. "
            "Run 'okf init' first."
        )
        raise typer.Exit(1)

    metadata = load_bundle_metadata(output_dir)
    since_ref = metadata.get("last_ingested_commit", "HEAD")
    raw_plans = metadata.get("concepts") or []
    try:
        plans = [OKFConceptPlan(**item) for item in raw_plans]
    except TypeError:
        plans = []
    if not plans:
        console.print(
            "[red]Error:[/red] This bundle has no concept map. "
            "Run 'okf init -f' once to create one."
        )
        raise typer.Exit(1)

    changed = get_changed_files(root, since_ref)
    if not changed:
        console.print("[yellow]No git changes detected since last update.[/yellow]")
        return

    affected = [p for p in plans if set(p.files_to_read) & set(changed)]
    covered = {f for p in plans for f in p.files_to_read}
    uncovered = [f for f in changed if f not in covered]
    if uncovered:
        existing_ids = {p.concept_id for p in plans}
        for new_plan in _fallback_plans([CodebaseFile(path=f) for f in uncovered]):
            if new_plan.concept_id in existing_ids:
                new_plan = new_plan.model_copy(
                    update={"concept_id": f"{new_plan.concept_id}-updates"}
                )
            plans.append(new_plan)
            affected.append(new_plan)

    if not affected:
        console.print(
            "[yellow]Changed files are not part of the wiki; "
            "nothing to update.[/yellow]"
        )
        return

    console.print(f"[dim]Changed files:[/dim] {len(changed)}")
    console.print(f"[dim]Concepts to refresh:[/dim] {len(affected)}")

    try:
        agent = build_agent(
            str(resolved_model),
            resolved_api_base if isinstance(resolved_api_base, str) else None,
            verbose=verbose,
            allow_cloud=cloud,
            profile=str(resolved_profile),
        )
    except PrivacyError as exc:
        console.print(f"[red]Privacy error:[/red] {exc}")
        raise typer.Exit(2) from exc

    deps: dict[str, Any] = {
        "root": str(root),
        "output": str(output_dir),
    }
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for plan in affected:
            task_id = progress.add_task(
                description=f"Updating {plan.concept_id}...", total=None
            )
            try:
                _draft_concept(plan, agent, deps, output_dir, str(resolved_profile))
            except Exception as exc:
                console.print(
                    f"[yellow]Failed to update {plan.concept_id}:[/yellow] {exc}"
                )
            finally:
                progress.remove_task(task_id)

        write_index(output_dir, read_concepts(output_dir))

    current_sha = ""
    try:
        repo = Repo(root)
        if not repo.bare and repo.head.is_valid():
            current_sha = repo.head.commit.hexsha
    except Exception:
        pass

    metadata["last_ingested_commit"] = current_sha
    metadata["concepts"] = [plan.model_dump() for plan in plans]
    save_bundle_metadata(output_dir, metadata)

    console.print(f"[green]Updated {len(affected)} concept(s) at:[/green] {output_dir}")
