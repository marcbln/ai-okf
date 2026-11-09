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
from ai_okf.config import (
    DEFAULT_MODEL,
    DEFAULT_OUTPUT,
    DEFAULT_WORKERS,
    PrivacyError,
    is_loopback_url,
    is_protected_path,
    resolve_api_base,
)
from ai_okf.core.okf_bundle import (
    parse_okf_markdown,
    save_bundle_metadata,
    write_concept,
    write_index,
)
from ai_okf.core.scanner import scan_codebase
from ai_okf.models.okf import CodebaseFile, OKFConcept, OKFFrontmatter
from ai_okf.models.plan import OKFConceptPlan
from ai_okf.project_config import ConfigError, load_project_config, resolve_value
from ai_okf.prompts import build_concept_prompt, build_plan_prompt

console = Console()

MAX_CONCEPTS = 8
MAX_SOURCE_CHARS = 24_000


def _load_sources(root: Path, files: list[str]) -> str:
    """Read the relevant note files verbatim, capped to the prompt budget."""
    chunks: list[str] = []
    remaining = MAX_SOURCE_CHARS
    for rel in files:
        if is_protected_path(rel):
            continue
        path = (root / rel).resolve()
        if path != root and root not in path.parents:
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(text) > remaining:
            text = text[:remaining] + "\n... [truncated]"
        chunks.append(f"### {rel}\n{text}")
        remaining -= len(text)
        if remaining <= 0:
            break
    return "\n\n".join(chunks)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _normalize_plans(plans: list[OKFConceptPlan]) -> list[OKFConceptPlan]:
    normalized: list[OKFConceptPlan] = []
    seen: set[str] = set()
    for index, plan in enumerate(plans, 1):
        slug = _slugify(plan.concept_id or plan.title)
        if not slug or not re.search(r"[a-z]", slug):
            slug = f"concept-{index}"
        if slug in seen:
            continue
        seen.add(slug)
        normalized.append(plan.model_copy(update={"concept_id": slug}))
        if len(normalized) >= MAX_CONCEPTS:
            break
    return normalized


