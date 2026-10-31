import logging
from typing import Any, Dict, List, Optional, Tuple
from backend.app.config import settings
from backend.app.vector_store import get_vector_store
from backend.app.bm25_store import get_bm25_store

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    rrf_k: int = 60,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Combines ranked lists from vector search and BM25 using Reciprocal Rank Fusion.
    RRF score = sum( 1.0 / (rrf_k + rank_i + 1) )
    """
    chunk_map: Dict[str, Dict[str, Any]] = {}
    rrf_scores: Dict[str, float] = {}

    # Accumulate vector ranks
    for rank, item in enumerate(vector_results):
        cid = item["id"]
        chunk_map[cid] = item
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank + 1))

    # Accumulate BM25 ranks
    for rank, item in enumerate(bm25_results):
        cid = item["id"]
        if cid not in chunk_map:
            chunk_map[cid] = item
        else:
            # Merge in bm25 metrics
            chunk_map[cid]["bm25_score"] = item.get("bm25_score", 0.0)
            chunk_map[cid]["bm25_normalized"] = item.get("bm25_normalized", 0.0)
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank + 1))

    # Sort chunks by RRF score descending
    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    final_chunks = []
    for cid in sorted_chunk_ids[:top_k]:
        chunk = dict(chunk_map[cid])
        chunk["rrf_score"] = float(rrf_scores[cid])
        final_chunks.append(chunk)

    return final_chunks


class HybridRetriever:
    def __init__(self, collection: str = "default", chroma_collection: Optional[str] = None):
        self.collection = collection
        chroma_name = chroma_collection or (
            "policypilot_real_docs" if collection == "real_docs" else "policypilot_chunks"
        )
        self.vector_store = get_vector_store(chroma_name)
        self.bm25_store = get_bm25_store(collection)

    def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.55
    ) -> Dict[str, Any]:
        """
        Executes hybrid retrieval:
        1. Vector search (top 15)
        2. BM25 search (top 15)
        3. Raw similarity threshold gating (best chunk vector cosine similarity)
        4. Reciprocal Rank Fusion (RRF) for top-k ordering
        """
        # Retrieve wide candidate pool (top 20) before RRF fusion
        candidate_k = max(20, top_k * 4)

        vector_results = self.vector_store.query(query_embedding, top_k=candidate_k)
        bm25_results = self.bm25_store.search(query, top_k=candidate_k)

        # Best vector cosine similarity
        best_vector_sim = (
            max([c.get("cosine_similarity", 0.0) for c in vector_results])
            if vector_results else 0.0
        )
        
        # Best BM25 normalized score (0.0 to 1.0)
        best_bm25_norm = (
            max([c.get("bm25_normalized", 0.0) for c in bm25_results])
            if bm25_results else 0.0
        )

        # Combined gating relevance: primarily vector similarity with optional keyword boost
        # If strong keyword match exists, it boosts confidence slightly
        gating_similarity = best_vector_sim
        if best_bm25_norm > 0.4:
            gating_similarity = max(best_vector_sim, 0.85 * best_vector_sim + 0.15 * best_bm25_norm)

        is_above_threshold = (gating_similarity >= threshold)

        fused_chunks = reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            rrf_k=settings.RRF_K,
            top_k=top_k
        )

        return {
            "chunks": fused_chunks,
            "gating_similarity": round(float(gating_similarity), 4),
            "best_vector_similarity": round(float(best_vector_sim), 4),
            "best_bm25_normalized": round(float(best_bm25_norm), 4),
            "is_above_threshold": is_above_threshold,
            "threshold": threshold,
        }


_retriever_instances: Dict[str, HybridRetriever] = {}


def get_retriever(collection: str = "default") -> HybridRetriever:
    global _retriever_instances
    if collection not in _retriever_instances:
        _retriever_instances[collection] = HybridRetriever(collection=collection)
    return _retriever_instances[collection]
