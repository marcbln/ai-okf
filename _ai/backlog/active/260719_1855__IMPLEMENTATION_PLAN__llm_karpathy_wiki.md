---
filename: "_ai/backlog/active/260719_1855__IMPLEMENTATION_PLAN__llm_karpathy_wiki.md"
title: "Implement LLM-Driven Karpathy Wiki Generation & Updates via PydanticAI 2.0"
createdAt: 2026-07-19 18:55
updatedAt: 2026-07-19 18:55
status: draft
priority: high
tags: [pydantic-ai-2, llm-wiki, okf, cli-commands]
estimatedComplexity: moderate
documentType: IMPLEMENTATION_PLAN
---
# Implementation Plan: LLM-Driven Karpathy Wiki Generation for Codebases

## 1. Problem Statement
The current implementation of the `okf` tool is a structural shell. Although it instantiates a PydanticAI agent, it performs static folder walking to generate hardcoded indices. It does not load the agent capabilities, register tools dynamically, or invoke the LLM during either the `init` or `update` processes.

## 2. Solution Summary
We will complete the implementation of the `ai-okf` framework by wiring PydanticAI 2.0 capabilities and transitioning both commands to run LLM-powered extraction loops:
1. **Capability Integration:** Register the `CodebaseAnalysisCapability` and `OKFGenerationCapability` with the agent in `kb_agent.py`.
2. **Robust Dependency Injection:** Update the `read_file_content` tool to use PydanticAI's `RunContext` to resolve paths relative to the analyzed repository root dynamically.
3. **Multi-Step Ingest Planning:** Instead of running single-turn calls that exceed model token limits, the agent will:
   - Perform a structural scan of the directory tree.
   - Run a planning phase using structured outputs (`result_type=list[OKFConceptPlan]`) to identify key modules, models, APIs, and cross-cutting concepts.
   - Sequentially generate the content of each Markdown page by reading targeted files.
4. **Git-Aware Incremental Updates:** Implement a state preservation file (`.okf-metadata.json`) containing the latest processed Git commit SHA. When running `okf update`, only modified/added files will be analyzed, prompting the agent to update target Markdown files or generate new pages while retaining existing human/agent-written structures.

## 3. Project Environment
- **Project Name:** AI-OKF (Knowledge Base Agent)
- **Primary Frameworks:** PydanticAI 2.0, Typer, Rich, GitPython
- **Source root:** `src/`

---

## 4. Multi-Phased Execution Plan

### Phase 1: Dependency Injection and Capability Activation
In this phase, we modify capability tools to use PydanticAI's context-aware dependency model so that the codebase tool can find the root directory at execution time, and hook the capabilities into our central builder.

#### [MODIFY] `src/ai_okf/agent/capabilities/code_analysis.py`
```python
from pathlib import Path
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import FunctionToolset


def read_file_content(ctx: RunContext[dict[str, Any]], path: str) -> str:
    """Read the contents of a file in the codebase.

    Args:
        ctx: PydanticAI run context containing dependencies.
        path: Relative path of the file to inspect.
    """
    root = ctx.deps.get("root", ".") if ctx.deps else "."
    full = Path(root) / path
    if not full.exists() or not full.is_file():
        return ""
    try:
        text = full.read_text(encoding="utf-8", errors="replace")
        if len(text) > 100_000:
            text = text[:100_000] + "\n... [truncated at 100KB]"
        return text
    except Exception:
        return ""


class CodebaseAnalysisCapability(AbstractCapability[dict[str, Any]]):
    id: str = "codebase-analysis"
    description: str = (
        "Capability for analyzing codebase files: reading file contents, "
        "identifying patterns, and extracting structural information."
    )
    defer_loading: bool = True

    def get_instructions(self) -> str:
        return (
            "You are a codebase analysis expert. Given a list of files in a project, "
            "analyze each file's purpose, structure, and key abstractions. "
            "Identify: modules/packages, classes, functions, data models, "
            "API endpoints, configuration, test patterns, dependencies. "
            "Use read_file_content to inspect relevant files before producing analysis."
        )

    def get_toolset(self) -> FunctionToolset:
        return FunctionToolset(tools=[read_file_content])
```

#### [MODIFY] `src/ai_okf/agent/kb_agent.py`
```python
import os
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from ai_okf.agent.capabilities.code_analysis import CodebaseAnalysisCapability
from ai_okf.agent.capabilities.okf_generation import OKFGenerationCapability
from ai_okf.config import DEFAULT_API_BASE, DEFAULT_MODEL


def build_agent(model_name: str | None = None, api_base: str | None = None) -> Agent[dict[str, Any], str]:
    model_name = model_name or os.environ.get("OKF_MODEL", DEFAULT_MODEL)
    api_base = api_base or os.environ.get("OKF_API_BASE", DEFAULT_API_BASE)
    api_key = os.environ.get("OKF_API_KEY", "no-key-required")
    
    model = OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(
            base_url=f"{api_base.rstrip('/')}/",
            api_key=api_key,
        ),
    )
    
    return Agent(
        model,
        deps_type=dict[str, Any],
        capabilities=[CodebaseAnalysisCapability(), OKFGenerationCapability()]
    )
```

