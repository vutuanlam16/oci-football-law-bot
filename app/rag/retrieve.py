from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.rag.embedder import get_embedder

def retrieve(
    db: Session, 
    query: str, 
    *, 
    top_k: int = 8, 
    doc_type: str | None = None,
    active_only: bool = True,
    effective_on: date | None = None
) -> list[dict]:
    """
    Retrieve relevant chunks using vector similarity search.
    
    Args:
        db: Database session
        query: User query string
        top_k: Number of results to return
        doc_type: Filter by document type (laws|discipline|competition|other)
        active_only: Only search in active (non-archived) documents
        effective_on: Filter by documents effective on this date
    
    Returns:
        List of chunks with metadata and similarity scores
    """
    embedder = get_embedder()
    qvec = embedder.embed([query])[0]

    # Build WHERE conditions
    where_clauses = []
    
    if doc_type:
        where_clauses.append("d.doc_type = CAST(:doc_type AS text)")
    
    if active_only:
        where_clauses.append("d.is_active = true")
    
    if effective_on:
        where_clauses.append(
            "(d.effective_date IS NULL OR d.effective_date <= CAST(:effective_on AS date))"
        )
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    sql = text(f"""
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
        d.doc_type AS doc_type,
        d.version_major,
        d.version_minor,
        d.is_active
      FROM chunks c
      JOIN documents d ON d.id = c.document_id
      WHERE {where_sql}
      ORDER BY c.embedding <=> CAST(:qvec AS vector)
      LIMIT :k
    """)
    
    params = {
        "qvec": qvec, 
        "k": top_k, 
        "doc_type": doc_type,
        "effective_on": effective_on
    }
    
    rows = db.execute(sql, params).mappings().all()
    return [dict(r) for r in rows]

