import os
import requests
from app.config import settings
from app.models import EMBED_DIM

MAX_EMBED_CHARS = int(os.getenv("EMBED_MAX_CHARS", "400"))

def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    # Prefer cutting on a whitespace boundary
    cut = text.rfind(" ", 0, max_chars)
    if cut == -1:
        cut = max_chars
    return text[:cut].strip()

class OllamaEmbedder:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.embed_model

    def embed(self, texts: list[str], *, truncate: bool = True, timeout_s: int = 120) -> list[list[float]]:
        # POST /api/embed with input as string[] is supported by Ollama.
        # https://docs.ollama.com/api/embed
        safe_texts = [_truncate_text(t, MAX_EMBED_CHARS) for t in texts]
        payload = {"model": self.model, "input": safe_texts, "truncate": truncate}
        r = requests.post(f"{self.base_url}/api/embed", json=payload, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
        embs = data.get("embeddings") or []
        if not embs:
            return []
        # Dimension safety check (must match DB schema)
        got = len(embs[0])
        if got != EMBED_DIM:
            raise RuntimeError(
                f"Embedding dim mismatch: model returned {got} dims, but DB expects {EMBED_DIM}. "
                f"Fix by using an embedding model with {EMBED_DIM} dims (e.g., nomic-embed-text), "
                f"or rebuild schema/migrations to match."
            )
        return embs
