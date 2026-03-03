from pydantic import BaseModel, Field
from datetime import date, datetime

class ChatIn(BaseModel):
    message: str = Field(..., description="User question (Vietnamese supported)")
    top_k: int | None = Field(None, description="Override retrieval top_k")
    doc_type: str | None = Field(None, description="Optional filter: laws|discipline|competition|other")
    active_only: bool = Field(True, description="Only search in active (non-archived) versions")
    effective_on: date | None = Field(None, description="Filter by effective date (for historical queries)")

class ChatCompareIn(BaseModel):
    message: str = Field(..., description="User question (Vietnamese supported)")
    models: list[str] = Field(..., description="List of model names to compare")
    top_k: int | None = Field(None, description="Override retrieval top_k")
    doc_type: str | None = Field(None, description="Optional filter: laws|discipline|competition|other")

class SearchIn(BaseModel):
    query: str
    top_k: int | None = None
    doc_type: str | None = None
    active_only: bool = True
    effective_on: date | None = None

class Citation(BaseModel):
    source_id: str
    quote: str
    doc_title: str
    section_label: str
    pages: str
    url: str | None = None
    version: str | None = None  # e.g., "2024.1"

class ChatAnswer(BaseModel):
    answer: str
    related_provisions: list[str]
    citations: list[Citation]
    followup_questions: list[str] = []
    confidence: float = 0.0
    version_warning: str | None = None  # Warning if multiple versions detected

class ChatCompareItem(BaseModel):
    model: str
    result: ChatAnswer

class SearchHit(BaseModel):
    source_id: str
    doc_title: str
    section_label: str
    section_type: str
    pages: str
    url: str | None = None
    text: str
    score: float | None = None  # smaller distance is better if using cosine distance
    version: str | None = None
    is_active: bool = True

# Version management schemas

class VersionInfo(BaseModel):
    """Version information for a document."""
    doc_id: str
    title: str
    version_major: int
    version_minor: int
    version_string: str  # e.g., "2024.1"
    is_active: bool
    effective_date: date | None = None
    archived_at: datetime | None = None
    superseded_by_id: int | None = None
    created_at: datetime

class VersionConflictDetail(BaseModel):
    """Details of a version conflict."""
    base_doc: str
    title_pattern: str
    doc_type: str | None
    conflict_count: int
    versions: list[dict]

class ArchiveVersionIn(BaseModel):
    """Request to archive a version."""
    doc_id: str
    superseded_by_doc_id: str | None = None

class CreateVersionIn(BaseModel):
    """Request to create a new version."""
    base_doc_id: str
    new_major: int
    new_minor: int = 0
    archive_old: bool = True
    effective_date: date | None = None

class VersionStatistics(BaseModel):
    """Version control statistics."""
    total_documents: int
    active_documents: int
    archived_documents: int
    conflicts_detected: int
    conflict_details: list[VersionConflictDetail]

class ResolveConflictsIn(BaseModel):
    """Request to auto-resolve conflicts."""
    doc_type: str | None = None
    strategy: str = Field("keep_latest", description="Strategy: keep_latest | keep_effective")

