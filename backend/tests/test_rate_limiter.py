import pytest
from fastapi.testclient import TestClient
from backend.app.config import settings
from backend.app.main import app
from backend.app.rate_limiter import limiter
from backend.app.embeddings import EmbeddingError

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter_state():
    limiter.reset_for_tests()
    yield
    limiter.reset_for_tests()


def test_chat_empty_or_whitespace_question_fails():
    """Empty or whitespace-only questions return 400 Bad Request."""
    resp = client.post("/api/chat", json={"question": "   ", "history": []})
    assert resp.status_code == 400
    assert "Question cannot be empty" in resp.json()["detail"]


def test_chat_oversized_question_fails():
    """Questions exceeding MAX_QUESTION_LENGTH return 400 Bad Request."""
    original_max = settings.MAX_QUESTION_LENGTH
    try:
        settings.MAX_QUESTION_LENGTH = 50
        oversized = "What is the policy regarding " + "a" * 100 + "?"
        resp = client.post("/api/chat", json={"question": oversized, "history": []})
        assert resp.status_code == 400
        assert "Question exceeds maximum length" in resp.json()["detail"]
    finally:
        settings.MAX_QUESTION_LENGTH = original_max


def test_chat_embedding_failure_returns_503(monkeypatch):
    """When embedding provider fails during chat, service returns 503 (no silent hash/zero vectors)."""
    from backend.app.routers import chat

    class FailingEmbeddingProvider:
        def embed_query(self, query):
            raise EmbeddingError("Gemini embedding API unavailable")

    monkeypatch.setattr(chat, "get_embedding_provider", lambda: FailingEmbeddingProvider())

    resp = client.post("/api/chat", json={"question": "What is the vacation policy?", "history": []})
    assert resp.status_code == 503
    assert "Embedding service temporarily unavailable" in resp.json()["detail"]


def test_rate_limit_per_minute_triggers_429():
    """Exceeding RATE_LIMIT_PER_MINUTE from the same client IP returns 429."""
    original_limit = settings.RATE_LIMIT_PER_MINUTE
    try:
        settings.RATE_LIMIT_PER_MINUTE = 3

        # First 3 requests should pass the rate limiter check (even if mock chat body fails or succeeds)
        for _ in range(3):
            # Using invalid empty body to trigger 400 after rate limit check succeeds
            resp = client.post("/api/chat", json={"question": "   ", "history": []})
            assert resp.status_code == 400

        # 4th request must be rejected by rate limiter with 429
        resp_blocked = client.post("/api/chat", json={"question": "valid query", "history": []})
        assert resp_blocked.status_code == 429
        assert "Rate limit exceeded" in resp_blocked.json()["detail"]
    finally:
        settings.RATE_LIMIT_PER_MINUTE = original_limit


def test_untrusted_client_cannot_bypass_rate_limit_with_forged_x_forwarded_for():
    """
    An untrusted client sending rotating X-Forwarded-For headers CANNOT bypass the rate limit
    because the peer IP is used, ignoring the forged header.
    """
    original_limit = settings.RATE_LIMIT_PER_MINUTE
    original_trusted = settings.TRUSTED_PROXIES
    try:
        settings.RATE_LIMIT_PER_MINUTE = 2
        # Set trusted proxies to something other than TestClient's default peer host (testclient)
        settings.TRUSTED_PROXIES = "192.168.1.100"

        # Client sends fake X-Forwarded-For: 1.1.1.1
        resp1 = client.post("/api/chat", json={"question": "   "}, headers={"X-Forwarded-For": "1.1.1.1"})
        assert resp1.status_code == 400

        # Client sends fake X-Forwarded-For: 2.2.2.2
        resp2 = client.post("/api/chat", json={"question": "   "}, headers={"X-Forwarded-For": "2.2.2.2"})
        assert resp2.status_code == 400

        # 3rd request from same socket sending yet another fake header (3.3.3.3) MUST be blocked
        resp3 = client.post("/api/chat", json={"question": "   "}, headers={"X-Forwarded-For": "3.3.3.3"})
        assert resp3.status_code == 429
        assert "Rate limit exceeded" in resp3.json()["detail"]
    finally:
        settings.RATE_LIMIT_PER_MINUTE = original_limit
        settings.TRUSTED_PROXIES = original_trusted


def test_daily_request_cap_triggers_429():
    """Exceeding DAILY_REQUEST_CAP triggers 429 across all requests."""
    original_cap = settings.DAILY_REQUEST_CAP
    try:
        settings.DAILY_REQUEST_CAP = 2

        # Make 2 requests
        client.post("/api/chat", json={"question": "   "})
        client.post("/api/chat", json={"question": "   "})

        # 3rd request should hit daily quota
        resp = client.post("/api/chat", json={"question": "Any question"})
        assert resp.status_code == 429
        assert "Daily demo request quota exceeded" in resp.json()["detail"]
    finally:
        settings.DAILY_REQUEST_CAP = original_cap

