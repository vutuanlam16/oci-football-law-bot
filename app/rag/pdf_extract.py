import fitz  # PyMuPDF

def extract_pages(pdf_path: str) -> list[tuple[int, str]]:
    """Return list of (page_no starting at 1, page_text)."""
    doc = fitz.open(pdf_path)
    pages: list[tuple[int, str]] = []
    for i in range(len(doc)):
        text = doc.load_page(i).get_text("text") or ""
        pages.append((i + 1, text))
    doc.close()
    return pages
