from datetime import datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from ai_okf.models.okf import OKFConcept


def write_concept(output_dir: Path, concept: OKFConcept) -> Path:
    path = output_dir / f"{concept.concept_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = concept.frontmatter.model_dump(exclude_none=True)
    ts = concept.frontmatter.timestamp or datetime.now()
    frontmatter["timestamp"] = ts.isoformat()
    fm = yaml.dump(frontmatter, sort_keys=False).strip()
    content = f"---\n{fm}\n---\n\n{concept.body.strip()}\n"
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
