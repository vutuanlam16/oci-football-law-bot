from app.config import settings
from app.rag.ollama_embedder import OllamaEmbedder
from app.rag.gemini_embedder import GeminiEmbedder


def get_embedder():
    if settings.embed_provider == "gemini":
        return GeminiEmbedder()
    return OllamaEmbedder()
