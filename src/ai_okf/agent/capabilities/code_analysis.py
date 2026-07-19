import fnmatch
from pathlib import Path
from typing import Any

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
    root = ctx.deps.get("root", ".") if ctx.deps else "."
    root_path = Path(root).resolve()

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
        extra = len(matched) - 100
        return matched[:100] + [f"... and {extra} more matches (truncated)"]
    return matched


def search_text_in_files(
    ctx: RunContext[dict[str, Any]], query: str, file_pattern: str | None = None
) -> list[str]:
    root = ctx.deps.get("root", ".") if ctx.deps else "."
    root_path = Path(root).resolve()

    files = scan_codebase(root_path)
    results = []
    query_lower = query.lower()

    for f in files:
        if file_pattern:
            name = Path(f.path).name
            if not fnmatch.fnmatch(name, file_pattern):
                if not fnmatch.fnmatch(f.path, file_pattern):
                    continue

        full_path = root_path / f.path
        if not full_path.exists() or not full_path.is_file():
            continue

        try:
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
            "Use read_file_content to inspect relevant files before analysis. "
            "Use find_files_matching to search for specific file paths using "
            "glob patterns or substrings. "
            "Use search_text_in_files to look up text or code patterns "
            "inside files across the codebase."
        )

    def get_toolset(self) -> FunctionToolset:
        return FunctionToolset(
            tools=[
                read_file_content,
                find_files_matching,
                search_text_in_files,
            ]
        )
