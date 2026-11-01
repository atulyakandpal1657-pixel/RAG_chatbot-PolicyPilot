import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.bm25_store import get_bm25_store
from backend.app.chunker import create_chunks_for_document
from backend.app.config import settings
from backend.app.db import get_all_chunks, init_db, list_documents, save_chunks, upsert_document, update_document_status
from backend.app.embeddings import get_embedding_provider
from backend.app.parser import parse_document
from backend.app.vector_store import get_vector_store
from scripts.generate_sample_docs import generate_all_sample_docs


def seed_database():
    print("=" * 60)
    print("PolicyPilot: Ingestion & Database Seeding")
    print("=" * 60)

    # 1. Initialize SQLite
    print("[1/5] Initializing SQLite schema...")
    init_db()

    # 2. Check / Generate Sample Documents
    # Resolve relative to this file so seed.py works from any CWD
    sample_dir = PROJECT_ROOT / "sample_docs"
    pdf_files = list(sample_dir.glob("*.pdf")) if sample_dir.exists() else []
    if len(pdf_files) < 3:
        print("[2/5] Generating fresh sample PDFs for Northwind Labs...")
        generate_all_sample_docs()
        pdf_files = list(sample_dir.glob("*.pdf"))
    else:
        print(f"[2/5] Found {len(pdf_files)} existing sample documents in sample_docs/.")

    # 3. Ingestion into ChromaDB & SQLite (idempotent: only if collection empty)
    existing_docs = list_documents(collection="default")
    force = "--force" in sys.argv
    if existing_docs and len(existing_docs) >= 3 and not force:
        print(f"[3/5] Collection 'default' already contains {len(existing_docs)} documents; skipping re-ingestion.")
        print("[4/5] Rebuilding in-memory BM25 index from SQLite chunks...")
        bm25_store = get_bm25_store()
        bm25_store.rebuild()
        print("\n" + "=" * 60)
        print("Database already seeded. Startup ready.")
        print("=" * 60)
        return

    print("[3/5] Parsing documents and generating vector embeddings...")
    vector_store = get_vector_store()
    embeddings_provider = get_embedding_provider()

    for pdf_path in sorted(pdf_files):
        filename = pdf_path.name
        print(f"\nProcessing '{filename}'...")
        content = pdf_path.read_bytes()
        file_size = len(content)

        # Parse into page-level text
        pages = parse_document(content, filename)
        print(f"  - Extracted {len(pages)} pages.")

        # Upsert document record in SQLite
        doc_id = upsert_document(
            filename=filename,
            page_count=len(pages),
            chunk_count=0,
            file_size=file_size,
            status="processing",
        )

        # Clear any prior vectors for this filename
        vector_store.delete_by_filename(filename)

        # Chunk respecting page boundaries
        chunks = create_chunks_for_document(
            doc_id=doc_id,
            filename=filename,
            pages=pages,
            target_size=800,
            overlap=120,
        )
        print(f"  - Generated {len(chunks)} page-bounded chunks.")

        # Embed chunk texts
        chunk_texts = [c["content"] for c in chunks]
        embeddings = embeddings_provider.embed_texts(chunk_texts)
        print(f"  - Generated {len(embeddings)} vector embeddings.")

        # Add to ChromaDB
        vector_store.add_chunks(chunks, embeddings)

        # Save to SQLite
        save_chunks(doc_id, chunks)

        # Finalize status
        update_document_status(doc_id, len(chunks), "ready")
        print(f"  - Document '{filename}' successfully ingested.")

    # 4. Rebuild BM25 Index
    print("\n[4/5] Rebuilding in-memory BM25 index from SQLite chunks...")
    bm25_store = get_bm25_store()
    bm25_store.rebuild()

    # 5. Summary
    docs = list_documents()
    total_chunks = len(get_all_chunks())
    print("\n" + "=" * 60)
    print("Seeding Complete!")
    print(f"Total Documents Ingested: {len(docs)}")
    print(f"Total Chunks in Vector & BM25 Store: {total_chunks}")
    print("=" * 60)


if __name__ == "__main__":
    seed_database()
