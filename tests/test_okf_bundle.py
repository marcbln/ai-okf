from datetime import datetime
from pathlib import Path

from ai_okf.core.okf_bundle import (
    _pluralize,
    concept_exists,
    read_concepts,
    write_concept,
    write_index,
)
from ai_okf.models.okf import OKFConcept, OKFFrontmatter


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
        OKFConcept(
            concept_id="a",
            frontmatter=OKFFrontmatter(type="Module", title="A"),
            body="",
        ),
        OKFConcept(
            concept_id="b",
            frontmatter=OKFFrontmatter(type="Module", title="B"),
            body="",
        ),
    ]
    write_index(tmp_path, concepts)
    index_path = tmp_path / "index.md"
    assert index_path.exists()
    content = index_path.read_text()
    assert "Modules" in content
    assert "[A](a.md)" in content
    assert "[B](b.md)" in content


def test_read_concepts_skips_index(tmp_path: Path):
    write_concept(
        tmp_path,
        OKFConcept(
            concept_id="a",
            frontmatter=OKFFrontmatter(type="Project", title="A"),
            body="body",
        ),
    )
    (tmp_path / "index.md").write_text("# Index\n")
    concepts = read_concepts(tmp_path)
    assert [c.concept_id for c in concepts] == ["a"]


def test_pluralize() -> None:
    assert _pluralize("process") == "Processes"
    assert _pluralize("decision") == "Decisions"
    assert _pluralize("project") == "Projects"
    assert _pluralize("category") == "Categories"
