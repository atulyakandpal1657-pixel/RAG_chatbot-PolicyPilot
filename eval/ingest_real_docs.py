import logging
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.bm25_store import get_bm25_store
from backend.app.chunker import create_chunks_for_document
from backend.app.db import (
    init_db,
    save_chunks,
    update_document_status,
    upsert_document,
)
from backend.app.embeddings import get_embedding_provider
from backend.app.parser import parse_document
from backend.app.vector_store import get_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest_real_docs")

REAL_COLLECTION_CHROMA = "policypilot_real_docs"
REAL_COLLECTION_SQLITE = "real_docs"


def ingest_real_docs():
    init_db()
    real_docs_dir = PROJECT_ROOT / "eval" / "real_docs"
    pdf_path = real_docs_dir / "demo_pdf_employee_benefits.pdf"

    if not pdf_path.exists():
        raise FileNotFoundError(f"Real document not found: {pdf_path}")

    filename = pdf_path.name
    content = pdf_path.read_bytes()
    file_size = len(content)

    print(f"Parsing '{filename}' ({file_size} bytes)...")
    pages = parse_document(content, filename)
    page_count = len(pages)
    print(f"Extracted {page_count} pages.")

    doc_id = upsert_document(
        filename=filename,
        page_count=page_count,
        chunk_count=0,
        file_size=file_size,
        status="processing",
        collection=REAL_COLLECTION_SQLITE,
    )

    vector_store = get_vector_store(REAL_COLLECTION_CHROMA)
    vector_store.delete_by_filename(filename)

    chunks = create_chunks_for_document(
        doc_id=doc_id,
        filename=filename,
        pages=pages,
        target_size=800,
        overlap=120,
    )
    print(f"Created {len(chunks)} chunks across {page_count} pages.")

    embeddings_provider = get_embedding_provider()
    chunk_texts = [c["content"] for c in chunks]
    print(f"Generating embeddings for {len(chunk_texts)} chunks using {embeddings_provider.__class__.__name__}...")
    embeddings = embeddings_provider.embed_texts(chunk_texts)

    print(f"Storing vectors in ChromaDB collection '{REAL_COLLECTION_CHROMA}'...")
    vector_store.add_chunks(chunks, embeddings)

    print(f"Saving chunks to SQLite with collection='{REAL_COLLECTION_SQLITE}'...")
    save_chunks(doc_id, chunks, collection=REAL_COLLECTION_SQLITE)

    update_document_status(doc_id, len(chunks), "ready")

    print(f"Rebuilding BM25 index for collection '{REAL_COLLECTION_SQLITE}'...")
    bm25 = get_bm25_store(REAL_COLLECTION_SQLITE)
    bm25.rebuild()

    print("\nIngestion complete:")
    print(f"  • Filename: {filename}")
    print(f"  • Pages: {page_count}")
    print(f"  • Chunks: {len(chunks)}")
    print(f"  • Chroma Collection: {REAL_COLLECTION_CHROMA} (Total count: {vector_store.collection.count()})")
    print(f"  • BM25 Index: {len(bm25.chunks)} chunks in '{REAL_COLLECTION_SQLITE}'\n")


if __name__ == "__main__":
    ingest_real_docs()

