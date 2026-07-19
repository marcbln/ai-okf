from datetime import datetime

from pydantic import BaseModel, Field


class OKFFrontmatter(BaseModel):
    type: str
    title: str | None = None
    description: str | None = None
    resource: str | None = None
    tags: list[str] = []
    timestamp: datetime | None = None


class OKFConcept(BaseModel):
    concept_id: str
    frontmatter: OKFFrontmatter
    body: str


class OKFBundle(BaseModel):
    root_path: str
    concepts: dict[str, OKFConcept] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class CodebaseFile(BaseModel):
    path: str
    language: str | None = None
    size_bytes: int = 0
    git_history_summary: str | None = None
