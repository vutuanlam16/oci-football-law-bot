import os
import glob
import argparse

from app.db import SessionLocal
from app.models import Document
from app.rag.ingest import ingest_pdf

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", default=os.getenv("PDF_DIR", "/data/raw"))
    parser.add_argument("--doc-type", default=None, help="laws|discipline|competition|other")
    parser.add_argument("--source-url-prefix", default=None, help="Optional base URL for citations")
    parser.add_argument("--force", action="store_true", help="Re-ingest even if doc_id exists (will create duplicate doc_id unless you delete first)")
    args = parser.parse_args()

    pdf_paths = sorted(glob.glob(os.path.join(args.pdf_dir, "*.pdf")))
    if not pdf_paths:
        print(f"[ingest] No PDFs found in {args.pdf_dir}")
        return

    db = SessionLocal()

    for pdf_path in pdf_paths:
        base = os.path.basename(pdf_path)
        doc_id = os.path.splitext(base)[0]

        exists = db.query(Document).filter(Document.doc_id == doc_id).first()
        if exists and not args.force:
            print(f"[ingest] Skip existing doc_id={doc_id}")
            continue

        title = doc_id
        source_url = None
        if args.source_url_prefix:
            source_url = args.source_url_prefix.rstrip("/") + "/" + base

        n = ingest_pdf(
            db,
            doc_id=doc_id,
            title=title,
            pdf_path=pdf_path,
            source_url=source_url,
            version_date=None,
            doc_type=args.doc_type,
        )
        print(f"[ingest] Ingested {doc_id}: {n} chunks")

if __name__ == "__main__":
    main()