---

### Phase 2: Schema Planning, Markdown Parsing, and Metadata Preservation
Define the structure used by the agent to plan out concepts, write helpers to parse Markdown raw strings generated by the LLM into native OKF models, and manage the commit state tracker file.

#### [NEW FILE] `src/ai_okf/models/plan.py`
```python
from pydantic import BaseModel, Field


class OKFConceptPlan(BaseModel):
    """A proposed OKF concept to generate during codebase ingestion."""
    concept_id: str = Field(description="Unique, lowercase, kebab-case identifier for the concept (e.g. core-auth).")
    type: str = Field(description="OKF type (Module, Class, API Endpoint, Data Model, Configuration, Pattern, etc.)")
    title: str = Field(description="Clear title of the concept.")
    description: str = Field(description="Brief summary of what this concept encapsulates.")
    files_to_read: list[str] = Field(description="Relative paths to files the LLM should read to generate this concept.")
```

#### [MODIFY] `src/ai_okf/core/okf_bundle.py`
```python
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from ai_okf.models.okf import OKFConcept, OKFFrontmatter

METADATA_FILE = ".okf-metadata.json"


def write_concept(output_dir: Path, concept: OKFConcept) -> Path:
    path = output_dir / f"{concept.concept_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = concept.frontmatter.model_dump(exclude_none=True)
    ts = concept.frontmatter.timestamp or datetime.now()
    frontmatter["timestamp"] = ts.isoformat()
    fm = yaml.dump(frontmatter, sort_keys=False).strip()
    content = f"---\n{fm}\n---\n\n{concept.body.strip()}\n"
    path.write_text(content, encoding="utf-8")
    return path


def concept_exists(output_dir: Path, concept_id: str) -> bool:
    return (output_dir / f"{concept_id}.md").exists()


def write_index(output_dir: Path, concepts: list[OKFConcept]) -> None:
    lines: list[str] = []
    by_type: dict[str, list[OKFConcept]] = {}
    for c in concepts:
        by_type.setdefault(c.frontmatter.type, []).append(c)
    for type_name, items in sorted(by_type.items()):
        plural = type_name + "s"
        lines.append(f"# {plural}\n")
        for c in items:
            desc = c.frontmatter.description or ""
            title = c.frontmatter.title or c.concept_id
            lines.append(f"* [{title}]({c.concept_id}.md) - {desc}")
        lines.append("")
    (output_dir / "index.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def parse_okf_markdown(concept_id: str, markdown_text: str) -> OKFConcept:
    """Parse raw Markdown output from the LLM containing YAML frontmatter."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", markdown_text.strip(), re.DOTALL)
    if not match:
        return OKFConcept(
            concept_id=concept_id,
            frontmatter=OKFFrontmatter(type="Concept", title=concept_id),
            body=markdown_text
        )
    fm_str, body = match.groups()
    try:
        fm_dict = yaml.safe_load(fm_str) or {}
    except Exception:
        fm_dict = {}

    frontmatter = OKFFrontmatter(
        type=fm_dict.get("type", "Concept"),
        title=fm_dict.get("title") or concept_id,
        description=fm_dict.get("description"),
        resource=fm_dict.get("resource"),
        tags=fm_dict.get("tags", []),
    )
    return OKFConcept(
        concept_id=concept_id,
        frontmatter=frontmatter,
        body=body.strip()
    )


def save_bundle_metadata(output_dir: Path, data: dict[str, Any]) -> None:
    """Save metadata such as processed commit hashes."""
    (output_dir / METADATA_FILE).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_bundle_metadata(output_dir: Path) -> dict[str, Any]:
    """Load metadata of the generated bundle."""
    file_path = output_dir / METADATA_FILE
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
```

---

### Phase 3: Implementing LLM execution in CLI commands

We now adapt `init_cmd.py` to draft ingestion plans and execute them through PydanticAI. 

#### [MODIFY] `src/ai_okf/commands/init_cmd.py`
```python
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
        # Step 1: Scan Structure
        progress.add_task(description="Scanning codebase structure...", total=None)
        files = scan_codebase(root)
        files_summary = "\n".join(f"- `{f.path}` ({f.language or 'unknown'})" for f in files)

        # Step 2: Build Planning Agent
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
            plan_result = agent.run_sync(plan_prompt, deps=deps, result_type=list[OKFConceptPlan])
            plans: list[OKFConceptPlan] = plan_result.output
        except Exception as e:
            console.print(f"[red]Error generating plan via LLM:[/red] {e}")
            raise typer.Exit(1)

        # Step 3: Sequential Content Generation
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

        # Step 4: Write indexes and save Git Checkpoint
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
```

