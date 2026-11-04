import hmac
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel
from backend.app.bm25_store import get_bm25_store
from backend.app.chunker import create_chunks_for_document
from backend.app.config import settings
from backend.app.db import (
    delete_document,
    get_all_chunks,
    get_document_by_id,
    list_documents,
    save_chunks,
    upsert_document,
    update_document_status,
)
from backend.app.embeddings import get_embedding_provider, EmbeddingError
from backend.app.parser import parse_document
from backend.app.vector_store import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def verify_admin_password(
    x_admin_password: Optional[str] = Header(None, alias="X-Admin-Password"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> bool:
    """Verifies that the caller provided the correct ADMIN_PASSWORD using constant-time comparison."""
    expected = settings.ADMIN_PASSWORD.strip() if settings.ADMIN_PASSWORD else ""
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin credentials not configured.",
        )

    provided = None
    if x_admin_password:
        provided = x_admin_password.strip()
    elif authorization and authorization.startswith("Bearer "):
        provided = authorization.split("Bearer ", 1)[1].strip()

    if provided and hmac.compare_digest(provided, expected):
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing admin credentials.",
    )


def verify_demo_mode_allowed() -> None:
    """Blocks mutating or resource-intensive operations when DEMO_MODE is active."""
    if settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation disabled in demo mode. Read-only access only.",
        )


async def read_upload_file_safely(file: UploadFile, max_bytes: int) -> bytes:
    """
    Safely reads an uploaded file in chunks while enforcing maximum file size
    and checking allowed file extension before reading into memory.
    """
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{suffix}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    total_bytes = 0
    chunks = []
    chunk_size = 64 * 1024  # 64 KB
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File '{filename}' exceeds maximum allowed size of {max_bytes // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


class DocumentResponse(BaseModel):
    id: str
    filename: str
    upload_time: str
    page_count: int
    chunk_count: int
    file_size: int
    status: str


class AdminStatusResponse(BaseModel):
    app_env: str
    demo_mode: bool
    company_name: str
    document_count: int


@router.get("/status", response_model=AdminStatusResponse)
async def get_admin_status():
    """Returns deployment status, demo mode flag, and current document count."""
    docs = list_documents(collection="default")
    return AdminStatusResponse(
        app_env=settings.APP_ENV or "production",
        demo_mode=bool(settings.DEMO_MODE),
        company_name=settings.COMPANY_NAME,
        document_count=len(docs),
    )


@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(_: bool = Depends(verify_admin_password)):
    """Retrieve all ingested documents."""
    return list_documents()


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    _: bool = Depends(verify_admin_password),
    __: None = Depends(verify_demo_mode_allowed),
):
    """
    Multi-file document ingestion.
    Re-uploading a file with the same name cleanly replaces the old version.
    In DEMO_MODE, returns HTTP 403.
    """
    results = []
    vector_store = get_vector_store()
    embeddings_provider = get_embedding_provider()
    bm25_store = get_bm25_store()

    for file in files:
        filename = Path(file.filename or "unknown").name
        # Validation: raises HTTP 400 for unsupported extension and HTTP 413 for oversized file
        content = await read_upload_file_safely(file, settings.MAX_UPLOAD_SIZE_BYTES)
        file_size = len(content)
        doc_id = None
        try:
            # 1. Parse document into pages
            pages = parse_document(content, filename)
            page_count = len(pages)

            # 2. Upsert document record in SQLite (cleans up old chunks if exists)
            doc_id = upsert_document(
                filename=filename,
                page_count=page_count,
                chunk_count=0,
                file_size=file_size,
                status="processing",
            )

            # Remove old vectors from ChromaDB if replacing
            vector_store.delete_by_filename(filename)

            # 3. Chunk text respecting page boundaries
            chunks = create_chunks_for_document(
                doc_id=doc_id,
                filename=filename,
                pages=pages,
                target_size=800,
                overlap=120,
            )

            # 4. Generate embeddings and store in ChromaDB
            chunk_texts = [c["content"] for c in chunks]
            embeddings = embeddings_provider.embed_texts(chunk_texts)
            vector_store.add_chunks(chunks, embeddings)

            # 5. Save chunks to SQLite
            save_chunks(doc_id, chunks)

            # Update document status to ready
            update_document_status(doc_id, len(chunks), "ready")

            results.append({
                "filename": filename,
                "status": "ready",
                "page_count": page_count,
                "chunk_count": len(chunks)
            })

        except EmbeddingError as ee:
            logger.error(f"Embedding failure during upload of {filename}: {ee}")
            if doc_id:
                try:
                    vector_store.delete_by_doc_id(doc_id)
                    vector_store.delete_by_filename(filename)
                    delete_document(doc_id)
                except Exception:
                    pass
            results.append({
                "filename": filename,
                "status": "failed",
                "error": "Embedding generation failed. Document ingestion was rolled back."
            })
        except Exception as e:
            logger.error(f"Error processing file {filename}: {type(e).__name__}", exc_info=True)
            if doc_id:
                try:
                    vector_store.delete_by_doc_id(doc_id)
                    vector_store.delete_by_filename(filename)
                    delete_document(doc_id)
                except Exception:
                    pass
            results.append({
                "filename": filename,
                "status": "failed",
                "error": str(e)
            })

    # Rebuild BM25 index after upload
    bm25_store.rebuild()

    return {"uploaded": results}


