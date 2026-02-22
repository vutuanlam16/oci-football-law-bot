import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "dev")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:your_secure_password_here@localhost:5432/football_law"
    )
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    chat_model: str = os.getenv("CHAT_MODEL", "qwen2.5:3b-instruct")
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")  # ollama|gemini
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    gemini_embed_model: str = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    embed_model: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
    embed_provider: str = os.getenv("EMBED_PROVIDER", "ollama")  # ollama|gemini
    embed_dim: int = int(os.getenv("EMBED_DIM", "768"))
    top_k: int = int(os.getenv("TOP_K", "8"))
    pdf_dir: str = os.getenv("PDF_DIR", "./data/raw")

settings = Settings()
