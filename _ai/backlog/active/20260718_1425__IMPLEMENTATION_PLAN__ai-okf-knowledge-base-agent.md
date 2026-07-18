---
filename: "_ai/backlog/active/20260718_1425__IMPLEMENTATION_PLAN__ai-okf-knowledge-base-agent.md"
title: "AI-OKF: Knowledge Base Agent for Codebase Exploration"
createdAt: 2026-07-18 14:25
updatedAt: 2026-07-18 14:25
status: draft
priority: high
tags: [okf, pydantic-ai, knowledge-base, codebase-exploration]
estimatedComplexity: complex
documentType: IMPLEMENTATION_PLAN
---

# AI-OKF: Knowledge Base Agent

## Problem

There is no tool that automatically creates and maintains an **OKF (Open Knowledge Format)** knowledge bundle from a codebase. Developers need a way to generate structured, LLM-friendly knowledge documents that capture:
- The codebase's architecture, modules, and key abstractions
- Database schemas, API endpoints, and data flows
- Business logic and design patterns
- Git history context (why things changed, major refactors)

Without such a tool, knowledge remains locked in source code comments, README files, and developer memory. Manual documentation is rarely written and quickly goes stale.

## Solution

Build `ai-okf`, a CLI tool that uses **PydanticAI 2.0** with composable **capabilities** to:

1. **`init`** — Scan an entire codebase, analyze it via an LLM, and generate a complete OKF bundle (hierarchical markdown with YAML frontmatter).
2. **`update`** — Incrementally update the OKF bundle based on git changes since the last run, preserving existing knowledge while adding/refreshing only what changed.

The tool uses the **capability composition pattern** from PydanticAI 2.0: codebase scanning, git analysis, and OKF generation are each separate capabilities that plug into a central agent. The model defaults to `deepseek-v4-flash-free` via the opencode API but is configurable to any OpenAI-compatible endpoint.

## Project Environment

- **Project Name**: ai-okf
- **Project Root**: `/home/marc/devel/ai-okf`
- **Language**: Python 3.12+
- **Package Manager**: uv
- **Key Dependencies**: pydantic-ai>=2.5.0, typer, rich, pyyaml, gitpython
- **Entry Point**: `okf` CLI command (via `[project.scripts]`)

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        CLI (Typer)                           │
│  okf init    <path> [--output <dir>] [--model <model>]      │
│  okf update  <path> [--output <dir>] [--model <model>]      │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    PydanticAI Agent                          │
│  Composed from capabilities:                                 │
│  • CodebaseScannerCapability  — walk files, infer types      │
│  • GitHistoryCapability       — analyze git log/diff         │
│  • OKFGenerationCapability    — produce OKF markdown         │
└──────────────────────┬───────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
┌──────────────────┐   ┌──────────────────────────┐
│  File Scanner     │   │  OKF Bundle Writer       │
│  (walker + parser)│   │  (creates .md files)     │
└──────────────────┘   └──────────────────────────┘
```

## Implementation Phases

### Phase 1: Project Scaffolding & Configuration

Create the project skeleton with `uv`, `pyproject.toml`, directory structure, and configuration models.

[NEW FILE] `pyproject.toml`
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ai-okf"
version = "0.1.0"
description = "OKF knowledge base agent — explore codebases and generate structured knowledge bundles"
requires-python = ">=3.12"
license = "MIT"
authors = [
    { name = "Developer", email = "dev@example.com" },
]
dependencies = [
    "typer>=0.9.0",
    "rich>=13.7.0",
    "pyyaml>=6.0",
    "pydantic-ai>=2.5.0",
    "gitpython>=3.1.0",
    "python-dotenv>=1.0.0",
    "httpx>=0.27.0",
]

[project.scripts]
okf = "ai_okf.cli:app"

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "black>=24.0.0",
    "mypy>=1.8.0",
    "ruff>=0.3.0",
]

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I"]

[tool.mypy]
strict = true

[tool.black]
line-length = 88
```

[NEW FILE] `.gitignore`
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
```

[NEW FILE] `src/ai_okf/__init__.py`
```python
"""AI-OKF: Knowledge base agent for codebase exploration."""
```

[NEW FILE] `src/ai_okf/config.py`
```python
import typer
from pathlib import Path

