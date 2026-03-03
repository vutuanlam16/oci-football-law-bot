from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings
from app.db import SessionLocal
from app.models import EMBED_DIM, Document, Chunk
from app.schemas import (
    ChatIn, ChatCompareIn, ChatCompareItem, SearchIn, ChatAnswer, SearchHit,
    VersionInfo, VersionConflictDetail, ArchiveVersionIn, CreateVersionIn,
    VersionStatistics, ResolveConflictsIn
)
from app.rag.retrieve import retrieve
from app.rag.answer import answer_question
from app.rag.versioning import VersioningService, VersionConflict

app = FastAPI(title="Football Law Bot (OCI Full Stack)")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def _startup_checks():
    if settings.embed_dim != EMBED_DIM:
        raise RuntimeError(
            f"EMBED_DIM env ({settings.embed_dim}) must match DB/model EMBED_DIM ({EMBED_DIM}). "
            "Update .env and rebuild/migrate consistently."
        )

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/data")
def data_ui():
    return FileResponse(STATIC_DIR / "data.html")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/search", response_model=list[SearchHit])
def search(payload: SearchIn):
    db = SessionLocal()
    hits = retrieve(
        db,
        payload.query,
        top_k=payload.top_k or settings.top_k,
        doc_type=payload.doc_type,
        active_only=payload.active_only,
        effective_on=payload.effective_on,
    )
    out: list[SearchHit] = []
    for i, h in enumerate(hits, start=1):
        pages = f"tr. {h['page_start']}-{h['page_end']}" if h["page_start"] != h["page_end"] else f"tr. {h['page_start']}"
        version_str = f"{h.get('version_major', 1)}.{h.get('version_minor', 0)}"
        out.append(SearchHit(
            source_id=f"S{i}",
            doc_title=h["doc_title"],
            section_label=h["section_label"],
            section_type=h["section_type"],
            pages=pages,
            url=h.get("source_url"),
            text=h["text"],
            score=float(h.get("distance")) if h.get("distance") is not None else None,
            version=version_str,
            is_active=h.get("is_active", True),
        ))
    return out

@app.post("/chat", response_model=ChatAnswer)
def chat(payload: ChatIn):
    db = SessionLocal()
    
    # Check for version conflicts if searching across all versions
    version_warning = None
    if not payload.active_only:
        vs = VersioningService(db)
        conflicts = vs.detect_conflicts(
            doc_type=payload.doc_type,
            effective_on=payload.effective_on
        )
        if conflicts:
            version_warning = (
                f"⚠️ Phát hiện {len(conflicts)} xung đột phiên bản. "
                f"Kết quả có thể chứa nhiều phiên bản khác nhau của cùng một luật."
            )
    
    hits = retrieve(
        db,
        payload.message,
        top_k=payload.top_k or settings.top_k,
        doc_type=payload.doc_type,
        active_only=payload.active_only,
        effective_on=payload.effective_on,
    )
    if not hits:
        raise HTTPException(status_code=404, detail="No sources found in knowledge base")
    
    result = answer_question(payload.message, hits)
    
    # Add version info to citations
    for citation in result.citations:
        # Try to find version from hits
        for h in hits:
            if h["doc_title"] in citation.doc_title:
                citation.version = f"{h.get('version_major', 1)}.{h.get('version_minor', 0)}"
                break
    
    if version_warning:
        result.version_warning = version_warning
    
    return result

@app.post("/chat/compare", response_model=list[ChatCompareItem])
def chat_compare(payload: ChatCompareIn):
    db = SessionLocal()
    hits = retrieve(
        db,
        payload.message,
        top_k=payload.top_k or settings.top_k,
        doc_type=payload.doc_type,
    )
    if not hits:
        raise HTTPException(status_code=404, detail="No sources found in knowledge base")
    results: list[ChatCompareItem] = []
    for model in payload.models:
        result = answer_question(payload.message, hits, model=model)
        results.append(ChatCompareItem(model=model, result=result))
    return results

