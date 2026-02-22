import json
from app.config import settings
from app.schemas import ChatAnswer, Citation
from app.rag.ollama_chat import OllamaChat
from app.rag.gemini_chat import GeminiChat

SYSTEM = (
    "Bạn là trợ lý tra cứu Luật bóng đá Việt Nam.\n"
    "CHỈ được trả lời dựa trên SOURCES được cung cấp.\n"
    "Mọi nội dung quan trọng phải có trích dẫn (source_id).\n"
    "Nếu SOURCES không đủ: trả lời 'Chưa đủ dữ liệu' và hỏi 1-2 câu làm rõ.\n"
    "Output ONLY JSON (không kèm markdown, không kèm giải thích ngoài JSON).\n"
)

def _build_sources(hits: list[dict]) -> tuple[str, list[dict]]:
    metas: list[dict] = []
    blocks: list[str] = []
    for i, h in enumerate(hits, start=1):
        sid = f"S{i}"
        pages = f"tr. {h['page_start']}-{h['page_end']}" if h["page_start"] != h["page_end"] else f"tr. {h['page_start']}"
        meta = {
            "source_id": sid,
            "doc_title": h["doc_title"],
            "section_label": h["section_label"],
            "pages": pages,
            "url": h.get("source_url"),
        }
        metas.append(meta)
        blocks.append(
            f"[{sid}] {meta['doc_title']} | {meta['section_label']} | {meta['pages']} | {meta['url']}\n"
            f"{h['text']}\n"
        )
    return "\n---\n".join(blocks), metas

def _extract_json(raw: str) -> dict:
    # Best-effort extraction if the model accidentally adds extra text
    raw = raw.strip()
    if raw.startswith("{") and raw.endswith("}"):
        return json.loads(raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(raw[start:end+1])
    raise ValueError("No JSON object found")

def _call_llm(prompt: str, *, model: str | None = None) -> str:
    if settings.llm_provider == "gemini":
        llm = GeminiChat(model=model)
        return llm.chat(SYSTEM, prompt, temperature=0.1)
    llm = OllamaChat(model=model)
    return llm.chat(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        temperature=0.1,
    )

def answer_question(question: str, hits: list[dict], *, model: str | None = None) -> ChatAnswer:
    sources_text, sources_meta = _build_sources(hits)
    allowed = {m["source_id"]: m for m in sources_meta}

    prompt = f"""QUESTION:
{question}

SOURCES:
{sources_text}

Return JSON with this schema:
{{
  "answer": "...",
  "related_provisions": ["..."],
  "citations": [
    {{
      "source_id": "S1",
      "quote": "<=30 từ trích đúng từ nguồn",
      "doc_title": "",
      "section_label": "",
      "pages": "",
      "url": null
    }}
  ],
  "followup_questions": [],
  "confidence": 0.0
}}

Rules:
- citations[].source_id MUST be one of: {list(allowed.keys())}
- quote must be copied from SOURCES (<= 30 words)
- doc_title/section_label/pages/url can be empty (server will fill)
- If not enough evidence, answer must be 'Chưa đủ dữ liệu' and include followup_questions.
"""

    raw = _call_llm(prompt, model=model)

    try:
        data = _extract_json(raw)
        out = ChatAnswer.model_validate(data)
    except Exception:
        # fallback: safe response
        out = ChatAnswer(
            answer="Chưa đủ dữ liệu để trả lời chắc chắn dựa trên các nguồn hiện có.",
            related_provisions=[],
            citations=[],
            followup_questions=["Bạn đang hỏi theo luật thi đấu (IFAB/VFF) hay điều lệ giải cụ thể (mùa nào)?"],
            confidence=0.0,
        )
        return out

    # Guardrail: keep only citations that reference provided sources; override metadata from DB
    cleaned: list[Citation] = []
    for c in out.citations:
        if c.source_id in allowed:
            meta = allowed[c.source_id]
            c.doc_title = meta["doc_title"]
            c.section_label = meta["section_label"]
            c.pages = meta["pages"]
            c.url = meta["url"]
            cleaned.append(c)
    out.citations = cleaned

    # Heuristic confidence: require at least 1 citation
    out.confidence = 0.75 if out.citations else 0.0
    return out
