import os
import pytest

# Ensure test environment defaults are set before any application module is imported
# This ensures pytest runs cleanly in CI or fresh clones with NO .env file present.
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEMO_MODE", "false")
os.environ.setdefault("ADMIN_PASSWORD", "test_ci_admin_password_123")
os.environ.setdefault("GEMINI_API_KEY", "dummy_gemini_api_key_for_ci_tests")
os.environ.setdefault("SQLITE_DB_PATH", "data/policypilot.db")
os.environ.setdefault("CHROMA_PERSIST_DIR", "data/chroma")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")


@pytest.fixture(autouse=True, scope="session")
def ensure_database_initialized():
    """Ensures SQLite tables and persistence directories exist before running tests."""
    from backend.app.config import settings
    from backend.app.db import init_db

    # Create directories if they do not exist
    settings.sqlite_full_path.parent.mkdir(parents=True, exist_ok=True)
    settings.chroma_full_path.mkdir(parents=True, exist_ok=True)
    init_db()
