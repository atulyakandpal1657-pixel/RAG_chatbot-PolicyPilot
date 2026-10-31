import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = (
    "I couldn't find this in the uploaded documents. "
    "Try rephrasing, or contact HR directly."
)

SYSTEM_PROMPT = """You are PolicyPilot, an AI HR Policy assistant.
You answer employee questions strictly and exclusively using the provided policy excerpts.

RULES:
1. Ground your answer ONLY in the provided numbered excerpts [1], [2], etc.
2. Never extrapolate, speculate, or introduce facts from outside the excerpts.
3. Every factual claim MUST be followed by its citation marker in brackets, e.g., [1], [2].
4. If the excerpts do NOT provide enough information to definitively answer the user's question, set "answerable" to false. Do not guess.
5. You must return a strict JSON object with this exact schema:
{
  "answerable": true | false,
  "confidence": 0.0 to 1.0,
  "answer": "Concise answer with citations [1], [2]...",
  "cited_indices": [1, 2] // List of integer numbers corresponding to excerpts cited in the answer
}

If "answerable" is false, leave "answer" as empty string "" and "cited_indices" as [].
"""

REWRITE_PROMPT = """You are a conversational query rewriter for an HR policy search system.
Given the previous conversation turns and the user's latest follow-up question, rewrite the question into a standalone, self-contained search query.
Preserve all specific entities, nouns, and intent. Do NOT answer the question. Only output the rewritten question string with no extra text or quotes.

Conversation history:
{history_text}

User follow-up question:
{question}

Standalone query:"""


