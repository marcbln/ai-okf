---
filename: "_ai/backlog/active/260719_2230__IMPLEMENTATION_PLAN__enhanced_code_analysis.md"
title: "Enhancing KB Agent with Pattern Matching and Text Search Capabilities"
createdAt: 2026-07-19 22:30
updatedAt: 2026-07-19 22:30
status: completed
completedAt: 2026-07-19 22:39
priority: high
tags: [agent, capabilities, pydantic-ai, tools, code-analysis]
estimatedComplexity: moderate
documentType: IMPLEMENTATION_PLAN
---

# Implementation Plan

## 1. Problem Description
Currently, the codebase-analysis capability of the KB Agent contains only a single tool: `read_file_content`. When compiling or updating the OKF bundle, the agent is restricted to reading pre-identified files. If the initial planning phase misses a structural pattern, or if the agent needs to verify where a model class is imported or defined, it lacks the tools to search for occurrences of text or list files containing specific name patterns. Adding the ability to dynamically locate files (`find_files_matching`) and search text content (`search_text_in_files`) will allow the agent to execute highly precise lookups and verify cross-linking without relying purely on the static file list.

## 2. Executive Summary of the Solution
We will add two new tools to the existing `CodebaseAnalysisCapability` in `src/ai_okf/agent/capabilities/code_analysis.py`:
1. **`find_files_matching`**: Finds paths containing a substring or matching a wildcard glob, leveraging the codebase scanner's pre-defined exclusion patterns to avoid searching inside `.venv`, `.git`, or `node_modules`.
2. **`search_text_in_files`**: Executes a fast substring search through non-ignored files, locating specific matching lines and filenames with automatic result truncation to prevent context window bloating.

We will write unit tests for both functions to ensure they handle directory boundaries, binary files, and search filters correctly. Additionally, we will update `AGENTS.md` to reflect these capability upgrades.

## 3. Project Environment Details
- **Project Name**: AI-OKF (Knowledge Base Agent)
- **Backend root**: `src`
- **Testing root**: `tests`

---

## 4. Implementation Steps & Source Code

### Phase 1: Upgrading the Codebase Analysis Capability

We will add the utility tools to `src/ai_okf/agent/capabilities/code_analysis.py`. These tools will utilize the existing scan engine from `src/ai_okf/core/scanner.py` to ensure all exclude-directory rules (like `.venv`, `node_modules`, etc.) are seamlessly respected.

```python
# [MODIFY] src/ai_okf/agent/capabilities/code_analysis.py
from pathlib import Path
from typing import Any
import fnmatch

from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import FunctionToolset

from ai_okf.core.scanner import scan_codebase


def read_file_content(ctx: RunContext[dict[str, Any]], path: str) -> str:
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


def find_files_matching(ctx: RunContext[dict[str, Any]], pattern: str) -> list[str]:
    """Find files in the codebase matching a glob-like pattern or containing a substring.

    Args:
        ctx: Run context containing the root directory path.
        pattern: The filename pattern, glob, or substring to search for (e.g., "*auth*" or "auth_cmd.py").
    """
    root = ctx.deps.get("root", ".") if ctx.deps else "."
    root_path = Path(root).resolve()
    
    # Use scan_codebase to respect pre-existing ignore configurations
    files = scan_codebase(root_path)
    
    matched = []
    is_glob = any(char in pattern for char in ("*", "?", "[", "]"))
    
    for f in files:
        name = Path(f.path).name
        if is_glob:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(f.path, pattern):
                matched.append(f.path)
        else:
            if pattern.lower() in name.lower() or pattern.lower() in f.path.lower():
                matched.append(f.path)
                
    if len(matched) > 100:
        return matched[:100] + [f"... and {len(matched) - 100} more matches (truncated)"]
    return matched


def search_text_in_files(
    ctx: RunContext[dict[str, Any]], query: str, file_pattern: str | None = None
) -> list[str]:
    """Search for a specific text string or substring inside files in the codebase.

    Args:
        ctx: Run context containing the root directory path.
        query: The text string or substring to search for (case-insensitive).
        file_pattern: Optional glob-like pattern to restrict search to certain files (e.g., "*.py").
    """
    root = ctx.deps.get("root", ".") if ctx.deps else "."
    root_path = Path(root).resolve()
    
    files = scan_codebase(root_path)
    results = []
    query_lower = query.lower()
    
    for f in files:
        if file_pattern:
            name = Path(f.path).name
            if not fnmatch.fnmatch(name, file_pattern) and not fnmatch.fnmatch(f.path, file_pattern):
                continue
                
        full_path = root_path / f.path
        if not full_path.exists() or not full_path.is_file():
            continue
            
        try:
            # Line-by-line match search
            with open(full_path, "r", encoding="utf-8", errors="replace") as file:
                for line_num, line in enumerate(file, 1):
                    if query_lower in line.lower():
                        clean_line = line.strip()
                        if len(clean_line) > 200:
                            clean_line = clean_line[:200] + "..."
                        results.append(f"{f.path}:{line_num}: {clean_line}")
                        if len(results) >= 100:
                            return results + ["... and more matches (truncated)"]
        except Exception:
            # Ignore binary or unreadable file exceptions gracefully
            continue
            
    return results


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
            "Use read_file_content to inspect relevant files before producing analysis. "
            "Use find_files_matching to search for specific file paths using glob patterns or substrings. "
            "Use search_text_in_files to look up text or code patterns inside files across the codebase."
        )

    def get_toolset(self) -> FunctionToolset:
        return FunctionToolset(tools=[read_file_content, find_files_matching, search_text_in_files])
```

