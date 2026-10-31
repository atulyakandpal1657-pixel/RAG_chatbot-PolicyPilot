import hashlib
import logging
import math
from abc import ABC, abstractmethod
from typing import List
from backend.app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract interface for embedding generation."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of text strings into vector representations."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Embed a single search query."""
        pass


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini Embeddings using Google GenAI SDK."""

    def __init__(self, api_key: str, model_name: str = "gemini-embedding-001"):
        from google import genai

        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings: List[List[float]] = []
        # Process in batches of 10 to avoid payload limits
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                # First try batch embed
                result = self.client.models.embed_content(
                    model=self.model_name,
                    contents=batch
                )
                if hasattr(result, "embeddings") and result.embeddings:
                    for emb in result.embeddings:
                        embeddings.append(list(emb.values))
                else:
                    raise ValueError("No embeddings returned in batch")
            except Exception as e:
                logger.warning(f"Batch embed failed, falling back to item-by-item: {e}")
                for t in batch:
                    try:
                        res = self.client.models.embed_content(
                            model=self.model_name,
                            contents=t
                        )
                        embeddings.append(list(res.embeddings[0].values))
                    except Exception as err:
                        logger.error(f"Failed to embed single text with Gemini: {err}")
                        embeddings.append(self._fallback_vector(t, 768))
        return embeddings

    def embed_query(self, query: str) -> List[float]:
        try:
            res = self.client.models.embed_content(
                model=self.model_name,
                contents=query
            )
            return list(res.embeddings[0].values)
        except Exception as e:
            logger.error(f"Gemini query embedding failed: {e}")
            return self._fallback_vector(query, 768)

    @staticmethod
    def _fallback_vector(text: str, dim: int = 768) -> List[float]:
        # Deterministic fallback vector if API fails
        val = [0.0] * dim
        h = hashlib.sha256(text.encode("utf-8")).digest()
        for idx in range(min(dim, len(h))):
            val[idx] = float(h[idx]) / 255.0
        norm = math.sqrt(sum(x * x for x in val)) or 1.0
        return [x / norm for x in val]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embedding Provider."""

    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        resp = self.client.embeddings.create(input=texts, model=self.model_name)
        return [list(item.embedding) for item in resp.data]

    def embed_query(self, query: str) -> List[float]:
        resp = self.client.embeddings.create(input=[query], model=self.model_name)
        return list(resp.data[0].embedding)


def get_embedding_provider() -> EmbeddingProvider:
    """Factory returning configured embedding provider."""
    provider_name = settings.EMBEDDINGS_PROVIDER.lower().strip()
    if provider_name == "openai" and settings.OPENAI_API_KEY:
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_EMBEDDING_MODEL
        )
    else:
        # Default to Gemini
        return GeminiEmbeddingProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_EMBEDDING_MODEL
        )
