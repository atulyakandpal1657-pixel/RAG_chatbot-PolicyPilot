import argparse
import json
import logging
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from backend.app.embeddings import get_embedding_provider
from backend.app.llm import FALLBACK_MESSAGE, get_llm_provider
from backend.app.retriever import get_retriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eval_runner")

JUDGE_PROMPT_TEMPLATE = """You are an objective evaluation judge comparing an AI assistant's answer to a ground truth expected answer.

Question: {question}
Ground Truth: {expected_answer}
Assistant Answer: {actual_answer}

Evaluation Criteria:
1. Is the assistant's answer factually consistent with the ground truth?
2. Does it provide the specific numbers, dates, or core facts required?
3. Minor differences in phrasing are completely acceptable as long as the factual meaning is identical.

Respond ONLY with a JSON object:
{{
  "score": 1 or 0,
  "explanation": "Brief reasoning"
}}
"""


def wilson_score_interval(k: int, n: int, confidence: float = 0.95) -> Dict[str, float]:
    """Calculates Wilson score 95% confidence interval for a binomial proportion."""
    if n == 0:
        return {"lower": 0.0, "upper": 0.0}
    z = 1.95996  # 95%
    p = k / n
    denominator = 1.0 + (z**2) / n
    centre = (p + (z**2) / (2.0 * n)) / denominator
    spread = (z / denominator) * math.sqrt((p * (1.0 - p) / n) + (z**2) / (4.0 * (n**2)))
    lower = max(0.0, centre - spread)
    upper = min(1.0, centre + spread)
    return {"lower": round(lower * 100, 1), "upper": round(upper * 100, 1)}


def evaluate_with_llm_judge(llm, question: str, expected: str, actual: str) -> Tuple[int, float, str, int, float]:
    """
    Uses LLM-as-judge to score answer accuracy (1 or 0).
    Returns: (score, judge_latency_ms, judge_model_used, retries, retry_delay_ms)
    """
    if not actual or FALLBACK_MESSAGE in actual:
        return 0, 0.0, "deterministic_abstention", 0, 0.0

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        expected_answer=expected,
        actual_answer=actual
    )

    judge_model = getattr(settings, "GEMINI_JUDGE_MODEL", "gemini-flash-lite-latest")
    fallbacks = [m.strip() for m in getattr(settings, "GEMINI_FALLBACK_MODELS", "gemini-flash-lite-latest,gemini-3.6-flash,gemini-3.5-flash").split(",") if m.strip()]
    candidates = [judge_model] + [m for m in fallbacks if m != judge_model]

    t_start = time.perf_counter()
    retries = 0
    retry_delay_ms = 0.0

    for model_cand in candidates:
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json"
            )
            resp = llm.client.models.generate_content(
                model=model_cand,
                contents=prompt,
                config=config
            )
            data = json.loads(resp.text)
            judge_ms = (time.perf_counter() - t_start) * 1000.0
            return int(data.get("score", 0)), round(judge_ms, 2), model_cand, retries, retry_delay_ms
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                retries += 1
                retry_delay_ms += 5000.0
                time.sleep(5.0)
                try:
                    resp = llm.client.models.generate_content(
                        model=model_cand, contents=prompt, config=config
                    )
                    judge_ms = (time.perf_counter() - t_start) * 1000.0
                    return int(json.loads(resp.text).get("score", 0)), round(judge_ms, 2), model_cand, retries, retry_delay_ms
                except Exception:
                    pass
            continue

    # Semantic keyword/entity overlap check if API calls fail
    expected_words = set(re.findall(r'\b\w+\b', expected.lower()))
    actual_words = set(re.findall(r'\b\w+\b', actual.lower()))
    overlap = len(expected_words.intersection(actual_words)) / max(1, len(expected_words))
    judge_ms = (time.perf_counter() - t_start) * 1000.0
    return (1 if overlap > 0.45 else 0), round(judge_ms, 2), "heuristic_fallback", retries, retry_delay_ms


