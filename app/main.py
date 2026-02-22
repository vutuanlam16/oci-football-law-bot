from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import settings
from app.db import SessionLocal
from app.models import EMBED_DIM, Document, Chunk
from app.schemas import ChatIn, ChatCompareIn, ChatCompareItem, SearchIn, ChatAnswer, SearchHit
from app.rag.retrieve import retrieve
from app.rag.answer import answer_question

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
    )
    out: list[SearchHit] = []
    for i, h in enumerate(hits, start=1):
        pages = f"tr. {h['page_start']}-{h['page_end']}" if h["page_start"] != h["page_end"] else f"tr. {h['page_start']}"
        out.append(SearchHit(
            source_id=f"S{i}",
            doc_title=h["doc_title"],
            section_label=h["section_label"],
            section_type=h["section_type"],
            pages=pages,
            url=h.get("source_url"),
            text=h["text"],
            score=float(h.get("distance")) if h.get("distance") is not None else None,
        ))
    return out

@app.post("/chat", response_model=ChatAnswer)
def chat(payload: ChatIn):
    db = SessionLocal()
    hits = retrieve(
        db,
        payload.message,
        top_k=payload.top_k or settings.top_k,
        doc_type=payload.doc_type,
    )
    if not hits:
        raise HTTPException(status_code=404, detail="No sources found in knowledge base")
    return answer_question(payload.message, hits)

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
def list_documents(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    db = SessionLocal()
    rows = db.query(Document).order_by(Document.id.desc()).offset(offset).limit(limit).all()
    return [
        {
            "id": d.id,
            "doc_id": d.doc_id,
            "title": d.title,
            "version_date": d.version_date,
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
