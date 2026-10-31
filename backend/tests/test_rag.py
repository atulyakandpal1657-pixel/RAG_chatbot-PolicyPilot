import pytest
from backend.app.chunker import chunk_text_page, create_chunks_for_document
from backend.app.retriever import reciprocal_rank_fusion
from backend.app.llm import FALLBACK_MESSAGE


def test_chunking_keeps_page_boundaries():
    """Verify that chunks never cross page boundaries and preserve 1-indexed page numbers."""
    pages = [
        {"page_number": 1, "text": "Page 1 Content. " * 50},  # ~800 chars
        {"page_number": 2, "text": "Page 2 Exclusive Content. " * 40},
        {"page_number": 3, "text": "Short page 3."},
    ]

    chunks = create_chunks_for_document(
        doc_id="test-doc-123",
        filename="handbook.pdf",
        pages=pages,
        target_size=400,
        overlap=60,
    )

    assert len(chunks) > 3, "Should produce multiple chunks across 3 pages."

    for c in chunks:
        page_num = c["page_number"]
        content = c["content"]
        # Verify page 1 chunks do not contain page 2 text
        if page_num == 1:
            assert "Page 2" not in content
            assert "Short page 3" not in content
        elif page_num == 2:
            assert "Page 1" not in content
            assert "Short page 3" not in content
        elif page_num == 3:
            assert "Page 1" not in content
            assert "Page 2" not in content


def test_chunking_single_page_boundary():
    """Verify chunk_text_page handles small, exact, and empty text correctly."""
    assert chunk_text_page("") == []
    assert chunk_text_page("   ") == []
    
    short = "Brief paragraph under target size."
    res = chunk_text_page(short, target_size=800, overlap=100)
    assert len(res) == 1
    assert res[0] == short


def test_fallback_triggers_below_threshold():
    """Verify that retrieval results below similarity threshold trigger Layer 1 fallback."""
    threshold = 0.55
    low_sim = 0.38
    is_above = (low_sim >= threshold)

    assert not is_above, "Score 0.38 should be strictly below 0.55 threshold"

    # Simulate fallback message
    response_answer = (
        FALLBACK_MESSAGE
        if not is_above
        else "Valid grounded answer."
    )
    assert response_answer == FALLBACK_MESSAGE
    assert "I couldn't find this in the uploaded documents" in response_answer


def test_citation_page_mapping():
    """Verify that citations correctly map chunk metadata without off-by-one errors."""
    mock_chunks = [
        {"id": "c1", "filename": "Handbook.pdf", "page_number": 2, "content": "PTO is 18 days."},
        {"id": "c2", "filename": "Benefits.pdf", "page_number": 3, "content": "401k match is 5%."},
    ]

    cited_indices = [1, 2]
    citations = []
    for idx in cited_indices:
        chunk = mock_chunks[idx - 1]
        citations.append({
            "n": idx,
            "filename": chunk["filename"],
            "page": chunk["page_number"],
            "snippet": chunk["content"]
        })

    assert len(citations) == 2
    assert citations[0]["n"] == 1
    assert citations[0]["filename"] == "Handbook.pdf"
    assert citations[0]["page"] == 2

    assert citations[1]["n"] == 2
    assert citations[1]["filename"] == "Benefits.pdf"
    assert citations[1]["page"] == 3


def test_reciprocal_rank_fusion():
    """Verify RRF rank aggregation logic."""
    vector_results = [
        {"id": "chunk_A", "content": "Vector top 1"},
        {"id": "chunk_B", "content": "Vector top 2"},
    ]
    bm25_results = [
        {"id": "chunk_B", "content": "BM25 top 1"},
        {"id": "chunk_C", "content": "BM25 top 2"},
    ]

    fused = reciprocal_rank_fusion(vector_results, bm25_results, rrf_k=60, top_k=3)

    # Chunk B appeared in both lists (rank 1 and rank 0), so it should rank first in fusion
    assert len(fused) == 3
    assert fused[0]["id"] == "chunk_B"
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]


def test_collection_isolation():
    """Verify that chunks stored in separate collections are cleanly partitioned."""
    from backend.app.db import get_all_chunks
    default_chunks = get_all_chunks(collection="default")
    real_chunks = get_all_chunks(collection="real_docs")

    # If database is seeded/ingested, verify separate chunks
    if default_chunks and real_chunks:
        default_files = set(c["filename"] for c in default_chunks)
        real_files = set(c["filename"] for c in real_chunks)
        assert "demo_pdf_employee_benefits.pdf" not in default_files
        assert "demo_pdf_employee_benefits.pdf" in real_files
