from typing import Any

from pydantic_ai.capabilities import AbstractCapability


class OKFGenerationCapability(AbstractCapability[dict[str, Any]]):
    id: str = "okf-generation"
    description: str = (
        "Capability for generating OKF-formatted knowledge documents "
        "from codebase analysis."
    )
    defer_loading: bool = True

    def get_instructions(self) -> str:
        return (
            "You generate OKF (Open Knowledge Format) documents. "
            "Each document has YAML frontmatter with a REQUIRED 'type' field "
            "and optional: title, description, resource, tags, timestamp. "
            "The body is markdown with structural headings. "
            "Types include: Module, Class, Function, API Endpoint, Data Model, "
            "Configuration, CLI Command, Test Suite, Pattern. "
            "Output format: return raw markdown with frontmatter separated by ---."
        )