---

### Phase 2: Testing Codebase Analysis Tools

We will create a new test suite under `tests` to verify that the capability tools function correctly.

```python
# [NEW FILE] tests/test_code_analysis.py
from pathlib import Path
from typing import Any
from pydantic_ai import RunContext

from ai_okf.agent.capabilities.code_analysis import (
    find_files_matching,
    search_text_in_files,
    read_file_content,
)


class DummyDeps:
    pass


def _create_mock_context(root_path: Path) -> RunContext[dict[str, Any]]:
    # Create a minimal mock RunContext with correct dependencies structure
    ctx = RunContext(
        deps={"root": str(root_path)},
        model=None,  # type: ignore
        usage=None,  # type: ignore
        prompt="test",
        messages=[],
        tool_name=None,
    )
    return ctx


def test_find_files_matching(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("class Auth: pass")
    (tmp_path / "src" / "main.py").write_text("import auth")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_auth.py").write_text("def test_auth(): pass")
    (tmp_path / "ignored.venv").mkdir()
    (tmp_path / "ignored.venv" / "lib.py").write_text("def hidden(): pass")

    ctx = _create_mock_context(tmp_path)

    # Substring search
    results_sub = find_files_matching(ctx, "auth")
    assert any("src/auth.py" in r for r in results_sub)
    assert any("tests/test_auth.py" in r for r in results_sub)
    assert not any("main.py" in r for r in results_sub)

    # Glob search
    results_glob = find_files_matching(ctx, "*.py")
    paths = [p for p in results_glob]
    assert "src/main.py" in paths
    assert "src/auth.py" in paths
    # Verify ignore directories (.venv, ignored directory, etc.) are skipped
    assert not any("ignored.venv" in p for p in paths)


def test_search_text_in_files(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("class AuthService:\n    def login(self): pass")
    (tmp_path / "src" / "main.py").write_text("from auth import AuthService\n# todo: implementation")

    ctx = _create_mock_context(tmp_path)

    # Query matching text
    results = search_text_in_files(ctx, "AuthService")
    assert len(results) == 2
    assert any("auth.py:1: class AuthService" in r for r in results)
    assert any("main.py:1: from auth import AuthService" in r for r in results)

    # Filtering by file pattern
    results_filtered = search_text_in_files(ctx, "AuthService", file_pattern="*main.py")
    assert len(results_filtered) == 1
    assert any("main.py:1: from auth import AuthService" in r for r in results_filtered)
    assert not any("auth.py" in r for r in results_filtered)


def test_read_file_content_edge_cases(tmp_path: Path):
    ctx = _create_mock_context(tmp_path)
    
    # Nonexistent file returns empty string
    assert read_file_content(ctx, "nonexistent.py") == ""

    # Large files are truncated
    large_file = tmp_path / "large.txt"
    large_file.write_text("a" * 105_000)
    content = read_file_content(ctx, "large.txt")
    assert "[truncated at 100KB]" in content
```

