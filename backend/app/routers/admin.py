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
from backend.app.embeddings import get_embedding_provider
from backend.app.parser import parse_document
from backend.app.vector_store import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def verify_admin_password(
    x_admin_password: Optional[str] = Header(None, alias="X-Admin-Password"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> bool:
    """Verifies that the caller provided the correct ADMIN_PASSWORD."""
    expected = settings.ADMIN_PASSWORD.strip()
    # Check X-Admin-Password header
    if x_admin_password and x_admin_password.strip() == expected:
        return True

    # Check Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        if token == expected:
            return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing admin credentials.",
    )


class DocumentResponse(BaseModel):
    id: str
    filename: str
    upload_time: str
    page_count: int
    chunk_count: int
    file_size: int
    status: str


@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(_: bool = Depends(verify_admin_password)):
    """Retrieve all ingested documents."""
    return list_documents()


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    _: bool = Depends(verify_admin_password)
):
    """
    Multi-file document ingestion.
    Re-uploading a file with the same name cleanly replaces the old version.
    """
    results = []
    vector_store = get_vector_store()
    embeddings_provider = get_embedding_provider()
    bm25_store = get_bm25_store()

    for file in files:
        filename = Path(file.filename).name
        try:
            content = await file.read()
            file_size = len(content)

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

        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}", exc_info=True)
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
    _: bool = Depends(verify_admin_password)
):
    """Deletes a document from SQLite, ChromaDB, and updates BM25."""
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
async def reindex_all(_: bool = Depends(verify_admin_password)):
    """Re-indexes all existing documents and updates BM25."""
    bm25_store = get_bm25_store()
    bm25_store.rebuild()
    return {"message": "Re-indexed successfully.", "total_chunks": len(get_all_chunks())}


@router.get("/eval-results")
async def get_eval_results(
    track: str = "all",
    _: bool = Depends(verify_admin_password)
):
    """Returns the evaluation reports for synthetic and/or real-world tracks."""
    # Resolve absolute path so it works regardless of uvicorn's working directory
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
    _: bool = Depends(verify_admin_password)
):
    """Triggers an evaluation run programmatically for synthetic or real tracks."""
    import subprocess
    import sys
    from pathlib import Path

    # Resolve absolute path — safe even when the project root contains spaces
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    eval_script = project_root / "eval" / "run_eval.py"
    track_arg = track if track in ["real", "real_v2"] else "synthetic"

    try:
        # Use a list so subprocess never needs shell=True (no quoting issues)
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
        logger.error(f"Failed to run evaluation ({track_arg}): {e}")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