def run_pipeline(question: str, collection: str = "default") -> Dict[str, Any]:
    """Runs a single question end-to-end through the PolicyPilot RAG pipeline for a given collection."""
    llm = get_llm_provider()
    embeddings = get_embedding_provider()
    retriever = get_retriever(collection=collection)

    t_total_start = time.perf_counter()

    # 1. Retrieval Timing (Embedding query + Vector + BM25 + RRF)
    t_ret_start = time.perf_counter()
    query_embedding = embeddings.embed_query(question)
    ret_res = retriever.retrieve(
        query=question,
        query_embedding=query_embedding,
        top_k=settings.TOP_K_RETRIEVAL,
        threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD
    )
    retrieval_ms = (time.perf_counter() - t_ret_start) * 1000.0

    gating_score = ret_res["gating_similarity"]
    chunks = ret_res["chunks"]

    # Layer 1 Fallback check
    if not ret_res["is_above_threshold"] or not chunks:
        total_ms = (time.perf_counter() - t_total_start) * 1000.0
        return {
            "answer": FALLBACK_MESSAGE,
            "citations": [],
            "answerable": False,
            "gating_score": gating_score,
            "latency_ms": round(total_ms, 2),
            "retrieval_ms": round(retrieval_ms, 2),
            "generation_ms": 0.0,
            "retry_count": 0,
            "retry_delay_ms": 0.0,
            "fallback_layer": "layer_1_retrieval",
            "model_used": None
        }

    # Layer 2 LLM Grounding
    llm_out = llm.generate_chat_response(question=question, context_chunks=chunks, temperature=0.0)
    total_ms = (time.perf_counter() - t_total_start) * 1000.0

    generation_ms = llm_out.get("generation_ms", max(0.0, total_ms - retrieval_ms))
    retry_count = llm_out.get("retry_count", 0)
    retry_delay_ms = llm_out.get("retry_delay_ms", 0.0)
    model_used = llm_out.get("model_used")

    if not llm_out.get("answerable", False) or not llm_out.get("answer", "").strip():
        return {
            "answer": FALLBACK_MESSAGE,
            "citations": [],
            "answerable": False,
            "gating_score": gating_score,
            "latency_ms": round(total_ms, 2),
            "retrieval_ms": round(retrieval_ms, 2),
            "generation_ms": round(generation_ms, 2),
            "retry_count": retry_count,
            "retry_delay_ms": round(retry_delay_ms, 2),
            "fallback_layer": "layer_2_llm",
            "model_used": model_used
        }

    # Format citations
    raw_cited = llm_out.get("cited_indices", [])
    answer_text = llm_out.get("answer", "").strip()
    if not raw_cited:
        found_markers = re.findall(r"\[(\d+)\]", answer_text)
        raw_cited = [int(m) for m in found_markers]

    citations = []
    seen = set()
    for idx_num in raw_cited:
        if idx_num in seen:
            continue
        if 1 <= idx_num <= len(chunks):
            seen.add(idx_num)
            c = chunks[idx_num - 1]
            citations.append({
                "n": idx_num,
                "filename": c.get("filename", ""),
                "page": int(c.get("page_number", 1)),
                "snippet": c.get("content", "")[:200]
            })

    if not citations and len(chunks) > 0:
        c = chunks[0]
        citations.append({
            "n": 1,
            "filename": c.get("filename", ""),
            "page": int(c.get("page_number", 1)),
            "snippet": c.get("content", "")[:200]
        })

    return {
        "answer": answer_text,
        "citations": citations,
        "answerable": True,
        "confidence": float(llm_out.get("confidence", 0.95)),
        "gating_score": gating_score,
        "latency_ms": round(total_ms, 2),
        "retrieval_ms": round(retrieval_ms, 2),
        "generation_ms": round(generation_ms, 2),
        "retry_count": retry_count,
        "retry_delay_ms": round(retry_delay_ms, 2),
        "fallback_layer": None,
        "model_used": model_used
    }


