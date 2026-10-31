import logging
import re
from typing import Any, Dict, List, Optional
from rank_bm25 import BM25Okapi
from backend.app.db import get_all_chunks

logger = logging.getLogger(__name__)


def tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokenization for BM25."""
    return re.findall(r'\b[a-zA-Z0-9_]+\b', text.lower())


class BM25Store:
    def __init__(self, collection: str = "default"):
        self.collection = collection
        self.bm25: Optional[BM25Okapi] = None
        self.chunks: List[Dict[str, Any]] = []
        # Automatically populate from SQLite on initialization
        self.rebuild()

    def rebuild(self) -> None:
        """
        Rebuilds the BM25 index in memory from chunks stored in SQLite for this collection.
        Must be called on startup and after every document upload or delete.
        """
        self.chunks = get_all_chunks(collection=self.collection)
        if not self.chunks:
            self.bm25 = None
            logger.info(f"BM25 index cleared for collection '{self.collection}' (no chunks present).")
            return

        corpus = [tokenize(c["content"]) for c in self.chunks]
        self.bm25 = BM25Okapi(corpus)
        logger.info(f"Rebuilt BM25 index for collection '{self.collection}' with {len(self.chunks)} chunks.")

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search BM25 index. Returns top_k chunks with their BM25 score.
        """
        if self.bm25 is None or not self.chunks:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        max_score = float(max(scores)) if len(scores) > 0 and max(scores) > 0 else 1.0

        # Pair scores with chunks
        scored_chunks = []
        for idx, score in enumerate(scores):
            if score > 0:
                chunk = dict(self.chunks[idx])
                chunk["bm25_score"] = float(score)
                chunk["bm25_normalized"] = float(score / max_score)
                scored_chunks.append(chunk)

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x["bm25_score"], reverse=True)
        return scored_chunks[:top_k]


_bm25_instances: Dict[str, BM25Store] = {}


def get_bm25_store(collection: str = "default") -> BM25Store:
    global _bm25_instances
    if collection not in _bm25_instances:
        _bm25_instances[collection] = BM25Store(collection=collection)
    return _bm25_instances[collection]
