import logging
import re
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.app.config import settings
from backend.app.embeddings import EmbeddingError, get_embedding_provider
from backend.app.llm import FALLBACK_MESSAGE, get_llm_provider
from backend.app.rate_limiter import rate_limit_chat
from backend.app.retriever import get_retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Employee question")
    history: List[ChatMessage] = Field(default=[], description="Previous conversation turns")


class CitationItem(BaseModel):
    n: int
    filename: str
    page: int
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[CitationItem]
    answerable: bool
    confidence: float
    search_query: Optional[str] = None
    gating_score: Optional[float] = None


@router.post("", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, _: None = Depends(rate_limit_chat)):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if len(question) > settings.MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Question exceeds maximum length of {settings.MAX_QUESTION_LENGTH} characters."
        )

    llm = get_llm_provider()
    embeddings = get_embedding_provider()
    retriever = get_retriever()

    # Step 1: Follow-up question rewrite (only run when chat history exists)
    history_dicts = [{"role": m.role, "content": m.content} for m in payload.history]
    if history_dicts:
        search_query = llm.rewrite_query(question, history_dicts)
        logger.info(f"Rewrote follow-up question: '{question}' -> '{search_query}'")
    else:
        search_query = question

    # Step 2: Embed query and retrieve hybrid chunks
    try:
        query_embedding = embeddings.embed_query(search_query)
    except EmbeddingError as e:
        logger.error(f"Embedding service failure during chat: {e}")
        raise HTTPException(
            status_code=503,
            detail="Embedding service temporarily unavailable. Please try again shortly."
        )
    except Exception as e:
        logger.error(f"Unexpected error generating query embedding: {type(e).__name__}")
        raise HTTPException(
            status_code=503,
            detail="Embedding service temporarily unavailable. Please try again shortly."
        )

    retrieval_res = retriever.retrieve(
        query=search_query,
        query_embedding=query_embedding,
        top_k=settings.TOP_K_RETRIEVAL,
        threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD,
    )

    gating_score = retrieval_res["gating_similarity"]
    chunks = retrieval_res["chunks"]

    # Step 3: Layer 1 Fallback Gating (below cosine similarity threshold or no chunks)
    if not retrieval_res["is_above_threshold"] or not chunks:
        logger.info(
            f"Layer 1 fallback triggered: gating_score={gating_score} < threshold={settings.RETRIEVAL_SIMILARITY_THRESHOLD}"
        )
        return ChatResponse(
            answer=FALLBACK_MESSAGE,
            citations=[],
            answerable=False,
            confidence=0.0,
            search_query=search_query,
            gating_score=gating_score,
        )

    # Step 4: Layer 2 LLM Grounding & Validation
    llm_output = llm.generate_chat_response(
        question=search_query,
        context_chunks=chunks,
        temperature=0.0
    )

    is_answerable = bool(llm_output.get("answerable", False))
    if not is_answerable or not llm_output.get("answer", "").strip():
        logger.info("Layer 2 fallback triggered: LLM determined question is not answerable from context.")
        return ChatResponse(
            answer=FALLBACK_MESSAGE,
            citations=[],
            answerable=False,
            confidence=round(float(llm_output.get("confidence", 0.0)), 2),
            search_query=search_query,
            gating_score=gating_score,
        )

    # Step 5: Format Citations
    raw_cited = llm_output.get("cited_indices", [])
    answer_text = llm_output.get("answer", "").strip()

    # If cited_indices is empty, scan answer text for [1], [2], etc.
    if not raw_cited:
        found_markers = re.findall(r"\[(\d+)\]", answer_text)
        raw_cited = [int(m) for m in found_markers]

    # Map indices to chunk excerpts
    citations: List[CitationItem] = []
    seen_indices = set()
    for idx_num in raw_cited:
        if idx_num in seen_indices:
            continue
        if 1 <= idx_num <= len(chunks):
            seen_indices.add(idx_num)
            c = chunks[idx_num - 1]
            raw_content = c.get("content", "").strip()
            # Snippet of 220 chars
            snippet = raw_content[:220] + ("..." if len(raw_content) > 220 else "")
            citations.append(
                CitationItem(
                    n=idx_num,
                    filename=c.get("filename", "document"),
                    page=int(c.get("page_number", 1)),
                    snippet=snippet,
                )
            )

    # Fallback if no citation markers were matched but answer is valid
    if not citations and len(chunks) > 0:
        c = chunks[0]
        snippet = c.get("content", "").strip()[:220] + "..."
        citations.append(
            CitationItem(
                n=1,
                filename=c.get("filename", "document"),
                page=int(c.get("page_number", 1)),
                snippet=snippet,
            )
        )

    confidence = round(float(llm_output.get("confidence", 0.95)), 2)

    return ChatResponse(
        answer=answer_text,
        citations=citations,
        answerable=True,
        confidence=confidence,
        search_query=search_query,
        gating_score=gating_score,
    )