@app.get("/api/documents")
def list_documents(
    limit: int = Query(50, ge=1, le=200), 
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True, description="Only show active versions")
):
    db = SessionLocal()
    q = db.query(Document).order_by(Document.id.desc())
    
    if active_only:
        q = q.filter(Document.is_active == True)
    
    rows = q.offset(offset).limit(limit).all()
    return [
        {
            "id": d.id,
            "doc_id": d.doc_id,
            "title": d.title,
            "version": f"{d.version_major}.{d.version_minor}",
            "version_date": d.version_date,
            "is_active": d.is_active,
            "effective_date": d.effective_date.isoformat() if d.effective_date else None,
            "archived_at": d.archived_at.isoformat() if d.archived_at else None,
            "source_url": d.source_url,
            "doc_type": d.doc_type,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in rows
    ]

@app.get("/api/chunks")
def list_chunks(
    document_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    db = SessionLocal()
    q = db.query(Chunk).order_by(Chunk.id.desc())
    if document_id is not None:
        q = q.filter(Chunk.document_id == document_id)
    rows = q.offset(offset).limit(limit).all()
    return [
        {
            "id": c.id,
            "document_id": c.document_id,
            "section_label": c.section_label,
            "section_type": c.section_type,
            "page_start": c.page_start,
            "page_end": c.page_end,
            "text": c.text,
        }
        for c in rows
    ]


# ========== Version Management Endpoints ==========

@app.get("/api/versions/history/{doc_id}", response_model=list[VersionInfo])
def get_version_history(doc_id: str):
    """Get all versions of a document."""
    db = SessionLocal()
    vs = VersioningService(db)
    docs = vs.get_version_history(doc_id)
    
    return [
        VersionInfo(
            doc_id=d.doc_id,
            title=d.title,
            version_major=d.version_major,
            version_minor=d.version_minor,
            version_string=f"{d.version_major}.{d.version_minor}",
            is_active=d.is_active,
            effective_date=d.effective_date,
            archived_at=d.archived_at,
            superseded_by_id=d.superseded_by_id,
            created_at=d.created_at,
        )
        for d in docs
    ]


@app.get("/api/versions/conflicts", response_model=list[VersionConflictDetail])
def detect_version_conflicts(
    doc_type: str | None = Query(None, description="Filter by document type")
):
    """Detect version conflicts (multiple active versions of same document)."""
    db = SessionLocal()
    vs = VersioningService(db)
    conflicts = vs.detect_conflicts(doc_type=doc_type)
    
    return [
        VersionConflictDetail(**c)
        for c in conflicts
    ]


@app.get("/api/versions/stats", response_model=VersionStatistics)
def get_version_statistics():
    """Get version control statistics."""
    db = SessionLocal()
    vs = VersioningService(db)
    stats = vs.get_statistics()
    
    return VersionStatistics(
        total_documents=stats["total_documents"],
        active_documents=stats["active_documents"],
        archived_documents=stats["archived_documents"],
        conflicts_detected=stats["conflicts_detected"],
        conflict_details=[VersionConflictDetail(**c) for c in stats["conflict_details"]]
    )


@app.post("/api/versions/archive")
def archive_document_version(payload: ArchiveVersionIn):
    """Archive a specific version."""
    db = SessionLocal()
    vs = VersioningService(db)
    
    try:
        doc = vs.archive_version(
            doc_id=payload.doc_id,
            superseded_by_doc_id=payload.superseded_by_doc_id
        )
        return {
            "success": True,
            "message": f"Archived {doc.doc_id}",
            "doc_id": doc.doc_id,
            "archived_at": doc.archived_at.isoformat() if doc.archived_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/versions/create")
def create_document_version(payload: CreateVersionIn):
    """Create a new version of an existing document."""
    db = SessionLocal()
    vs = VersioningService(db)
    
    try:
        new_doc, archived_doc = vs.create_new_version(
            base_doc_id=payload.base_doc_id,
            new_major=payload.new_major,
            new_minor=payload.new_minor,
            archive_old=payload.archive_old,
            effective_date=payload.effective_date,
        )
        
        return {
            "success": True,
            "message": f"Created new version {new_doc.doc_id}",
            "new_version": {
                "doc_id": new_doc.doc_id,
                "version": f"{new_doc.version_major}.{new_doc.version_minor}",
                "effective_date": new_doc.effective_date.isoformat() if new_doc.effective_date else None,
            },
            "archived_old": archived_doc is not None,
            "old_version": {
                "doc_id": archived_doc.doc_id,
                "archived_at": archived_doc.archived_at.isoformat() if archived_doc.archived_at else None,
            } if archived_doc else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/versions/resolve")
def resolve_conflicts_auto(payload: ResolveConflictsIn):
    """Auto-resolve version conflicts using specified strategy."""
    db = SessionLocal()
    vs = VersioningService(db)
    
    try:
        archived = vs.resolve_conflicts_auto(
            doc_type=payload.doc_type,
            strategy=payload.strategy
        )
        
        return {
            "success": True,
            "message": f"Resolved conflicts using strategy '{payload.strategy}'",
            "conflicts_resolved": len(archived),
            "archived_versions": archived,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