class LLMProvider(ABC):
    @abstractmethod
    def generate_chat_response(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """Generate structured answer with citations."""
        pass

    @abstractmethod
    def rewrite_query(self, question: str, history: List[Dict[str, str]]) -> str:
        """Rewrite follow-up question into standalone query using conversation history."""
        pass


def _build_context_prompt(chunks: List[Dict[str, Any]]) -> str:
    parts = []
    for idx, c in enumerate(chunks, 1):
        filename = c.get("filename", "document")
        page = c.get("page_number", 1)
        content = c.get("content", "").strip()
        parts.append(f"[{idx}] Document: {filename} (Page {page})\n{content}\n")
    return "\n".join(parts)


def _clean_json_output(raw_text: str) -> Dict[str, Any]:
    text = raw_text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
        text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        # Fallback regex extraction of JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return {"answerable": False, "confidence": 0.0, "answer": "", "cited_indices": []}


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-3.8-flash"):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate_chat_response(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        from google.genai import types

        context_str = _build_context_prompt(context_chunks)
        user_message = (
            f"CONTEXT POLICY EXCERPTS:\n{context_str}\n\n"
            f"EMPLOYEE QUESTION: {question}\n\n"
            "Produce the JSON response adhering strictly to the system instructions."
        )

        candidate_models = [self.model_name]
        configured_fallbacks = [m.strip() for m in settings.GEMINI_FALLBACK_MODELS.split(",") if m.strip()]
        for fallback in configured_fallbacks:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        last_error = None
        retries = 0
        retry_delay_ms = 0.0
        t_gen_start = time.perf_counter()

        for candidate in candidate_models:
            try:
                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=temperature,
                    response_mime_type="application/json"
                )
                resp = self.client.models.generate_content(
                    model=candidate,
                    contents=user_message,
                    config=config
                )
                raw_text = resp.text or "{}"
                parsed = _clean_json_output(raw_text)
                gen_total = (time.perf_counter() - t_gen_start) * 1000.0
                parsed["model_used"] = candidate
                parsed["generation_ms"] = round(max(0.0, gen_total - retry_delay_ms), 2)
                parsed["retry_count"] = retries
                parsed["retry_delay_ms"] = round(retry_delay_ms, 2)
                return parsed
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "PerDay" in err_msg or "per day" in err_msg:
                    logger.warning(f"Daily quota reached on {candidate}, switching immediately to next candidate...")
                    continue
                elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    logger.info(f"Rate limit hit on {candidate}, sleeping 3s and retrying...")
                    retries += 1
                    retry_delay_ms += 3000.0
                    time.sleep(3.0)
                    try:
                        resp = self.client.models.generate_content(
                            model=candidate,
                            contents=user_message,
                            config=config
                        )
                        raw_text = resp.text or "{}"
                        res = _clean_json_output(raw_text)
                        gen_total = (time.perf_counter() - t_gen_start) * 1000.0
                        res["model_used"] = candidate
                        res["generation_ms"] = round(max(0.0, gen_total - retry_delay_ms), 2)
                        res["retry_count"] = retries
                        res["retry_delay_ms"] = round(retry_delay_ms, 2)
                        return res
                    except Exception as retry_err:
                        last_error = retry_err
                        logger.warning(f"Retry on {candidate} failed: {retry_err}")
                else:
                    logger.warning(f"Model {candidate} failed ({e}), trying next candidate...")

        logger.error(f"All Gemini candidate models failed: {last_error}")
        gen_total = (time.perf_counter() - t_gen_start) * 1000.0
        return {
            "answerable": False,
            "confidence": 0.0,
            "answer": "",
            "cited_indices": [],
            "model_used": None,
            "generation_ms": round(max(0.0, gen_total - retry_delay_ms), 2),
            "retry_count": retries,
            "retry_delay_ms": round(retry_delay_ms, 2),
        }

    def rewrite_query(self, question: str, history: List[Dict[str, str]]) -> str:
        history_lines = []
        for turn in history[-4:]:  # Last 4 turns
            role = turn.get("role", "user")
            content = turn.get("content", "").strip()
            history_lines.append(f"{role.capitalize()}: {content}")
        history_text = "\n".join(history_lines)

        prompt = REWRITE_PROMPT.format(history_text=history_text, question=question)
        candidate_models = [self.model_name]
        for fallback in [m.strip() for m in settings.GEMINI_FALLBACK_MODELS.split(",") if m.strip()]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        for candidate in candidate_models:
            try:
                resp = self.client.models.generate_content(
                    model=candidate,
                    contents=prompt
                )
                rewritten = resp.text.strip() if resp.text else question
                return rewritten if len(rewritten) > 2 else question
            except Exception as e:
                logger.warning(f"Query rewrite failed on {candidate}: {e}, trying next candidate...")
        return question


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def generate_chat_response(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        context_str = _build_context_prompt(context_chunks)
        user_message = (
            f"CONTEXT POLICY EXCERPTS:\n{context_str}\n\n"
            f"EMPLOYEE QUESTION: {question}\n\n"
            "Produce the JSON response adhering strictly to the system instructions."
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            raw = resp.choices[0].message.content or "{}"
            return _clean_json_output(raw)
        except Exception as e:
            logger.error(f"OpenAI LLM generation failed: {e}")
            return {"answerable": False, "confidence": 0.0, "answer": "", "cited_indices": []}

    def rewrite_query(self, question: str, history: List[Dict[str, str]]) -> str:
        history_lines = []
        for turn in history[-4:]:
            role = turn.get("role", "user")
            content = turn.get("content", "").strip()
            history_lines.append(f"{role.capitalize()}: {content}")
        history_text = "\n".join(history_lines)

        prompt = REWRITE_PROMPT.format(history_text=history_text, question=question)
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            text = resp.choices[0].message.content
            return text.strip() if text else question
        except Exception as e:
            logger.warning(f"OpenAI query rewrite failed: {e}")
            return question


class AnthropicLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "claude-3-5-haiku-20241022"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = model_name

    def generate_chat_response(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        context_str = _build_context_prompt(context_chunks)
        user_message = (
            f"CONTEXT POLICY EXCERPTS:\n{context_str}\n\n"
            f"EMPLOYEE QUESTION: {question}\n\n"
            "Produce the JSON response adhering strictly to the system instructions."
        )

        try:
            resp = self.client.messages.create(
                model=self.model_name,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
                temperature=temperature,
                max_tokens=1000
            )
            raw = resp.content[0].text if resp.content else "{}"
            return _clean_json_output(raw)
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return {"answerable": False, "confidence": 0.0, "answer": "", "cited_indices": []}

    def rewrite_query(self, question: str, history: List[Dict[str, str]]) -> str:
        history_lines = [f"{t.get('role', 'user')}: {t.get('content', '')}" for t in history[-4:]]
        prompt = REWRITE_PROMPT.format(history_text="\n".join(history_lines), question=question)
        try:
            resp = self.client.messages.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200
            )
            text = resp.content[0].text
            return text.strip() if text else question
        except Exception:
            return question


def get_llm_provider() -> LLMProvider:
    provider = settings.LLM_PROVIDER.lower().strip()
    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMProvider(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.OPENAI_LLM_MODEL
        )
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicLLMProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model_name=settings.ANTHROPIC_LLM_MODEL
        )
    else:
        return GeminiLLMProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_LLM_MODEL
        )
