from sqlalchemy import text
from sqlalchemy.orm import Session
from app.rag.embedder import get_embedder

def retrieve(db: Session, query: str, *, top_k: int = 8, doc_type: str | None = None) -> list[dict]:
    embedder = get_embedder()
    qvec = embedder.embed([query])[0]

    sql = text("""
      SELECT
        c.id,
        c.section_label,
        c.section_type,
        c.page_start,
        c.page_end,
        c.text,
        (c.embedding <=> CAST(:qvec AS vector)) AS distance,
        d.title AS doc_title,
        d.source_url AS source_url,
        d.doc_type AS doc_type
      FROM chunks c
      JOIN documents d ON d.id = c.document_id
      WHERE (CAST(:doc_type AS text) IS NULL OR d.doc_type = CAST(:doc_type AS text))
      ORDER BY c.embedding <=> CAST(:qvec AS vector)
      LIMIT :k
    """)
    rows = db.execute(sql, {"qvec": qvec, "k": top_k, "doc_type": doc_type}).mappings().all()
    return [dict(r) for r in rows]