CLI_CONTEXT_SETTINGS: dict[str, object] = {
    "help_option_names": ["-h", "--help"],
}

DEFAULT_MODEL = "deepseek-v4-flash-free"
DEFAULT_API_BASE = "https://opencode.ai/zen/v1"
DEFAULT_OUTPUT = Path(".okf-bundle")
```

[NEW FILE] `src/ai_okf/models/__init__.py`
```python
"""Pydantic models for OKF concepts and scan results."""
```

[NEW FILE] `src/ai_okf/models/okf.py`
```python
from datetime import datetime
from pydantic import BaseModel, Field


class OKFFrontmatter(BaseModel):
    type: str
    title: str | None = None
    description: str | None = None
    resource: str | None = None
    tags: list[str] = []
    timestamp: datetime | None = None


class OKFConcept(BaseModel):
    concept_id: str
    frontmatter: OKFFrontmatter
    body: str


class OKFBundle(BaseModel):
    root_path: str
    concepts: dict[str, OKFConcept] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CodebaseFile(BaseModel):
    path: str
    language: str | None = None
    size_bytes: int = 0
    git_history_summary: str | None = None
```

[NEW FILE] `src/ai_okf/models/scan_result.py`
```python
from pydantic import BaseModel
from .okf import CodebaseFile


class ScanResult(BaseModel):
    files: list[CodebaseFile]
    git_changes_since: str | None = None
```

### Phase 2: Core Scanning Logic

Build the codebase scanner and git analyzer — deterministic parts that do NOT require an LLM.

[NEW FILE] `src/ai_okf/core/__init__.py`
```python
"""Core scanning and bundle management logic."""
```

[NEW FILE] `src/ai_okf/core/scanner.py`
```python
from pathlib import Path
from ai_okf.models.okf import CodebaseFile


LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".jsx": "JavaScript React",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".sql": "SQL",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
}

IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv",
    ".egg-info", "dist", "build", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".okf-bundle",
}

IGNORE_FILES = {".DS_Store"}


def scan_codebase(root: Path) -> list[CodebaseFile]:
    files: list[CodebaseFile] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        parts = rel.parts
        if any(p in IGNORE_DIRS for p in parts):
            continue
        suffix = path.suffix.lower()
        lang = LANGUAGE_MAP.get(suffix)
        files.append(CodebaseFile(
            path=str(rel),
            language=lang,
            size_bytes=path.stat().st_size,
        ))
    files.sort(key=lambda f: f.path)
    return files
```

[NEW FILE] `src/ai_okf/core/git_scanner.py`
```python
from pathlib import Path
from git import Repo, GitCommandError


def get_git_summary(path: Path) -> str:
    try:
        repo = Repo(path)
        if repo.bare or not repo.head.is_valid():
            return ""
        commits = list(repo.iter_commits(max_count=30))
        if not commits:
            return ""
        lines = [f"Branch: {repo.active_branch.name}"]
        lines.append(f"Total commits: {sum(1 for _ in repo.iter_commits())}")
        lines.append("Recent activity (last 10 commits):")
        for c in commits[:10]:
            date = c.committed_datetime.strftime("%Y-%m-%d")
            msg = c.message.split("\n")[0][:80]
            lines.append(f"  [{date}] {c.hexsha[:8]} {msg}")
        return "\n".join(lines)
    except (GitCommandError, Exception):
        return ""


def get_changes_since(path: Path, since_ref: str = "HEAD") -> str:
    try:
        repo = Repo(path)
        if repo.bare or not repo.head.is_valid():
            return ""
        diff = repo.git.diff(since_ref, "--stat")
        log = repo.git.log(since_ref, "--oneline", "--max-count=20")
        return f"Changes since {since_ref}:\n{diff}\n\nRecent commits:\n{log}"
    except (GitCommandError, Exception):
        return ""
```

[NEW FILE] `src/ai_okf/core/okf_bundle.py`
```python
from pathlib import Path
import yaml
from datetime import datetime
from ai_okf.models.okf import OKFConcept, OKFFrontmatter


