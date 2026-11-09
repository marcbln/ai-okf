from typing import Any

from pydantic_ai.capabilities import AbstractCapability

CODE_TYPES = (
    "Module, Class, Function, API Endpoint, Data Model, Configuration, "
    "CLI Command, Test Suite, Pattern"
)
NOTES_TYPES = (
    "Project, Decision, Person, Organisation, Theme, Open Question, "
    "Reference, Concept"
)


class OKFGenerationCapability(AbstractCapability[dict[str, Any]]):
    id: str = "okf-generation"
    description: str = (
        "Capability for generating OKF-formatted knowledge documents "
        "from project analysis."
    )
    defer_loading: bool = True

    def get_instructions(self) -> str:
        return self._instructions(CODE_TYPES)

    def _instructions(self, types: str) -> str:
        return (
            "You generate OKF (Open Knowledge Format) documents. "
            "Each document has YAML frontmatter with a REQUIRED 'type' field "
            "and optional: title, description, resource, tags, timestamp. "
            "The body is markdown with structural headings. "
            f"Types include: {types}. "
            "Output format: return raw markdown with frontmatter separated by ---."
        )


class NotesOKFGenerationCapability(OKFGenerationCapability):
    id: str = "notes-okf-generation"

    def get_instructions(self) -> str:
        return self._instructions(NOTES_TYPES)