def compute_split_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates accuracy, citation accuracy, fallback precision/recall, and Wilson 95% CIs."""
    total = len(results)
    if total == 0:
        return {}

    answerable_items = [r for r in results if r["is_answerable"]]
    unanswerable_items = [r for r in results if not r["is_answerable"]]

    # Answer accuracy on answerable
    correct_answers = sum(r["answer_correct"] for r in answerable_items)
    answer_acc = (correct_answers / len(answerable_items)) if answerable_items else 1.0

    # Citation accuracy on answerable
    correct_citations = sum(r["citation_correct"] for r in answerable_items)
    citation_acc = (correct_citations / len(answerable_items)) if answerable_items else 1.0

    # Fallback metrics on unanswerable
    true_abstentions = sum(1 for r in unanswerable_items if r["abstained"])
    fallback_recall = (true_abstentions / len(unanswerable_items)) if unanswerable_items else 1.0

    false_abstentions = sum(1 for r in answerable_items if r["abstained"])
    all_abstentions = true_abstentions + false_abstentions
    fallback_precision = (true_abstentions / all_abstentions) if all_abstentions > 0 else 1.0

    overall_score = (0.45 * answer_acc) + (0.35 * citation_acc) + (0.20 * fallback_recall)

    # Latencies
    avg_total_ms = sum(r["latency_ms"] for r in results) / total
    avg_retrieval_ms = sum(r.get("latency_breakdown", {}).get("retrieval_ms", 0.0) for r in results) / total
    avg_generation_ms = sum(r.get("latency_breakdown", {}).get("generation_ms", 0.0) for r in results) / total
    avg_retry_ms = sum(r.get("latency_breakdown", {}).get("retry_delay_ms", 0.0) for r in results) / total
    avg_judge_ms = sum(r.get("latency_breakdown", {}).get("judge_ms", 0.0) for r in results) / total

    # Confidence intervals
    ans_ci = wilson_score_interval(correct_answers, len(answerable_items))
    cit_ci = wilson_score_interval(correct_citations, len(answerable_items))
    fb_ci = wilson_score_interval(true_abstentions, len(unanswerable_items))

    return {
        "total_questions": total,
        "answerable_count": len(answerable_items),
        "unanswerable_count": len(unanswerable_items),
        "answer_accuracy": round(answer_acc * 100, 1),
        "answer_accuracy_ci": ans_ci,
        "citation_accuracy": round(citation_acc * 100, 1),
        "citation_accuracy_ci": cit_ci,
        "fallback_recall": round(fallback_recall * 100, 1),
        "fallback_recall_ci": fb_ci,
        "fallback_precision": round(fallback_precision * 100, 1),
        "false_abstentions": false_abstentions,
        "overall_score": round(overall_score * 100, 1),
        "avg_latency_ms": round(avg_total_ms, 1),
        "latency_breakdown_avg": {
            "retrieval_ms": round(avg_retrieval_ms, 1),
            "generation_ms": round(avg_generation_ms, 1),
            "retry_delay_ms": round(avg_retry_ms, 1),
            "judge_ms": round(avg_judge_ms, 1),
        }
    }


def diagnose_failure(record: Dict[str, Any]) -> str:
    """Provides an automated root-cause diagnosis for a failed evaluation record."""
    qid = record["id"]
    is_ans = record["is_answerable"]
    abstained = record["abstained"]
    actual = record["actual_answer"]
    expected = record["expected_answer"]
    citations = record.get("citations", [])
    gating = record.get("gating_score", 0.0)
    layer = record.get("fallback_layer")

    if not is_ans:
        if not abstained:
            return (
                f"False Positive (Failed to Abstain): Question {qid} was expected to trigger fallback, "
                f"but the system generated an answer (model {record.get('model_used')}). "
                f"Gating similarity score {gating} exceeded threshold {settings.RETRIEVAL_SIMILARITY_THRESHOLD}, "
                f"and Layer 2 grounding did not recognize out-of-scope/false-premise boundaries."
            )
        return "Passed: Correctly abstained."

    reasons = []
    if abstained:
        if layer == "layer_1_retrieval":
            reasons.append(
                f"False Abstention at Layer 1: Gating score {gating:.4f} fell below threshold "
                f"{settings.RETRIEVAL_SIMILARITY_THRESHOLD}."
            )
        elif layer == "layer_2_llm":
            reasons.append(
                f"False Abstention at Layer 2: Chunks passed retrieval gating ({gating:.4f} >= {settings.RETRIEVAL_SIMILARITY_THRESHOLD}), "
                f"but the generator LLM marked answerable=false or failed to extract the answer."
            )
        else:
            reasons.append("False Abstention: System returned fallback message instead of answering.")

    if record["answer_correct"] == 0 and not abstained:
        reasons.append(
            f"Factual Discrepancy: Expected '{expected}', but actual answer was: '{actual[:150]}...' "
            f"(LLM judge scored 0)."
        )

    if record["citation_correct"] == 0 and not abstained:
        exp_doc = record.get("expected_file")
        exp_p = record.get("expected_page")
        actual_cits = [f"{c.get('filename')} p.{c.get('page')}" for c in citations]
        reasons.append(
            f"Citation Mismatch: Expected {exp_doc} p.{exp_p}, but retrieved/cited: {', '.join(actual_cits) if actual_cits else 'None'}."
        )

    return " | ".join(reasons) if reasons else "Passed"


def run_evaluation(
    questions_path: Optional[str] = None,
    collection: str = "default",
    track: str = "synthetic"
):
    eval_dir = Path(__file__).resolve().parent

    if track == "real_v2":
        track_name = "Real-World Benchmark Track Pass 2 (real_questions_v2.json)"
        q_file = Path(questions_path) if questions_path else (eval_dir / "real_questions_v2.json")
        out_json = eval_dir / "real_results_v2.json"
        out_md = eval_dir / "real_results_v2.md"
        actual_collection = "real_docs"
    elif track == "real" or collection == "real_docs":
        track_name = "Real-World Benchmark (Public PDF Track v1)"
        q_file = Path(questions_path) if questions_path else (eval_dir / "real_questions.json")
        out_json = eval_dir / "real_results.json"
        out_md = eval_dir / "real_results.md"
        actual_collection = "real_docs"
    else:
        track_name = "Synthetic Benchmark (Northwind Labs Track)"
        q_file = Path(questions_path) if questions_path else (eval_dir / "questions.json")
        out_json = eval_dir / "results.json"
        out_md = eval_dir / "results.md"
        actual_collection = collection

    if not q_file.exists():
        if track == "synthetic":
            from eval.generate_questions import generate_questions_json
            generate_questions_json()
        else:
            raise FileNotFoundError(f"Questions file not found: {q_file}")

    from backend.app.bm25_store import get_bm25_store
    bm25 = get_bm25_store(actual_collection)
    bm25.rebuild()
    print(f"Rebuilt BM25 index with {len(bm25.chunks)} chunks for collection '{actual_collection}'.")

    questions = json.loads(q_file.read_text(encoding="utf-8"))
    llm = get_llm_provider()

    print(f"\n=======================================================")
    print(f"  Starting Evaluation: {track_name}")
    print(f"  Questions File: '{q_file.name}' | Collection: '{actual_collection}'")
    print(f"  Total Questions: {len(questions)} | Threshold: {settings.RETRIEVAL_SIMILARITY_THRESHOLD}")
    print(f"=======================================================\n")

    evaluated_records = []

    for i, q in enumerate(questions, 1):
        qid = q["id"]
        q_text = q["question"]
        is_ans = q["is_answerable"]
        split = q.get("split", "test")
        subtype = q.get("subtype", "standard")
        exp_ans = q.get("expected_answer", "")
        exp_file = q.get("source_filename")
        exp_page = q.get("source_page")

        print(f"[{i:02d}/{len(questions):02d}] ({split.upper()}) {q_text[:55]}...")
        result = run_pipeline(q_text, collection=actual_collection)

        actual_ans = result["answer"]
        abstained = not result["answerable"] or (FALLBACK_MESSAGE in actual_ans)
        citations = result.get("citations", [])

        # Judge evaluation & timing
        if is_ans:
            if abstained:
                ans_correct, judge_ms, judge_model, j_retries, j_retry_ms = 0, 0.0, "abstained_skip", 0, 0.0
            else:
                ans_correct, judge_ms, judge_model, j_retries, j_retry_ms = evaluate_with_llm_judge(
                    llm, q_text, exp_ans, actual_ans
                )
        else:
            ans_correct, judge_ms, judge_model, j_retries, j_retry_ms = (1 if abstained else 0), 0.0, "abstention_verified", 0, 0.0

        # Citation correctness
        if is_ans:
            cit_correct = 0
            for cit in citations:
                cit_file = cit.get("filename", "")
                cit_page = int(cit.get("page", -1))
                if (exp_file and exp_file.lower() in cit_file.lower()) and (exp_page == cit_page):
                    cit_correct = 1
                    break
        else:
            cit_correct = 1 if (len(citations) == 0 and abstained) else 0

        total_retries = result.get("retry_count", 0) + j_retries
        total_retry_delay = result.get("retry_delay_ms", 0.0) + j_retry_ms

        record = {
            "id": qid,
            "split": split,
            "subtype": subtype,
            "question": q_text,
            "is_answerable": is_ans,
            "expected_answer": exp_ans,
            "expected_file": exp_file,
            "expected_page": exp_page,
            "actual_answer": actual_ans,
            "citations": citations,
            "abstained": abstained,
            "answer_correct": ans_correct,
            "citation_correct": cit_correct,
            "gating_score": result.get("gating_score"),
            "latency_ms": result.get("latency_ms", 0.0),
            "latency_breakdown": {
                "retrieval_ms": result.get("retrieval_ms", 0.0),
                "generation_ms": result.get("generation_ms", 0.0),
                "retry_count": total_retries,
                "retry_delay_ms": total_retry_delay,
                "judge_ms": judge_ms,
                "pipeline_total_ms": result.get("latency_ms", 0.0),
                "eval_total_ms": round(result.get("latency_ms", 0.0) + judge_ms, 2)
            },
            "fallback_layer": result.get("fallback_layer"),
            "model_used": result.get("model_used"),
            "judge_model_used": judge_model,
        }
        record["diagnosis"] = diagnose_failure(record)
        evaluated_records.append(record)
        time.sleep(1.0)

    # Audit models
    gen_models = set(r.get("model_used") for r in evaluated_records if r.get("model_used"))
    print(f"\n[Model Audit] Generator models used: {gen_models}")

    dev_records = [r for r in evaluated_records if r["split"] == "dev"]
    test_records = [r for r in evaluated_records if r["split"] == "test"]

    dev_metrics = compute_split_metrics(dev_records) if dev_records else None
    test_metrics = compute_split_metrics(test_records) if test_records else None
    combined_metrics = compute_split_metrics(evaluated_records)

    timestamp = datetime.now(timezone.utc).isoformat()

    full_report = {
        "timestamp": timestamp,
        "track": track,
        "track_name": track_name,
        "collection": actual_collection,
        "combined": combined_metrics,
        "dev_split": dev_metrics,
        "test_split": test_metrics,
        "config": {
            "retrieval_threshold": settings.RETRIEVAL_SIMILARITY_THRESHOLD,
            "top_k": settings.TOP_K_RETRIEVAL,
            "llm_model": settings.GEMINI_LLM_MODEL,
            "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
        },
        "questions": evaluated_records,
    }

    out_json.write_text(json.dumps(full_report, indent=2), encoding="utf-8")
    print(f"\nSaved benchmark results to: {out_json}")

    md_content = generate_markdown_report(full_report)
    out_md.write_text(md_content, encoding="utf-8")
    print(f"Saved formatted markdown report to: {out_md}")

    # Console summary
    print("\n" + "=" * 78)
    print(f"               {track_name.upper()} SUMMARY")
    print("=" * 78)
    print(f"Overall Score:            {combined_metrics['overall_score']}%")
    print(f"Answer Accuracy:          {combined_metrics['answer_accuracy']}% [95% CI: {combined_metrics['answer_accuracy_ci']['lower']}% - {combined_metrics['answer_accuracy_ci']['upper']}%]")
    print(f"Citation Accuracy:        {combined_metrics['citation_accuracy']}% [95% CI: {combined_metrics['citation_accuracy_ci']['lower']}% - {combined_metrics['citation_accuracy_ci']['upper']}%]")
    print(f"Fallback Recall:          {combined_metrics['fallback_recall']}% [95% CI: {combined_metrics['fallback_recall_ci']['lower']}% - {combined_metrics['fallback_recall_ci']['upper']}%]")
    print(f"Fallback Precision:       {combined_metrics['fallback_precision']}%")
    print(f"False Abstentions:        {combined_metrics['false_abstentions']}")
    print(f"Avg Pipeline Latency:     {combined_metrics['avg_latency_ms']} ms")
    print(f"  • Retrieval:            {combined_metrics['latency_breakdown_avg']['retrieval_ms']} ms")
    print(f"  • Generation:           {combined_metrics['latency_breakdown_avg']['generation_ms']} ms")
    print(f"  • Retry/Backoff Delay:  {combined_metrics['latency_breakdown_avg']['retry_delay_ms']} ms")
    print(f"  • Judge Evaluation:     {combined_metrics['latency_breakdown_avg']['judge_ms']} ms")
    print("=" * 78)

    failed_records = [
        r for r in evaluated_records
        if (r["is_answerable"] and (r["answer_correct"] == 0 or r["citation_correct"] == 0))
        or (not r["is_answerable"] and not r["abstained"])
    ]

    if failed_records:
        print(f"\nFAILED QUESTIONS ({len(failed_records)} / {len(evaluated_records)}):")
        for f in failed_records:
            print(f"  • [ID {f['id']}] {f['question']}")
            print(f"    Diagnosis: {f['diagnosis']}")
    else:
        print(f"\nAll {len(evaluated_records)} questions PASSED successfully (100% precision & recall)!")
    print("=" * 78 + "\n")

    return full_report


def generate_markdown_report(report: Dict[str, Any]) -> str:
    combined = report["combined"]
    dev = report.get("dev_split")
    test = report.get("test_split")
    cfg = report["config"]
    records = report["questions"]
    track_title = report.get("track_name", "PolicyPilot Evaluation Benchmark Results")

    has_dev_test = (dev is not None and test is not None)

    md = f"""# {track_title}

