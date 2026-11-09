from pathlib import Path

from ai_okf.commands.init_cmd import (
    MAX_CONCEPTS,
    _fallback_plans,
    _load_sources,
    _normalize_plans,
    _parse_json_array,
    _plans_from_data,
    _slugify,
    _strip_code_fence,
)
from ai_okf.models.okf import CodebaseFile
from ai_okf.models.plan import OKFConceptPlan


def _plan(concept_id: str, title: str = "T") -> OKFConceptPlan:
    return OKFConceptPlan(
        concept_id=concept_id,
        type="Project",
        title=title,
        description="d",
        files_to_read=["a.md"],
    )


def test_slugify() -> None:
    assert _slugify("T2 Migration!") == "t2-migration"
    assert _slugify("1") == "1"


def test_normalize_replaces_numeric_ids() -> None:
    plans = _normalize_plans([_plan("1"), _plan("2"), _plan("T2 Migration")])
    assert [p.concept_id for p in plans] == ["concept-1", "concept-2", "t2-migration"]


def test_normalize_dedupes_and_caps() -> None:
    plans = [_plan(f"Topic {i}") for i in range(MAX_CONCEPTS + 3)]
    plans.append(_plan("Topic 0"))
    result = _normalize_plans(plans)
    assert len(result) == MAX_CONCEPTS
    assert len({p.concept_id for p in result}) == MAX_CONCEPTS


def test_strip_code_fence() -> None:
    fenced = "```markdown\n# Title\n\nBody\n```"
    assert _strip_code_fence(fenced) == "# Title\n\nBody"
    assert _strip_code_fence("plain") == "plain"


def test_load_sources_reads_and_skips_protected(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("alpha content")
    (tmp_path / ".secrets.md").write_text("secret content")
    out = _load_sources(tmp_path, ["a.md", ".secrets.md", "missing.md"])
    assert "### a.md" in out
    assert "alpha content" in out
    assert "secret content" not in out


def test_parse_json_array_tolerates_trailing_prose() -> None:
    text = (
        '[{"concept_id": "t2", "type": "Project", "title": "T2", '
        '"description": "d", "files_to_read": ["a.md"]}]\n\nHere is why I chose this.'
    )
    data = _parse_json_array(text)
    assert len(data) == 1
    assert data[0]["concept_id"] == "t2"


def test_parse_json_array_from_fence() -> None:
    text = '```json\n[{"concept_id": "a"}]\n```\ntrailing'
    assert _parse_json_array(text) == [{"concept_id": "a"}]


def test_plans_from_data_ignores_non_dict() -> None:
    data = [
        "t2",
        {
            "concept_id": "ok",
            "type": "Project",
            "title": "OK",
            "description": "",
            "files_to_read": [],
        },
    ]
    plans = _plans_from_data(data)
    assert [p.concept_id for p in plans] == ["ok"]


def test_fallback_plans_groups_by_folder() -> None:
    files = [
        CodebaseFile(path="projects/t2/a.md"),
        CodebaseFile(path="projects/t2/b.md"),
        CodebaseFile(path="README.md"),
    ]
    plans = {p.concept_id: p for p in _fallback_plans(files)}
    assert plans["projects"].files_to_read == [
        "projects/t2/a.md",
        "projects/t2/b.md",
    ]
    assert plans["root"].files_to_read == ["README.md"]