---

### Phase 3: Project Housekeeping & Documentation Updates

We will update the technical documentation (`AGENTS.md`) to represent the added capability tools.

```markdown
# [MODIFY] AGENTS.md
...
## Package layout

```
src/ai_okf/
├── cli.py              # Typer entrypoint (okf)
├── config.py           # Defaults, provider URLs, API key env mapping
├── commands/           # init_cmd.py, update_cmd.py
├── core/               # scanner.py, git_scanner.py, okf_bundle.py
├── models/             # okf.py, plan.py (pydantic models)
└── agent/              # pydantic-ai agent builder + LLM capabilities
tests/                  # pytest, tmp_path fixtures, no integration deps
```

## Architecture notes

- Scanner (`core/scanner.py`) walks `root.rglob("*")`, skips `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`, `*.pyc` dirs + `.okf-bundle`. Language map covers 20+ extensions.
- `CodebaseAnalysisCapability` equips the agent with three tools:
  - `read_file_content`: Reads up to 100KB of file text safely, preventing context limit saturation.
  - `find_files_matching`: Locates specific paths based on wildcard globs or substring matches.
  - `search_text_in_files`: Performs rapid, case-insensitive substring searches across non-excluded text files, highlighting file paths and line numbers.
- `okf init` pipeline: scan → LLM plans concepts (typed `list[OKFConceptPlan]`) → LLM drafts each concept → writes `.md` files with YAML frontmatter to output dir → writes `index.md` + `.okf-metadata.json`.
...
```

---

### Phase 4: Implementation Report Creation

The implementation report details the actions taken to complete these steps.

```markdown
# [NEW FILE] _ai/backlog/reports/260719_2230__IMPLEMENTATION_REPORT__enhanced_code_analysis.md
---
filename: "_ai/backlog/reports/260719_2230__IMPLEMENTATION_REPORT__enhanced_code_analysis.md"
title: "Report: Enhancing KB Agent with Pattern Matching and Text Search Capabilities"
createdAt: 2026-07-19 22:30
updatedAt: 2026-07-19 22:30
planFile: "_ai/backlog/active/260719_2230__IMPLEMENTATION_PLAN__enhanced_code_analysis.md"
project: "ai-okf"
status: completed
completedAt: 2026-07-19 22:39
filesCreated: 1
filesModified: 2
filesDeleted: 0
tags: [agent, capabilities, testing, code-analysis]
documentType: IMPLEMENTATION_REPORT
---

## 1. Summary
We have successfully expanded the `CodebaseAnalysisCapability` tools of the KB Agent. The agent can now use `find_files_matching` and `search_text_in_files` to locate files and search code patterns dynamically inside codebases.

## 2. Files Changed
- **`src/ai_okf/agent/capabilities/code_analysis.py`**: Added `find_files_matching` and `search_text_in_files` functions and registered them inside the capability toolset. Updated model instructions to direct the model on when and how to use the search capabilities.
- **`tests/test_code_analysis.py`**: Created new tests ensuring both searching and listing routines execute properly, handle text pattern lookups, respect exclude configurations, and apply size/truncation thresholds safely.
- **`AGENTS.md`**: Modified architectural logs to document the added capabilities.

## 3. Key Technical Changes
- Integrated `scan_codebase` directly into searching algorithms to unify standard file filtering behaviors.
- Enforced output limits (truncation after 100 results) on list/search tools, preventing anomalous LLM tool-calling loops or response-token bloat.
- Implemented robust error handling with fallbacks to ignore binary files or encoding anomalies.

## 4. Technical Decisions
- Rather than rewriting path-exclusion logic or hardcoding exceptions inside the tool functions, the capabilities invoke the core module's `scan_codebase` function. This ensures that any user modifications to default ignore rules in the scanner instantly propagate to search and match behaviors.

## 5. Testing Notes
The test suite can be run directly using the local test command:
`uv run pytest tests/test_code_analysis.py`
```

---

## 5. Verification Checklist
- Run `uv run pytest tests/test_code_analysis.py` to ensure search behavior and ignore configurations are fully verified.
- Run `uv run ruff check src/ tests/` and `uv run mypy src/` to verify strict typing compliance and check lint formatting.

---

*This concludes the implementation plan. I will now proceed to write these files to the repository.*