def write_concept(output_dir: Path, concept: OKFConcept) -> Path:
    path = output_dir / f"{concept.concept_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = concept.frontmatter.model_dump(exclude_none=True)
    ts = concept.frontmatter.timestamp or datetime.now()
    frontmatter["timestamp"] = ts.isoformat()
    content = f"---\n{yaml.dump(frontmatter, sort_keys=False).strip()}\n---\n\n{concept.body.strip()}\n"
    path.write_text(content)
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
    (output_dir / "index.md").write_text("\n".join(lines).strip() + "\n")
```

### Phase 3: PydanticAI Agent with Capabilities

Build the LLM-powered agent using PydanticAI 2.0's capability composition pattern.

[NEW FILE] `src/ai_okf/agent/__init__.py`
```python
"""PydanticAI agent setup with composable capabilities."""
```

[NEW FILE] `src/ai_okf/agent/kb_agent.py`
```python
import os
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from ai_okf.config import DEFAULT_MODEL, DEFAULT_API_BASE


def build_agent(model_name: str | None = None, api_base: str | None = None) -> Agent:
    model_name = model_name or os.environ.get("OKF_MODEL", DEFAULT_MODEL)
    api_base = api_base or os.environ.get("OKF_API_BASE", DEFAULT_API_BASE)
    api_key = os.environ.get("OKF_API_KEY", "no-key-required")
    model = OpenAIModel(
        model_name,
        provider=OpenAIProvider(
            base_url=f"{api_base.rstrip('/')}/",
            api_key=api_key,
        ),
    )
    return Agent(model)
```

[NEW FILE] `src/ai_okf/agent/capabilities/__init__.py`
```python
"""Composable capabilities for the AI-OKF agent."""
```

[NEW FILE] `src/ai_okf/agent/capabilities/code_analysis.py`
```python
from pathlib import Path
from typing import Any
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import FunctionToolset


def read_file_content(path: str, root: str = ".") -> str:
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
            "Identify: modules/packages, classes, functions, data models, API endpoints, "
            "configuration, test patterns, dependencies. "
            "Use read_file to inspect relevant files before producing analysis."
        )

    def get_toolset(self):
        return FunctionToolset(tools=[read_file_content])
```

[NEW FILE] `src/ai_okf/agent/capabilities/okf_generation.py`
```python
from typing import Any
from pydantic_ai.capabilities import AbstractCapability


class OKFGenerationCapability(AbstractCapability[dict[str, Any]]):
    id: str = "okf-generation"
    description: str = (
        "Capability for generating OKF-formatted knowledge documents "
        "from codebase analysis."
    )
    defer_loading: bool = True

    def get_instructions(self) -> str:
        return (
            "You generate OKF (Open Knowledge Format) documents. "
            "Each document has YAML frontmatter with a REQUIRED 'type' field "
            "and optional: title, description, resource, tags, timestamp. "
            "The body is markdown with structural headings. "
            "Types include: Module, Class, Function, API Endpoint, Data Model, "
            "Configuration, CLI Command, Test Suite, Pattern. "
            "Output format: return raw markdown with frontmatter separated by ---."
        )
```

### Phase 4: CLI Commands

Implement the Typer CLI with `init` and `update` commands.

[NEW FILE] `src/ai_okf/cli.py`
```python
import typer
from ai_okf.config import CLI_CONTEXT_SETTINGS
from ai_okf.commands.init_cmd import init_command
from ai_okf.commands.update_cmd import update_command

app = typer.Typer(
    context_settings=CLI_CONTEXT_SETTINGS,
    no_args_is_help=True,
    name="okf",
    help="OKF Knowledge Base Agent — explore codebases and generate structured knowledge bundles.",
)

app.command(name="init")(init_command)
app.command(name="update")(update_command)
```

[NEW FILE] `src/ai_okf/commands/__init__.py`
```python
"""CLI command implementations."""
```

[NEW FILE] `src/ai_okf/commands/init_cmd.py`
```python
from pathlib import Path
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from ai_okf.core.scanner import scan_codebase
from ai_okf.core.git_scanner import get_git_summary
from ai_okf.core.okf_bundle import write_concept, write_index
from ai_okf.agent.kb_agent import build_agent
from ai_okf.models.okf import OKFConcept, OKFFrontmatter
from ai_okf.config import DEFAULT_OUTPUT

console = Console()


