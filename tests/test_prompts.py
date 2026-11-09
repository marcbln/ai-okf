from ai_okf.models.plan import OKFConceptPlan
from ai_okf.prompts import build_concept_prompt, build_plan_prompt, build_update_prompt


def test_notes_plan_prompt_is_topic_oriented() -> None:
    prompt = build_plan_prompt("notes", "- `a.md` (Markdown)")
    assert "projects" in prompt
    assert "open questions" in prompt
    assert "modules" not in prompt


def test_code_plan_prompt_is_code_oriented() -> None:
    prompt = build_plan_prompt("code", "- `a.py` (Python)")
    assert "modules" in prompt


def test_notes_concept_prompt_grounds_facts() -> None:
    plan = OKFConceptPlan(
        concept_id="t2",
        type="Project",
        title="T2",
        description="T2 project",
        files_to_read=["a.md"],
    )
    prompt = build_concept_prompt("notes", plan)
    assert "Use only facts present in the notes" in prompt
    assert "Do not invent" in prompt
    assert "frontmatter" in prompt


def test_notes_update_prompt_flags_contradictions() -> None:
    prompt = build_update_prompt("notes", "M a.md", "wiki")
    assert "contradicts" in prompt
