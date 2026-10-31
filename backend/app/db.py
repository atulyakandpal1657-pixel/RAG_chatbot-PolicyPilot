import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.config import settings


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.sqlite_full_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize SQLite database tables for document metadata and chunks."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT UNIQUE NOT NULL,
                upload_time TEXT NOT NULL,
                page_count INTEGER NOT NULL DEFAULT 0,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                file_size INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'ready',
                collection TEXT NOT NULL DEFAULT 'default'
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                char_count INTEGER NOT NULL,
                collection TEXT NOT NULL DEFAULT 'default',
                FOREIGN KEY (doc_id) REFERENCES documents (id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks (doc_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_filename ON chunks (filename)")

        # Migrations for existing databases
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN collection TEXT NOT NULL DEFAULT 'default'")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE chunks ADD COLUMN collection TEXT NOT NULL DEFAULT 'default'")
        except Exception:
            pass
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_collection ON chunks (collection)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents (collection)")
        conn.commit()


def upsert_document(
    filename: str,
    page_count: int = 0,
    chunk_count: int = 0,
    file_size: int = 0,
    status: str = "ready",
    clear_chunks: bool = True,
    collection: str = "default",
) -> str:
    """Insert or update a document record. Only clears chunks if clear_chunks is True."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE filename = ?", (filename,))
        existing = cursor.fetchone()
        
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            doc_id = existing["id"]
            if clear_chunks:
                cursor.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            cursor.execute(
                """
                UPDATE documents
                SET upload_time = ?, page_count = ?, chunk_count = ?, file_size = ?, status = ?, collection = ?
                WHERE id = ?
                """,
                (now, page_count, chunk_count, file_size, status, collection, doc_id),
            )
        else:
            doc_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO documents (id, filename, upload_time, page_count, chunk_count, file_size, status, collection)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, filename, now, page_count, chunk_count, file_size, status, collection),
            )
        conn.commit()
        return doc_id


def update_document_status(doc_id: str, chunk_count: int, status: str = "ready") -> None:
    """Update document chunk count and status without touching chunks."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE documents SET chunk_count = ?, status = ? WHERE id = ?",
            (chunk_count, status, doc_id)
        )
        conn.commit()


def save_chunks(doc_id: str, chunks: List[Dict[str, Any]], collection: str = "default") -> None:
    """Save chunks associated with a document."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for c in chunks:
            cursor.execute(
                """
                INSERT OR REPLACE INTO chunks (id, doc_id, filename, page_number, chunk_index, content, char_count, collection)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c["id"],
                    doc_id,
                    c["filename"],
                    c["page_number"],
                    c["chunk_index"],
                    c["content"],
                    len(c["content"]),
                    collection,
                ),
            )
        conn.commit()


def delete_document(doc_id_or_filename: str) -> Optional[str]:
    """Delete document and its chunks by ID or filename. Returns deleted doc_id or None."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, filename FROM documents WHERE id = ? OR filename = ?",
            (doc_id_or_filename, doc_id_or_filename),
        )
        row = cursor.fetchone()
        if not row:
            return None
        doc_id = row["id"]
        cursor.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        return doc_id


def list_documents(collection: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return document records, optionally filtered by collection."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if collection:
            cursor.execute("SELECT * FROM documents WHERE collection = ? ORDER BY upload_time DESC", (collection,))
        else:
            cursor.execute("SELECT * FROM documents ORDER BY upload_time DESC")
        return [dict(row) for row in cursor.fetchall()]


def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_chunks(collection: Optional[str] = "default") -> List[Dict[str, Any]]:
    """Retrieve all chunks across documents, optionally filtered by collection."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if collection is not None:
            cursor.execute(
                """
                SELECT id, doc_id, filename, page_number, chunk_index, content, collection
                FROM chunks
                WHERE collection = ?
                ORDER BY filename, chunk_index
                """,
                (collection,)
            )
        else:
            cursor.execute(
                """
                SELECT id, doc_id, filename, page_number, chunk_index, content, collection
                FROM chunks
                ORDER BY filename, chunk_index
                """
            )
        return [dict(row) for row in cursor.fetchall()]
