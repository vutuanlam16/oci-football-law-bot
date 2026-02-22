from pydantic import BaseModel, Field

class ChatIn(BaseModel):
    message: str = Field(..., description="User question (Vietnamese supported)")
    top_k: int | None = Field(None, description="Override retrieval top_k")
    doc_type: str | None = Field(None, description="Optional filter: laws|discipline|competition|other")

class ChatCompareIn(BaseModel):
    message: str = Field(..., description="User question (Vietnamese supported)")
    models: list[str] = Field(..., description="List of model names to compare")
    top_k: int | None = Field(None, description="Override retrieval top_k")
    doc_type: str | None = Field(None, description="Optional filter: laws|discipline|competition|other")

class SearchIn(BaseModel):
    query: str
    top_k: int | None = None
    doc_type: str | None = None

class Citation(BaseModel):
    source_id: str
    quote: str
    doc_title: str
    section_label: str
    pages: str
    url: str | None = None

class ChatAnswer(BaseModel):
    answer: str
    related_provisions: list[str]
    citations: list[Citation]
    followup_questions: list[str] = []
    confidence: float = 0.0

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
