from pathlib import Path

from ai_okf.config import (
    EXTRA_TEXT_EXTENSIONS,
    KNOWN_TEXT_NAMES,
    MAX_FILE_BYTES,
    is_protected_path,
)
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
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    ".egg-info",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".okf-bundle",
}

IGNORE_FILES = {".DS_Store"}


def _is_text_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in LANGUAGE_MAP or suffix in EXTRA_TEXT_EXTENSIONS:
        return True
    return path.name in KNOWN_TEXT_NAMES


def scan_codebase(
    root: Path,
    exclude_dirs: set[Path] | None = None,
) -> list[CodebaseFile]:
    excluded = exclude_dirs or set()
    files: list[CodebaseFile] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        parts = rel.parts
        if any(p in IGNORE_DIRS for p in parts):
            continue
        if rel.name in IGNORE_FILES:
            continue
        full = root / rel
        if any(full == ex or ex in full.parents for ex in excluded):
            continue
        if is_protected_path(str(rel)):
            continue
        if not _is_text_file(path):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_BYTES:
            continue
        files.append(
            CodebaseFile(
                path=str(rel),
                language=LANGUAGE_MAP.get(path.suffix.lower()),
                size_bytes=size,
            )
        )
    files.sort(key=lambda f: f.path)
    return files
