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


def read_concepts(output_dir: Path) -> list[OKFConcept]:
    concepts: list[OKFConcept] = []
    for path in sorted(output_dir.glob("*.md")):
        if path.name == "index.md":
            continue
        concepts.append(parse_okf_markdown(path.stem, path.read_text(encoding="utf-8")))
    return concepts


def _pluralize(type_name: str) -> str:
    name = type_name.strip() or "Concept"
    words = name.split()
    last = words[-1]
    lower = last.lower()
    if lower.endswith(("s", "sh", "ch", "x", "z")):
        plural = last + "es"
    elif lower.endswith("y") and len(last) > 1 and last[-2].lower() not in "aeiou":
        plural = last[:-1] + "ies"
    else:
        plural = last + "s"
    words[-1] = plural
    return " ".join(word[:1].upper() + word[1:] for word in words)


def write_index(output_dir: Path, concepts: list[OKFConcept]) -> None:
    lines: list[str] = []
    by_type: dict[str, list[OKFConcept]] = {}
    for c in concepts:
        by_type.setdefault(c.frontmatter.type, []).append(c)
    for type_name, items in sorted(by_type.items()):
        lines.append(f"# {_pluralize(type_name)}\n")
        for c in items:
            desc = c.frontmatter.description or ""
            title = c.frontmatter.title or c.concept_id
            lines.append(f"* [{title}]({c.concept_id}.md) - {desc}")
        lines.append("")
    index_path = output_dir / "index.md"
    index_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def parse_okf_markdown(concept_id: str, markdown_text: str) -> OKFConcept:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", markdown_text.strip(), re.DOTALL)
    if not match:
        return OKFConcept(
            concept_id=concept_id,
            frontmatter=OKFFrontmatter(type="Concept", title=concept_id),
            body=markdown_text,
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
        body=body.strip(),
    )


def save_bundle_metadata(output_dir: Path, data: dict[str, Any]) -> None:
    path = output_dir / METADATA_FILE
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_bundle_metadata(output_dir: Path) -> dict[str, Any]:
    file_path = output_dir / METADATA_FILE
    if not file_path.exists():
        return {}
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}
