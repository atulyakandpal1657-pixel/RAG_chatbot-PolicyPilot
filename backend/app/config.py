from pathlib import Path
from typing import Optional, Union
import os
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

KNOWN_DEFAULT_PASSWORDS = {
    "change_me_in_env",
    "change_this_to_a_secure_password",
    "admin",
    "password",
    "12345678",
    "root",
}
MIN_ADMIN_PASSWORD_LENGTH = 12


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment & Demo Mode
    APP_ENV: Optional[str] = "production"
    DEMO_MODE: Optional[Union[bool, str]] = None

    # Provider Selection
    LLM_PROVIDER: str = "gemini"
    EMBEDDINGS_PROVIDER: str = "gemini"

    # Gemini (model names sourced from https://ai.google.dev/gemini-api/docs/models)
    GEMINI_API_KEY: str = ""
    GEMINI_LLM_MODEL: str = "gemini-3.6-flash"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash,gemini-3.6-flash,gemini-flash-lite-latest"
    GEMINI_JUDGE_MODEL: str = "gemini-3.6-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

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

    # Limits and Protections
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_QUESTION_LENGTH: int = 1500
    RATE_LIMIT_PER_MINUTE: int = 30
    DAILY_REQUEST_CAP: int = 500
    TRUSTED_PROXIES: str = "127.0.0.1,::1"

    # Branding
    COMPANY_NAME: str = "Northwind Labs"

    # Comma-separated browser origins permitted by CORS
    CORS_ALLOWED_ORIGINS: str = ""

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

    @model_validator(mode="after")
    def validate_env_and_security(self) -> "Settings":
        # 0. Deprecated env var guard — fail clearly instead of silently ignoring old names
        _deprecated = {
            "ALLOWED_ORIGINS": "CORS_ALLOWED_ORIGINS",
        }
        for old_name, new_name in _deprecated.items():
            if os.environ.get(old_name) is not None:
                raise ValueError(
                    f"Environment variable '{old_name}' is deprecated. "
                    f"Rename it to '{new_name}' in your deployment configuration."
                )

        # 1. APP_ENV validation
        env_raw = (self.APP_ENV or "production").strip().lower()
        if env_raw not in ("production", "development"):
            raise ValueError(f"Invalid APP_ENV: '{self.APP_ENV}'. Must be 'production' or 'development'.")
        self.APP_ENV = env_raw

        # 2. DEMO_MODE resolution
        if self.DEMO_MODE is None:
            self.DEMO_MODE = True if self.APP_ENV == "production" else False
        elif isinstance(self.DEMO_MODE, str):
            dm_str = self.DEMO_MODE.strip().lower()
            if dm_str in ("true", "1", "yes"):
                self.DEMO_MODE = True
            elif dm_str in ("false", "0", "no"):
                self.DEMO_MODE = False
            else:
                raise ValueError(f"Invalid DEMO_MODE: '{self.DEMO_MODE}'. Must be 'true' or 'false'.")
        elif isinstance(self.DEMO_MODE, bool):
            pass
        else:
            raise ValueError(f"Invalid DEMO_MODE type: {type(self.DEMO_MODE)}. Must be boolean or 'true'/'false'.")

        # 3. Production Password & Strength checks
        # All rules apply unconditionally in production, regardless of DEMO_MODE.
        if self.APP_ENV == "production":
            pwd = (self.ADMIN_PASSWORD or "").strip()
            if not pwd:
                raise ValueError("ADMIN_PASSWORD must be configured and cannot be empty in production.")
            if pwd in KNOWN_DEFAULT_PASSWORDS:
                raise ValueError(
                    "In production, ADMIN_PASSWORD cannot be a known default placeholder."
                )
            if len(pwd) < MIN_ADMIN_PASSWORD_LENGTH:
                raise ValueError(
                    f"In production, ADMIN_PASSWORD must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters."
                )

        return self


settings = Settings()
