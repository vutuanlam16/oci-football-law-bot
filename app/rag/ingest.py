import os
import time
from sqlalchemy.orm import Session
from app.models import Document, Chunk
from app.rag.pdf_extract import extract_pages
from app.rag.chunker import chunk_pages
from app.rag.embedder import get_embedder

def ingest_pdf(
    db: Session,
    *,
    doc_id: str,
    title: str,
    pdf_path: str,
    source_url: str | None = None,
    version_date: str | None = None,
    doc_type: str | None = None,
    batch_size: int = int(os.getenv("EMBED_BATCH_SIZE", "8")),
) -> int:
    """Ingest a single PDF into DB. Returns number of chunks inserted."""
    doc = Document(
        doc_id=doc_id,
        title=title,
        version_date=version_date,
        source_url=source_url,
        doc_type=doc_type,
    )
    db.add(doc)
    db.flush()  # assign doc.id

    pages = extract_pages(pdf_path)
    chunks = chunk_pages(pages)

    embedder = get_embedder()
    total = 0

    batch_sleep = float(os.getenv("EMBED_BATCH_SLEEP", "0"))
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        embs = embedder.embed([c.text for c in batch])

        for c, e in zip(batch, embs):
            db.add(
                Chunk(
                    document_id=doc.id,
                    section_label=c.section_label,
                    section_type=c.section_type,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    text=c.text,
                    embedding=e,
                )
            )
            total += 1
        if batch_sleep > 0:
            time.sleep(batch_sleep)

    db.commit()
    return total
