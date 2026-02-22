import re
from dataclasses import dataclass

LAW_RE = re.compile(r"^\s*LU\s*\ẬT\s+\d+\b.*$", re.IGNORECASE)
ARTICLE_RE = re.compile(r"^\s*ĐI\s*ỀU\s+\d+\b.*$", re.IGNORECASE)

@dataclass
class ChunkOut:
    section_label: str
    section_type: str
    page_start: int
    page_end: int
    text: str

MAX_CHARS = 800  # keep chunks small to avoid embedding context limits

def _split_text(text: str, max_chars: int) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for ln in text.splitlines(keepends=True):
        if size + len(ln) > max_chars and buf:
            parts.append("".join(buf).strip() + "\n")
            buf = []
            size = 0
        buf.append(ln)
        size += len(ln)
    if buf:
        parts.append("".join(buf).strip() + "\n")
    return [p for p in parts if p.strip()]

def chunk_pages(pages: list[tuple[int, str]]) -> list[ChunkOut]:
    """Heuristic chunking by legal headings (LUẬT / Điều). Keeps page range for citations."""
    chunks: list[ChunkOut] = []
    cur: dict | None = None

    def flush():
        nonlocal cur
        if cur and (cur.get("text") or "").strip():
            text = cur["text"]
            parts = _split_text(text, MAX_CHARS)
            for p in parts:
                chunks.append(
                    ChunkOut(
                        section_label=cur["section_label"],
                        section_type=cur["section_type"],
                        page_start=cur["page_start"],
                        page_end=cur["page_end"],
                        text=p,
                    )
                )
        cur = None

    for page_no, page_text in pages:
        lines = [ln.rstrip() for ln in page_text.splitlines()]
        for ln in lines:
            if LAW_RE.match(ln):
                flush()
                cur = {
                    "section_label": ln.strip(),
                    "section_type": "LAW",
                    "page_start": page_no,
                    "page_end": page_no,
                    "text": ln.strip() + "\n",
                }
                continue

            if ARTICLE_RE.match(ln):
                flush()
                cur = {
                    "section_label": ln.strip(),
                    "section_type": "ARTICLE",
                    "page_start": page_no,
                    "page_end": page_no,
                    "text": ln.strip() + "\n",
                }
                continue

            if cur is None:
                # fallback if document lacks headings
                cur = {
                    "section_label": f"Trang {page_no}",
                    "section_type": "PAGE",
                    "page_start": page_no,
                    "page_end": page_no,
                    "text": "",
                }

            cur["text"] += ln + "\n"
            cur["page_end"] = page_no

    flush()
    return chunks
