from pydantic import BaseModel

from .okf import CodebaseFile


class ScanResult(BaseModel):
    files: list[CodebaseFile]
    git_changes_since: str | None = None
