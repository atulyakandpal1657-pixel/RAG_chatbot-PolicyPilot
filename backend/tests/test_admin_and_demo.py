import io
import pytest
from fastapi.testclient import TestClient
from backend.app.config import settings
from backend.app.main import app
from backend.app.embeddings import EmbeddingError

client = TestClient(app)


def test_admin_routes_require_authentication():
    """All admin routes must return 401 when accessed without credentials."""
    dummy_file = {"files": ("test.txt", io.BytesIO(b"content"), "text/plain")}

    # 1. GET /documents
    resp = client.get("/api/admin/documents")
    assert resp.status_code == 401
    assert "Invalid or missing admin credentials" in resp.text

    # 2. POST /upload
    resp = client.post("/api/admin/upload", files=dummy_file)
    assert resp.status_code == 401
    assert "Invalid or missing admin credentials" in resp.text

    # 3. DELETE /documents/{id}
    resp = client.delete("/api/admin/documents/some_doc_id")
    assert resp.status_code == 401
    assert "Invalid or missing admin credentials" in resp.text

    # 4. POST /reindex
    resp = client.post("/api/admin/reindex")
    assert resp.status_code == 401
    assert "Invalid or missing admin credentials" in resp.text

    # 5. GET /eval-results
    resp = client.get("/api/admin/eval-results")
    assert resp.status_code == 401
    assert "Invalid or missing admin credentials" in resp.text

    # 6. POST /run-eval
    resp = client.post("/api/admin/run-eval")
    assert resp.status_code == 401
    assert "Invalid or missing admin credentials" in resp.text


def test_admin_status_endpoint_is_accessible():
    """The /api/admin/status endpoint provides deployment status without requiring credentials."""
    resp = client.get("/api/admin/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "app_env" in data
    assert "demo_mode" in data
    assert "company_name" in data
    assert "document_count" in data


def test_demo_mode_blocks_mutating_routes():
    """When DEMO_MODE is True, all mutating admin routes must return 403 even with correct password."""
    original_demo_mode = settings.DEMO_MODE
    original_password = settings.ADMIN_PASSWORD
    test_password = "test_valid_admin_password_123"

    try:
        settings.DEMO_MODE = True
        settings.ADMIN_PASSWORD = test_password
        headers = {"X-Admin-Password": test_password}

        # 1. POST /upload
        dummy_file = ("policy.pdf", io.BytesIO(b"%PDF-1.4 dummy content"), "application/pdf")
        resp_upload = client.post("/api/admin/upload", headers=headers, files={"files": dummy_file})
        assert resp_upload.status_code == 403, f"Upload should return 403 in demo mode, got {resp_upload.status_code}"
        assert "Operation disabled in demo mode" in resp_upload.json()["detail"]

        # 2. DELETE /documents/{id}
        resp_del = client.delete("/api/admin/documents/dummy_id", headers=headers)
        assert resp_del.status_code == 403, f"Delete should return 403 in demo mode, got {resp_del.status_code}"
        assert "Operation disabled in demo mode" in resp_del.json()["detail"]

        # 3. POST /reindex
        resp_reindex = client.post("/api/admin/reindex", headers=headers)
        assert resp_reindex.status_code == 403, f"Reindex should return 403 in demo mode, got {resp_reindex.status_code}"
        assert "Operation disabled in demo mode" in resp_reindex.json()["detail"]

        # 4. POST /run-eval
        resp_eval = client.post("/api/admin/run-eval", headers=headers)
        assert resp_eval.status_code == 403, f"Run-eval should return 403 in demo mode, got {resp_eval.status_code}"
        assert "Operation disabled in demo mode" in resp_eval.json()["detail"]

        # Permitted Read-only: GET /documents and GET /eval-results should NOT return 403
        resp_docs = client.get("/api/admin/documents", headers=headers)
        assert resp_docs.status_code == 200, f"GET documents should succeed in demo mode, got {resp_docs.status_code}"

    finally:
        settings.DEMO_MODE = original_demo_mode
        settings.ADMIN_PASSWORD = original_password


def test_upload_protections_size_and_extension():
    """Upload checks extension whitelist and maximum upload size."""
    original_demo_mode = settings.DEMO_MODE
    original_password = settings.ADMIN_PASSWORD
    test_password = "test_valid_admin_password_123"

    try:
        settings.DEMO_MODE = False
        settings.ADMIN_PASSWORD = test_password
        headers = {"X-Admin-Password": test_password}

        # 1. Invalid extension (.exe)
        bad_file = ("malware.exe", io.BytesIO(b"binary content"), "application/octet-stream")
        resp_ext = client.post("/api/admin/upload", headers=headers, files={"files": bad_file})
        assert resp_ext.status_code == 200  # Multi-file handler catches per-file error and returns result dict
        results = resp_ext.json().get("uploaded", [])
        assert len(results) == 1
        assert results[0]["status"] == "failed"
        assert "Unsupported file format" in results[0]["error"]

        # 2. Oversized file (> MAX_UPLOAD_SIZE_BYTES)
        original_max_size = settings.MAX_UPLOAD_SIZE_BYTES
        try:
            settings.MAX_UPLOAD_SIZE_BYTES = 100  # Set limit to 100 bytes for test
            oversized_data = b"x" * 200
            oversized_file = ("large.pdf", io.BytesIO(oversized_data), "application/pdf")
            resp_size = client.post("/api/admin/upload", headers=headers, files={"files": oversized_file})
            results_size = resp_size.json().get("uploaded", [])
            assert len(results_size) == 1
            assert results_size[0]["status"] == "failed"
            assert "exceeds maximum allowed size" in results_size[0]["error"]
        finally:
            settings.MAX_UPLOAD_SIZE_BYTES = original_max_size

    finally:
        settings.DEMO_MODE = original_demo_mode
        settings.ADMIN_PASSWORD = original_password


def test_embedding_failure_rolls_back_ingestion(monkeypatch):
    """When embedding provider fails during ingestion, database and vector store are rolled back."""
    from backend.app import embeddings
    from backend.app.routers import admin

    class FailingEmbeddingProvider(embeddings.EmbeddingProvider):
        def embed_texts(self, texts):
            raise EmbeddingError("Simulated provider outage")
        def embed_query(self, query):
            raise EmbeddingError("Simulated query outage")

    monkeypatch.setattr(admin, "get_embedding_provider", lambda: FailingEmbeddingProvider())

    original_demo_mode = settings.DEMO_MODE
    original_password = settings.ADMIN_PASSWORD
    test_password = "test_valid_admin_password_123"

    try:
        settings.DEMO_MODE = False
        settings.ADMIN_PASSWORD = test_password
        headers = {"X-Admin-Password": test_password}

        test_pdf = ("failing_doc.txt", io.BytesIO(b"Sample policy text for rollback test."), "text/plain")
        resp = client.post("/api/admin/upload", headers=headers, files={"files": test_pdf})
        data = resp.json()
        assert len(data["uploaded"]) == 1
        assert data["uploaded"][0]["status"] == "failed"
        assert "Embedding generation failed" in data["uploaded"][0]["error"]

        # Verify document was not left in SQLite
        from backend.app.db import get_document_by_id, list_documents
        docs = list_documents()
        assert not any(d["filename"] == "failing_doc.txt" for d in docs)

    finally:
        settings.DEMO_MODE = original_demo_mode
        settings.ADMIN_PASSWORD = original_password
