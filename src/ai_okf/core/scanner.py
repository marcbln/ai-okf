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
        files.append(
            CodebaseFile(
                path=str(rel),
                language=lang,
                size_bytes=path.stat().st_size,
            )
        )
    files.sort(key=lambda f: f.path)
    return files
