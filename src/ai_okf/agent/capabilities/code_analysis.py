from pathlib import Path
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import FunctionToolset


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