def init_command(
    path: str = typer.Argument(".", help="Path to the codebase to analyze"),
    output: str = typer.Option(
        str(DEFAULT_OUTPUT), "--output", "-o", help="Output directory for the OKF bundle"
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
        console.print(f"[red]Error:[/red] Path '{path}' does not exist or is not a directory.")
        raise typer.Exit(1)

    if output_dir.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] Output directory '{output}' already exists. "
            f"Use --force to overwrite."
        )
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Scanning codebase...", total=None)
        files = scan_codebase(root)

        progress.add_task(description="Analyzing git history...", total=None)
        git_summary = get_git_summary(root)

        progress.add_task(description="Building concepts...", total=None)
        agent = build_agent(model, api_base)

        concepts: list[OKFConcept] = []

        project_concept = OKFConcept(
            concept_id="project",
            frontmatter=OKFFrontmatter(
                type="Project",
                title=root.name,
                description=(
                    f"Automatically generated OKF knowledge bundle for {root.name}"
                ),
                tags=["codebase", "auto-generated"],
            ),
            body=(
                f"# Project: {root.name}\n\n"
                f"{git_summary or 'No git history available.'}\n\n"
                f"This bundle was auto-generated by AI-OKF.\n"
            ),
        )
        write_concept(output_dir, project_concept)
        concepts.append(project_concept)

        dirs_seen: set[str] = set()
        for f in files:
            parts = f.path.split("/")
            if len(parts) > 1:
                module_dir = parts[0]
                if module_dir not in dirs_seen:
                    dirs_seen.add(module_dir)
                    sub_files = [x for x in files if x.path.startswith(module_dir + "/")]
                    file_list = "\n".join(f"- `{x.path}`" for x in sub_files)
                    module_concept = OKFConcept(
                        concept_id=module_dir,
                        frontmatter=OKFFrontmatter(
                            type="Module",
                            title=module_dir,
                            description=f"Module directory: {module_dir}",
                        ),
                        body=f"# {module_dir}\n\nThis module contains:\n{file_list}",
                    )
                    write_concept(output_dir, module_concept)
                    concepts.append(module_concept)

        write_index(output_dir, concepts)

    console.print(f"[green]OKF bundle created at:[/green] {output_dir}")
```

[NEW FILE] `src/ai_okf/commands/update_cmd.py`
```python
from pathlib import Path
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from ai_okf.core.git_scanner import get_changes_since
from ai_okf.config import DEFAULT_OUTPUT

console = Console()


