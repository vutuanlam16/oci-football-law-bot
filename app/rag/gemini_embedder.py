import os
import requests
from app.config import settings
from app.models import EMBED_DIM

MAX_EMBED_CHARS = int(os.getenv("EMBED_MAX_CHARS", "400"))

def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text.rfind(" ", 0, max_chars)
    if cut == -1:
        cut = max_chars
    return text[:cut].strip()

class GeminiEmbedder:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_embed_model
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required when EMBED_PROVIDER=gemini")

    def embed(self, texts: list[str], *, timeout_s: int = 60) -> list[list[float]]:
        safe_texts = [_truncate_text(t, MAX_EMBED_CHARS) for t in texts]
        results = []
        
        for text in safe_texts:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
            payload = {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": text}]},
                "outputDimensionality": EMBED_DIM,
            }
            r = requests.post(url, json=payload, timeout=timeout_s)
            r.raise_for_status()
            data = r.json()
            emb = data.get("embedding", {}).get("values", [])
            results.append(emb)
        
        if not results:
            return []
        
        got = len(results[0])
        if got != EMBED_DIM:
            raise RuntimeError(
                f"Embedding dim mismatch: model returned {got} dims, but DB expects {EMBED_DIM}. "
                f"Check EMBED_DIM setting or Gemini API response."
            )
        return results