*Run timestamp: {report['timestamp']}*  
*Collection: `{report.get('collection', 'default')}`*  
*Configuration: LLM=`{cfg['llm_model']}`, Embeddings=`{cfg['embedding_model']}`, Cosine Threshold=`{cfg['retrieval_threshold']}`, Top-K=`{cfg['top_k']}`*

---

## 1. Executive Summary Performance

"""
    if has_dev_test:
        md += f"""| Metric | Combined ({combined['total_questions']} Qs) | Dev Split ({dev['total_questions']} Qs) | Test Split ({test['total_questions']} Qs) | Wilson 95% CI (Combined) |
| :--- | :---: | :---: | :---: | :---: |
| **Overall Benchmark Score** | **{combined['overall_score']}%** | **{dev['overall_score']}%** | **{test['overall_score']}%** | — |
| **Answer Accuracy** (Answerable Qs) | {combined['answer_accuracy']}% | {dev['answer_accuracy']}% | {test['answer_accuracy']}% | [{combined['answer_accuracy_ci']['lower']}%, {combined['answer_accuracy_ci']['upper']}%] |
| **Citation Accuracy** (Exact Page Match) | {combined['citation_accuracy']}% | {dev['citation_accuracy']}% | {test['citation_accuracy']}% | [{combined['citation_accuracy_ci']['lower']}%, {combined['citation_accuracy_ci']['upper']}%] |
| **Fallback Recall** (Abstention Rate) | {combined['fallback_recall']}% | {dev['fallback_recall']}% | {test['fallback_recall']}% | [{combined['fallback_recall_ci']['lower']}%, {combined['fallback_recall_ci']['upper']}%] |
| **Fallback Precision** | {combined['fallback_precision']}% | {dev['fallback_precision']}% | {test['fallback_precision']}% | — |
| **False Abstentions** | {combined['false_abstentions']} | {dev['false_abstentions']} | {test['false_abstentions']} | — |
| **Average Pipeline Latency** | {combined['avg_latency_ms']} ms | {dev['avg_latency_ms']} ms | {test['avg_latency_ms']} ms | Retrieval: {combined['latency_breakdown_avg']['retrieval_ms']}ms, Gen: {combined['latency_breakdown_avg']['generation_ms']}ms |
"""
    else:
        md += f"""| Metric | Track Score ({combined['total_questions']} Qs) | Wilson 95% Confidence Interval | Benchmark Target |
