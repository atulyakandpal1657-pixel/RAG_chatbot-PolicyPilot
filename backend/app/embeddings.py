import logging
from abc import ABC, abstractmethod
from typing import List
from backend.app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass


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
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                result = self.client.models.embed_content(
                    model=self.model_name,
                    contents=batch
                )
                if hasattr(result, "embeddings") and result.embeddings:
                    for emb in result.embeddings:
                        embeddings.append(list(emb.values))
                else:
                    raise EmbeddingError("No embeddings returned in batch response")
            except Exception as e:
                logger.warning(f"Batch embed failed, attempting item-by-item: {type(e).__name__}")
                for t in batch:
                    try:
                        res = self.client.models.embed_content(
                            model=self.model_name,
                            contents=t
                        )
                        embeddings.append(list(res.embeddings[0].values))
                    except Exception as err:
                        logger.error(f"Gemini text embedding failed: {type(err).__name__}")
                        raise EmbeddingError(f"Failed to generate text embeddings: {type(err).__name__}") from err
        return embeddings

    def embed_query(self, query: str) -> List[float]:
        try:
            res = self.client.models.embed_content(
                model=self.model_name,
                contents=query
            )
            return list(res.embeddings[0].values)
        except Exception as e:
            logger.error(f"Gemini query embedding failed: {type(e).__name__}")
            raise EmbeddingError(f"Failed to generate query embedding: {type(e).__name__}") from e


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embedding Provider."""

    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            resp = self.client.embeddings.create(input=texts, model=self.model_name)
            return [list(item.embedding) for item in resp.data]
        except Exception as e:
            logger.error(f"OpenAI text embedding failed: {type(e).__name__}")
            raise EmbeddingError(f"Failed to generate text embeddings with OpenAI: {type(e).__name__}") from e

    def embed_query(self, query: str) -> List[float]:
        try:
            resp = self.client.embeddings.create(input=[query], model=self.model_name)
            return list(resp.data[0].embedding)
        except Exception as e:
            logger.error(f"OpenAI query embedding failed: {type(e).__name__}")
            raise EmbeddingError(f"Failed to generate query embedding with OpenAI: {type(e).__name__}") from e


def get_embedding_provider() -> EmbeddingProvider:
    """Factory returning configured embedding provider."""
    provider_name = settings.EMBEDDINGS_PROVIDER.lower().strip()
    if provider_name == "openai" and settings.OPENAI_API_KEY:
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_EMBEDDING_MODEL
        )
    else:
        return GeminiEmbeddingProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_EMBEDDING_MODEL
        )