def update_command(
    path: str = typer.Argument(".", help="Path to the codebase to analyze"),
    output: str = typer.Option(
        str(DEFAULT_OUTPUT), "--output", "-o", help="Output directory for the OKF bundle"
    ),
    model: str = typer.Option(
        None, "--model", "-m", help="LLM model to use"
    ),
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
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Checking git changes...", total=None)
        changes = get_changes_since(root)

        progress.add_task(description="Analyzing incremental changes...", total=None)

        if changes:
            console.print(f"[dim]{changes[:500] if changes else 'No changes detected.'}[/dim]")
        else:
            console.print("[yellow]No changes detected since last update.[/yellow]")
```

### Phase 5: Tests

[NEW FILE] `tests/__init__.py`
```python
"""Tests for ai-okf."""
```

[NEW FILE] `tests/test_scanner.py`
```python
from pathlib import Path
from ai_okf.core.scanner import scan_codebase


def test_scan_codebase(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "src" / "utils.py").write_text("def helper(): pass")
    (tmp_path / "README.md").write_text("# Project")
    files = scan_codebase(tmp_path)
    paths = [f.path for f in files]
    assert "src/main.py" in paths
    assert "src/utils.py" in paths
    assert "README.md" in paths


def test_scan_ignores_git_dir(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]")
    (tmp_path / "main.py").write_text("x = 1")
    files = scan_codebase(tmp_path)
    assert all(".git" not in f.path for f in files)


def test_scan_ignores_venv(tmp_path: Path):
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("lib")
    (tmp_path / "main.py").write_text("x = 1")
    files = scan_codebase(tmp_path)
    assert all(".venv" not in f.path for f in files)
```

[NEW FILE] `tests/test_okf_bundle.py`
```python
from pathlib import Path
from datetime import datetime
from ai_okf.models.okf import OKFConcept, OKFFrontmatter
from ai_okf.core.okf_bundle import write_concept, concept_exists, write_index


def test_write_concept(tmp_path: Path):
    concept = OKFConcept(
        concept_id="test/concept",
        frontmatter=OKFFrontmatter(
            type="TestType",
            title="Test Concept",
            description="A test",
            tags=["test"],
            timestamp=datetime(2026, 1, 1, 0, 0, 0),
        ),
        body="# Test\n\nThis is a test concept.",
    )
    path = write_concept(tmp_path, concept)
    assert path.exists()
    content = path.read_text()
    assert "type: TestType" in content
    assert "title: Test Concept" in content
    assert "This is a test concept." in content


def test_concept_exists(tmp_path: Path):
    assert not concept_exists(tmp_path, "nonexistent")
    concept = OKFConcept(
        concept_id="exists",
        frontmatter=OKFFrontmatter(type="Test"),
        body="body",
    )
    write_concept(tmp_path, concept)
    assert concept_exists(tmp_path, "exists")


def test_write_index(tmp_path: Path):
    concepts = [
        OKFConcept(concept_id="a", frontmatter=OKFFrontmatter(type="Module", title="A"), body=""),
        OKFConcept(concept_id="b", frontmatter=OKFFrontmatter(type="Module", title="B"), body=""),
    ]
    write_index(tmp_path, concepts)
    index_path = tmp_path / "index.md"
    assert index_path.exists()
    content = index_path.read_text()
    assert "Modules" in content
    assert "[A](a.md)" in content
    assert "[B](b.md)" in content
```

[NEW FILE] `tests/test_git_scanner.py`
```python
from pathlib import Path
from ai_okf.core.git_scanner import get_git_summary, get_changes_since


def test_get_git_summary_empty_dir(tmp_path: Path):
    result = get_git_summary(tmp_path)
    assert result == ""


def test_get_changes_since_empty_dir(tmp_path: Path):
    result = get_changes_since(tmp_path)
    assert result == ""
```

### Phase 6: Documentation & Housekeeping

[NEW FILE] `README.md`
```markdown
# AI-OKF

OKF Knowledge Base Agent — automatically explores codebases and generates structured **OKF (Open Knowledge Format)** knowledge bundles.

## Quick Start

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Set your API endpoint (defaults to opencode.ai free tier)
export OKF_MODEL="deepseek-v4-flash-free"
export OKF_API_BASE="https://opencode.ai/zen/v1"

# Initialize a knowledge bundle from a codebase
okf init /path/to/project --output ./knowledge-base

# Update it after changes
okf update /path/to/project --output ./knowledge-base
```

## Usage

- `okf init [PATH]` — Full codebase scan, generates complete OKF bundle
- `okf update [PATH]` — Incremental update based on git changes
- `--model, -m` — Choose LLM model (default: deepseek-v4-flash-free)
- `--api-base` — Custom OpenAI-compatible API base URL
- `--output, -o` — Output directory (default: .okf-bundle)

## Output Format

The generated bundle follows [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md):
- Hierarchical markdown with YAML frontmatter
- `index.md` for each directory level
- Cross-linking between concepts
- Every concept has a REQUIRED `type` field
```

[MODIFY] `.gitignore` — add `.okf-bundle/` (included in Phase 1 above)

## Implementation Order

1. Phase 1: Scaffolding + config (pyproject.toml, .gitignore, package dirs, config.py, models)
2. Phase 2: Core logic (scanner.py, git_scanner.py, okf_bundle.py)
3. Phase 3: PydanticAI agent (kb_agent.py, capabilities/)
4. Phase 4: CLI commands (cli.py, init_cmd.py, update_cmd.py)
5. Phase 5: Tests (test_scanner.py, test_okf_bundle.py, test_git_scanner.py)
6. Phase 6: README.md

Each phase should be validated with `uv run pytest` before moving to the next.

## Testing Strategy

- Unit tests for scanner, git_scanner, okf_bundle (no LLM needed)
- Mock-based tests for agent commands
- Manual integration test: `okf init . --output /tmp/test-bundle`

## Verification

After implementation:
1. `uv run pytest` — all tests pass
2. `uv run black . && uv run ruff .` — linting clean
3. `uv run mypy src/` — type checking passes
4. `okf --help` — shows init and update commands
5. `okf init . --force` — generates OKF bundle without error