@router.delete("/documents/{doc_id_or_name}")
async def delete_document_endpoint(
    doc_id_or_name: str,
    _: bool = Depends(verify_admin_password),
    __: None = Depends(verify_demo_mode_allowed),
):
    """Deletes a document from SQLite, ChromaDB, and updates BM25. In DEMO_MODE, returns 403."""
    vector_store = get_vector_store()
    bm25_store = get_bm25_store()

    # Delete from ChromaDB
    vector_store.delete_by_doc_id(doc_id_or_name)
    vector_store.delete_by_filename(doc_id_or_name)

    # Delete from SQLite
    deleted_id = delete_document(doc_id_or_name)
    if not deleted_id:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Rebuild BM25 index
    bm25_store.rebuild()

    return {"message": f"Document '{doc_id_or_name}' deleted successfully."}


@router.post("/reindex")
async def reindex_all(
    _: bool = Depends(verify_admin_password),
    __: None = Depends(verify_demo_mode_allowed),
):
    """Re-indexes all existing documents and updates BM25. In DEMO_MODE, returns 403."""
    bm25_store = get_bm25_store()
    bm25_store.rebuild()
    return {"message": "Re-indexed successfully.", "total_chunks": len(get_all_chunks())}


@router.get("/eval-results")
async def get_eval_results(
    track: str = "all",
    _: bool = Depends(verify_admin_password)
):
    """Returns the evaluation reports for synthetic and/or real-world tracks."""
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    synthetic_path = project_root / "eval" / "results.json"
    real_path = project_root / "eval" / "real_results.json"
    real_v2_path = project_root / "eval" / "real_results_v2.json"

    res: Dict[str, Any] = {"has_results": False}

    synthetic_data = None
    if synthetic_path.exists():
        try:
            synthetic_data = json.loads(synthetic_path.read_text(encoding="utf-8"))
            synthetic_data["has_results"] = True
            res["synthetic"] = synthetic_data
            for k, v in synthetic_data.items():
                if k not in res:
                    res[k] = v
            res["has_results"] = True
        except Exception as e:
            logger.warning(f"Error reading synthetic results: {e}")

    real_data = None
    if real_path.exists():
        try:
            real_data = json.loads(real_path.read_text(encoding="utf-8"))
            real_data["has_results"] = True
            res["real"] = real_data
            res["has_results"] = True
        except Exception as e:
            logger.warning(f"Error reading real results: {e}")

    real_v2_data = None
    if real_v2_path.exists():
        try:
            real_v2_data = json.loads(real_v2_path.read_text(encoding="utf-8"))
            real_v2_data["has_results"] = True
            res["real_v2"] = real_v2_data
            res["has_results"] = True
        except Exception as e:
            logger.warning(f"Error reading real v2 results: {e}")

    if track == "synthetic" and synthetic_data:
        return synthetic_data
    elif track == "real" and real_data:
        return real_data
    elif track == "real_v2" and real_v2_data:
        return real_v2_data

    if not res["has_results"]:
        res["message"] = "Evaluation has not been run yet. Click 'Run Evaluation' to start."

    return res


@router.post("/run-eval")
async def trigger_eval(
    track: str = "synthetic",
    _: bool = Depends(verify_admin_password),
    __: None = Depends(verify_demo_mode_allowed),
):
    """Triggers an evaluation run programmatically. In DEMO_MODE, returns 403."""
    import subprocess
    import sys

    project_root = Path(__file__).resolve().parent.parent.parent.parent
    eval_script = project_root / "eval" / "run_eval.py"
    track_arg = track if track in ["real", "real_v2"] else "synthetic"

    try:
        result = subprocess.run(
            [sys.executable, str(eval_script), "--track", track_arg],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(project_root),
        )
        if track_arg == "real_v2":
            target_file = "real_results_v2.json"
        elif track_arg == "real":
            target_file = "real_results.json"
        else:
            target_file = "results.json"

        results_path = project_root / "eval" / target_file
        if results_path.exists():
            data = json.loads(results_path.read_text(encoding="utf-8"))
            data["has_results"] = True
            return data
        return {"has_results": True, "output": result.stdout}
    except Exception as e:
        logger.error(f"Failed to run evaluation ({track_arg}): {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Evaluation execution failed.")