| :--- | :---: | :---: | :---: |
| **Overall Benchmark Score** | **{combined['overall_score']}%** | — | > 85.0% |
| **Answer Accuracy** (Answerable Qs) | **{combined['answer_accuracy']}%** ({combined['answerable_count']} Qs) | [{combined['answer_accuracy_ci']['lower']}%, {combined['answer_accuracy_ci']['upper']}%] | > 85.0% |
| **Citation Accuracy** (Exact Page Match) | **{combined['citation_accuracy']}%** | [{combined['citation_accuracy_ci']['lower']}%, {combined['citation_accuracy_ci']['upper']}%] | > 80.0% |
| **Fallback Recall** (Abstention on Unanswerable) | **{combined['fallback_recall']}%** ({combined['unanswerable_count']} Qs) | [{combined['fallback_recall_ci']['lower']}%, {combined['fallback_recall_ci']['upper']}%] | > 85.0% |
| **Fallback Precision** | **{combined['fallback_precision']}%** | — | > 90.0% |
| **False Abstentions** | **{combined['false_abstentions']}** | — | 0 |
| **Average Pipeline Latency** | **{combined['avg_latency_ms']} ms** | Retrieval: {combined['latency_breakdown_avg']['retrieval_ms']}ms, Gen: {combined['latency_breakdown_avg']['generation_ms']}ms | < 25,000 ms |
"""

    md += """
