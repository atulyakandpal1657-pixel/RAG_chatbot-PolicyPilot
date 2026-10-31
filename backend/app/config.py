from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Provider Selection
    LLM_PROVIDER: str = "gemini"
    EMBEDDINGS_PROVIDER: str = "gemini"

    # Gemini (model names sourced from https://ai.google.dev/gemini-api/docs/models)
    GEMINI_API_KEY: str = ""
    GEMINI_LLM_MODEL: str = "gemini-3.6-flash"         # verified active non-2.5 Flash model
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash,gemini-3.6-flash,gemini-flash-lite-latest"
    GEMINI_JUDGE_MODEL: str = "gemini-3.6-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"  # verified active embedding model

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_LLM_MODEL: str = "claude-3-5-haiku-20241022"

    # Retrieval and Threshold
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.55
    TOP_K_RETRIEVAL: int = 5
    RRF_K: int = 60

    # Admin Portal
    ADMIN_PASSWORD: str = "change_me_in_env"

    # Storage Paths
    SQLITE_DB_PATH: str = "data/policypilot.db"
    CHROMA_PERSIST_DIR: str = "data/chroma"
    SAMPLE_DOCS_DIR: str = "sample_docs"

    @property
    def sqlite_full_path(self) -> Path:
        p = Path(self.SQLITE_DB_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def chroma_full_path(self) -> Path:
        p = Path(self.CHROMA_PERSIST_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