#### [MODIFY] `src/ai_okf/commands/update_cmd.py`
```python
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
    parse_okf_markdown,
    save_bundle_metadata,
    write_concept,
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
    model: str = typer.Option(None, "--model", "-m", help="LLM model to use"),
    api_base: str = typer.Option(
        None, "--api-base", help="OpenAI-compatible API base URL"
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

        # Prompt the agent to inspect diffs and rewrite/append concepts accordingly
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

            # Capture current git commit state
            try:
                repo = Repo(root)
                if not repo.bare and repo.head.is_valid():
                    metadata["last_ingested_commit"] = repo.head.commit.hexsha
                    save_bundle_metadata(output_dir, metadata)
            except Exception:
                pass

        except Exception as e:
            console.print(f"[red]Failed to run incremental update:[/red] {e}")
```

---

### Phase 4: Project Housekeeping

Ensure standard cleanups are performed. We update `.gitignore` and add an explanation of the Karpathy Wiki pattern to `README.md`.

#### [MODIFY] `.gitignore`
```
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.env
dist/
build/
*.egg
.DS_Store
.okf-bundle/
.okf-metadata.json
```

#### [MODIFY] `README.md`
```markdown
# AI-OKF

OKF Knowledge Base Agent — automatically explores codebases and generates structured **OKF (Open Knowledge Format)** knowledge bundles.

## Karpathy LLM Wiki Architecture
Unlike standard chunk-and-search vector RAG models which are stateless, `ai-okf` generates a persistent, compounding, structured knowledge base directly written in Git-versioned Markdown. 
1. **Planning Phase:** A deep analysis mapping codebase structures to discrete OKF Concepts.
2. **Modular Compilation:** The agent reads focused file bundles and authors isolated concept sheets with standard frontmatter.
3. **Diff-Driven Evolution:** Updates run iteratively over code changes, keeping documentation fresh without full codebase rebuilds.

## Quick Start

```bash
uv venv
source .venv/bin/activate && uv pip install -e ".[dev]"

# Set your API endpoint and model (defaults to opencode.ai free tier)
export OKF_MODEL="deepseek-v4-flash-free"
export OKF_API_BASE="https://opencode.ai/zen/v1"

# Initialize a knowledge bundle from a codebase
okf init /path/to/project --output ./knowledge-base

# Update it incrementally after making changes
okf update /path/to/project --output ./knowledge-base
```
```

---

### Phase 5: Generating the Implementation Report
At the completion of these stages, the agent will execute verification tests and write a detailed implementation report summarizing the changes.

#### [NEW FILE] `_ai/backlog/reports/260719_1855__IMPLEMENTATION_REPORT__llm_karpathy_wiki.md`
```markdown
---
filename: "_ai/backlog/reports/260719_1855__IMPLEMENTATION_REPORT__llm_karpathy_wiki.md"
title: "Report: Implement LLM-Driven Karpathy Wiki Generation & Updates"
createdAt: 2026-07-19 18:55
updatedAt: 2026-07-19 18:55
planFile: "_ai/backlog/active/260719_1855__IMPLEMENTATION_PLAN__llm_karpathy_wiki.md"
project: "ai-okf"
status: completed
filesCreated: 2
filesModified: 6
filesDeleted: 0
tags: [pydantic-ai-2, core-capabilities, integration]
documentType: IMPLEMENTATION_REPORT
---

# Ingestion Report: Karpathy LLM Wiki Integration

## 1. Summary
The implementation successfully moves `ai-okf` from hardcoded static index files to dynamic, LLM-orchestrated compilation loops using PydanticAI 2.0 capabilities. The tool now runs modular extraction cycles, maps structure schemas, and performs incremental updates using Git differentials.

## 2. Files Changed
- **New Files:**
  - `src/ai_okf/models/plan.py`: Defines the OKF planning schema used for structural parsing.
  - `_ai/backlog/reports/260719_1855__IMPLEMENTATION_REPORT__llm_karpathy_wiki.md`: This file.
- **Modified Files:**
  - `src/ai_okf/agent/capabilities/code_analysis.py`: Refactored to accept dependency context.
  - `src/ai_okf/agent/kb_agent.py`: Loaded the two main capabilities into the agent builder.
  - `src/ai_okf/core/okf_bundle.py`: Added parser for Markdown frontmatter extraction and metadata trackers.
  - `src/ai_okf/commands/init_cmd.py`: Completely rewrote the setup logic to support two-phase ingestion.
  - `src/ai_okf/commands/update_cmd.py`: Wired the modification diffs up to the agent.
  - `README.md` & `.gitignore`: Added tool updates.

## 3. Key Decisions
- **Two-phase Ingest:** Instead of passing the entire codebase in one prompt, the agent plans a blueprint of the concepts and compiles them sequentially. This avoids hitting token window limitations and makes the generation pipeline robust against rate limits.
- **State Checkpoints:** Storing `last_ingested_commit` in `.okf-metadata.json` ensures that incremental updates stay aligned with code modification dates.
```