---

## 2. Per-Question Detailed Breakdown

| ID | Question | Type | Answer | Citation | Pipeline Latency | Retrieval / Gen | Gating Score | Generator Model |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
"""

    for r in records:
        ans_icon = "✅ Pass" if r["answer_correct"] else "❌ Fail"
        cit_icon = "✅ Pass" if r["citation_correct"] else ("➖ N/A" if not r["is_answerable"] else "❌ Fail")
        qtype = "Answerable" if r["is_answerable"] else f"Unanswerable ({r.get('subtype', 'near_miss')})"
        bd = r.get("latency_breakdown", {})
        ret_gen = f"{bd.get('retrieval_ms', 0):.0f}ms / {bd.get('generation_ms', 0):.0f}ms"
        md += f"| {r['id']} | {r['question']} | {qtype} | {ans_icon} | {cit_icon} | {r['latency_ms']:.0f}ms | {ret_gen} | {r.get('gating_score', 'N/A')} | `{r.get('model_used', 'N/A')}` |\n"

    failed_records = [
        r for r in records
        if (r["is_answerable"] and (r["answer_correct"] == 0 or r["citation_correct"] == 0))
        or (not r["is_answerable"] and not r["abstained"])
    ]

    md += "\n---\n\n## 3. Failure Analysis & Diagnoses\n\n"
    if failed_records:
        md += f"Found **{len(failed_records)} failure(s)** during this evaluation run:\n\n"
        for f in failed_records:
            md += f"### Question {f['id']}: {f['question']}\n"
            md += f"- **Type**: `{'Answerable' if f['is_answerable'] else 'Unanswerable'}`\n"
            md += f"- **Diagnosis**: {f.get('diagnosis', 'N/A')}\n"
            if f["is_answerable"]:
                md += f"- **Expected**: {f['expected_answer']} (`{f['expected_file']}`, p.{f['expected_page']})\n"
                md += f"- **Actual**: {f['actual_answer']}\n"
            else:
                md += f"- **Expected**: Fallback abstention message\n"
                md += f"- **Actual**: {f['actual_answer']}\n\n"
    else:
        md += "🎉 **Zero failures!** All questions passed answer verification, exact citation page matching, and fallback abstention.\n\n"

    return md


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PolicyPilot Benchmark Evaluation Runner")
    parser.add_argument("--track", choices=["synthetic", "real", "real_v2", "all"], default="synthetic", help="Benchmark track to run")
    parser.add_argument("--questions", type=str, default=None, help="Custom questions JSON file path")
    parser.add_argument("--collection", type=str, default=None, help="Chroma/SQLite collection name")
    args = parser.parse_args()

    if args.track == "all":
        print("\n>>> Running Synthetic Benchmark Track <<<\n")
        run_evaluation(track="synthetic", collection="default")
        print("\n>>> Running Real-World Benchmark Track (v1) <<<\n")
        run_evaluation(track="real", collection="real_docs")
        print("\n>>> Running Real-World Benchmark Track (v2) <<<\n")
        run_evaluation(track="real_v2", collection="real_docs")
    else:
        col = args.collection or ("real_docs" if "real" in args.track else "default")
        run_evaluation(questions_path=args.questions, collection=col, track=args.track)
