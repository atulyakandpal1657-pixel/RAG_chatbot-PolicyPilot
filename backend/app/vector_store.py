import logging
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION_NAME = "policypilot_chunks"
COLLECTION_NAME = DEFAULT_COLLECTION_NAME


class VectorStore:
    def __init__(self, collection_name: str = DEFAULT_COLLECTION_NAME):
        self.collection_name = collection_name
        self.persist_dir = str(settings.chroma_full_path)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        """Add or upsert chunks and their embeddings into ChromaDB."""
        if not chunks or not embeddings:
            return

        ids = [c["id"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [
            {
                "doc_id": str(c["doc_id"]),
                "filename": str(c["filename"]),
                "page_number": int(c["page_number"]),
                "chunk_index": int(c["chunk_index"])
            }
            for c in chunks
        ]

        # Upsert in batches of 100 to avoid limits
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            self.collection.upsert(
                ids=ids[i:i + batch_size],
                embeddings=embeddings[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size]
            )
        logger.info(f"Upserted {len(chunks)} chunks into ChromaDB collection '{self.collection_name}'.")

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Deletes all chunks belonging to doc_id."""
        try:
            self.collection.delete(where={"doc_id": doc_id})
            logger.info(f"Deleted vector chunks for doc_id {doc_id} from collection '{self.collection_name}'.")
        except Exception as e:
            logger.warning(f"Error deleting chunks for doc_id {doc_id}: {e}")

    def delete_by_filename(self, filename: str) -> None:
        """Deletes all chunks belonging to filename."""
        try:
            self.collection.delete(where={"filename": filename})
            logger.info(f"Deleted vector chunks for filename {filename} from collection '{self.collection_name}'.")
        except Exception as e:
            logger.warning(f"Error deleting chunks for filename {filename}: {e}")

    def query(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Query top_k most similar chunks.
        Calculates raw cosine similarity = (1.0 - distance).
        """
        count = self.collection.count()
        if count == 0:
            return []

        n_results = min(top_k, count)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        formatted_results = []
        if results and results["ids"] and len(results["ids"][0]) > 0:
            ids = results["ids"][0]
            docs = results["documents"][0] if results["documents"] else []
            metas = results["metadatas"][0] if results["metadatas"] else []
            distances = results["distances"][0] if results["distances"] else []

            for idx in range(len(ids)):
                # In cosine space, distance is 1 - cosine_sim (in range [0, 2])
                dist = distances[idx] if idx < len(distances) else 1.0
                # Clamp similarity to [0.0, 1.0]
                similarity = max(0.0, min(1.0, 1.0 - dist))

                meta = metas[idx] if idx < len(metas) else {}
                formatted_results.append({
                    "id": ids[idx],
                    "content": docs[idx] if idx < len(docs) else "",
                    "doc_id": meta.get("doc_id", ""),
                    "filename": meta.get("filename", ""),
                    "page_number": int(meta.get("page_number", 1)),
                    "chunk_index": int(meta.get("chunk_index", 0)),
                    "cosine_similarity": float(similarity),
                    "vector_distance": float(dist)
                })

        return formatted_results


_vector_store_instances: Dict[str, VectorStore] = {}


def get_vector_store(collection_name: str = DEFAULT_COLLECTION_NAME) -> VectorStore:
    global _vector_store_instances
    if collection_name not in _vector_store_instances:
        _vector_store_instances[collection_name] = VectorStore(collection_name=collection_name)
    return _vector_store_instances[collection_name]