def _strip_code_fence(text: str) -> str:
    match = re.match(r"^```[a-zA-Z0-9_-]*\s*\n(.*?)\n```\s*$", text.strip(), re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def _plans_from_data(data: list[Any]) -> list[OKFConceptPlan]:
    plans: list[OKFConceptPlan] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            plans.append(OKFConceptPlan(**item))
        except Exception:
            continue
    return plans


def _fallback_plans(files: list[CodebaseFile]) -> list[OKFConceptPlan]:
    """Group notes by top-level folder when the LLM plan is unusable."""
    groups: dict[str, list[str]] = {}
    for f in files:
        parts = Path(f.path).parts
        key = parts[0] if len(parts) > 1 else "root"
        groups.setdefault(key, []).append(f.path)
    plans: list[OKFConceptPlan] = []
    for key, paths in sorted(groups.items())[:MAX_CONCEPTS]:
        slug = _slugify(key) or f"group-{len(plans) + 1}"
        plans.append(
            OKFConceptPlan(
                concept_id=slug,
                type="Theme",
                title=key.replace("-", " ").title(),
                description=f"Notes grouped under {key}.",
                files_to_read=paths,
            )
        )
    return plans


def _parse_json_array(text: str) -> list[Any]:
    """Extract the first JSON array from model output, tolerating prose."""
    candidates = [text]
    fence = re.search(r"```(?:json)?\n?(.*?)\n?```", text, re.DOTALL)
    if fence:
        candidates.insert(0, fence.group(1))
    decoder = json.JSONDecoder()
    for candidate in candidates:
        for match in re.finditer(r"\[", candidate):
            try:
                value, _ = decoder.raw_decode(candidate[match.start() :])
            except json.JSONDecodeError:
                continue
            if isinstance(value, list):
                return value
    raise ValueError("No JSON array found in model output")


def _plan_via_text(
    agent: Any,
    deps: dict[str, Any],
    plan_prompt: str,
) -> list[OKFConceptPlan]:
    fallback_prompt = (
        f"{plan_prompt}\n\n"
        "Return ONLY a raw JSON array (no markdown, no code fences) where each "
        "object has keys: concept_id, type, title, description, files_to_read. "
        "Output nothing except the JSON array."
    )
    result = agent.run_sync(fallback_prompt, deps=deps)
    plans = _plans_from_data(_parse_json_array(result.output))
    if not plans:
        raise ValueError("model returned no valid concept plan objects")
    return plans


def _draft_concept(
    plan: OKFConceptPlan,
    agent: Any,
    deps: dict[str, Any],
    output_dir: Path,
    profile: str,
) -> Any:
    sources = None
    if profile == "notes":
        sources = _load_sources(Path(deps["root"]).resolve(), plan.files_to_read)
    raw = agent.run_sync(build_concept_prompt(profile, plan, sources), deps=deps).output
    if profile == "notes" and not raw.lstrip().startswith("---"):
        concept = OKFConcept(
            concept_id=plan.concept_id,
            frontmatter=OKFFrontmatter(
                type=plan.type,
                title=plan.title,
                description=plan.description,
                tags=[],
            ),
            body=_strip_code_fence(raw),
        )
    else:
        concept = parse_okf_markdown(plan.concept_id, raw)
    write_concept(output_dir, concept)
    return concept


def _resolve_workers(value: Any, base_url: str) -> int:
    if value is None:
        return 1 if is_loopback_url(base_url) else DEFAULT_WORKERS
    try:
        workers = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("--workers must be a positive integer") from exc
    if workers < 1:
        raise ValueError("--workers must be a positive integer")
    return workers


def init_command(  # type: ignore[no-untyped-def]
    path: str = typer.Argument(".", help="Path to the notes or codebase to analyze"),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for the OKF bundle (default: .okf-bundle)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model (provider/model)",
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
    workers: int | None = typer.Option(
        None,
        "--workers",
        help="Parallel draft workers (default: 4, or 1 for a local endpoint)",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing OKF bundle"
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

    if not root.exists() or not root.is_dir():
        console.print(f"[red]Error:[/red] Path '{path}' does not exist.")
        raise typer.Exit(1)

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
    resolved_workers, _ = resolve_value(workers, "OKF_WORKERS", project.workers, None)

    output_path = Path(str(resolved_output))
    if not output_path.is_absolute():
        output_path = root / output_path
    output_dir = output_path.resolve()
    if output_dir.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] Output directory '{output_dir}' exists. "
            "Use -f to force."
        )
        raise typer.Exit(1)

    base_url = resolve_api_base(
        str(resolved_model),
        resolved_api_base if isinstance(resolved_api_base, str) else None,
    )
    try:
        worker_count = _resolve_workers(resolved_workers, base_url)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(2) from exc

    console.print(f"[dim]Profile:[/dim] [cyan]{resolved_profile}[/cyan]")
    console.print(f"[dim]Using model:[/dim] [cyan]{resolved_model}[/cyan]")
    console.print(f"[dim]Endpoint:[/dim] [cyan]{base_url}[/cyan]")
    console.print(f"[dim]Workers:[/dim] [cyan]{worker_count}[/cyan]")
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
            description="Scanning project structure...", total=None
        )
        files = scan_codebase(root, exclude_dirs={output_dir})
        progress.remove_task(scan_task)
        files_summary = "\n".join(
            f"- `{f.path}` ({f.language or 'unknown'})" for f in files
        )

        plan_task = progress.add_task(
            description="Preparing agent and planning concepts...", total=None
        )
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

        plan_prompt = build_plan_prompt(str(resolved_profile), files_summary)

        try:
            if is_loopback_url(base_url):
                console.print("[dim]Local endpoint: using text-based planning.[/dim]")
                plans = _plan_via_text(agent, deps, plan_prompt)
            else:
                try:
                    plan_result = agent.run_sync(
                        plan_prompt, deps=deps, output_type=list[OKFConceptPlan]
                    )
                    plans = plan_result.output
                except Exception:
                    console.print(
                        "[yellow]Structured output not supported by model, falling "
                        "back to text-based planning...[/yellow]"
                    )
                    plans = _plan_via_text(agent, deps, plan_prompt)
        except Exception as exc:
            console.print(
                f"[yellow]LLM planning failed ({exc}); using a folder-based plan."
                "[/yellow]"
            )
            plans = _fallback_plans(files)

        plans = _normalize_plans(plans)
        progress.remove_task(plan_task)

        concepts = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as pool:
            fut_to_task: dict[concurrent.futures.Future[Any], Any] = {}
            for plan in plans:
                task_id = progress.add_task(
                    description=f"Drafting concept: {plan.concept_id}...", total=None
                )
                future = pool.submit(
                    _draft_concept,
                    plan,
                    agent,
                    deps,
                    output_dir,
                    str(resolved_profile),
                )
                fut_to_task[future] = task_id

            for future in concurrent.futures.as_completed(fut_to_task):
                task_id = fut_to_task[future]
                progress.remove_task(task_id)
                try:
                    concept = future.result()
                    concepts.append(concept)
                except Exception as e:
                    console.print(
                        f"[yellow]Skipping concept drafting due to generation "
                        f"failure:[/yellow] {e}"
                    )

        write_index(output_dir, concepts)

        current_sha = ""
        try:
            repo = Repo(root)
            if not repo.bare and repo.head.is_valid():
                current_sha = repo.head.commit.hexsha
        except Exception:
            pass

        save_bundle_metadata(
            output_dir,
            {
                "last_ingested_commit": current_sha,
                "concepts": [plan.model_dump() for plan in plans],
            },
        )

    console.print(
        f"[green]OKF bundle successfully initialized with {len(concepts)} "
        f"concepts at:[/green] {output_dir}"
    )
