from pydantic import BaseModel, Field


class OKFConceptPlan(BaseModel):
    concept_id: str = Field(
        description=(
            "Unique, lowercase, kebab-case identifier for the concept "
            "(e.g. core-auth)."
        )
    )
    type: str = Field(
        description=(
            "OKF type (Module, Class, API Endpoint, Data Model, "
            "Configuration, Pattern, etc.)"
        )
    )
    title: str = Field(description="Clear title of the concept.")
    description: str = Field(
        description="Brief summary of what this concept encapsulates."
    )
    files_to_read: list[str] = Field(
        description=(
            "Relative paths to files the LLM should read to generate this " "concept."
        )
    )
