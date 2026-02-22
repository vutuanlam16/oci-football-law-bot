import os
import requests
from app.config import settings

class OllamaChat:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.chat_model

    def chat(self, messages: list[dict], *, temperature: float = 0.1, timeout_s: int | None = None) -> str:
        if timeout_s is None:
            timeout_s = int(os.getenv("OLLAMA_CHAT_TIMEOUT", "600"))
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=timeout_s)
        r.raise_for_status()
        data = r.json()
        return (data.get("message") or {}).get("content") or ""
