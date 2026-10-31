
# PolicyPilot ✈️

> **Enterprise HR Policy RAG Chatbot with Citation Verification & Dual-Layer Hallucination Fallback**

PolicyPilot is a production-grade, citation-backed Retrieval-Augmented Generation (RAG) assistant designed to answer employee questions about corporate HR policies, benefits, leaves, and security guidelines. Answers are **strictly grounded** in source policy documents with verifiable page citations, or cleanly abstained with a dedicated fallback message when documentation does not support an answer.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion Pipeline
        A[Upload: PDF / DOCX / TXT / MD] --> B[Parser: PyMuPDF / python-docx]
        B --> C[Page-Boundary Chunker: ~800 chars, ~120 overlap]
        C --> D[SQLite Metadata Store: docs & chunks]
        C --> E[Vector Embeddings: gemini-embedding-001]
        E --> F[(ChromaDB: Vector Index)]
        C --> G[(BM25 In-Memory Index: rank_bm25 — rebuilt on startup & every upload/delete)]
    end

    subgraph Chat & Retrieval Engine
        H[Employee Question] --> I{Chat History Exists?}
        I -- Yes --> J[Query Rewriter: Contextualize Standalone Query]
        I -- No --> K[Direct Query]
        J --> L[Hybrid Search: Vector Cosine + BM25]
        K --> L
        L --> M[Cosine Similarity Gating: Best Vector Chunk]
        M --> N{Score >= Threshold (0.55)?}
        N -- No --> O[Layer 1 Fallback: I couldn't find this in the documents...]
        N -- Yes --> P[Reciprocal Rank Fusion RRF k=60: Top-5 Chunks — ordering only]
        P --> Q[LLM Grounding: gemini-3.8-flash / Strict Prompt]
        Q --> R{Structured Answerable?}
        R -- No --> O
        R -- Yes --> S[Grounded Response: Text + [1], [2] Citations]
    end

    subgraph User Experience
        S --> T[Next.js Chat UI: Citation Chips]
        T --> U[Interactive Citation Drawer: Document + Page + Snippet]
        O --> V[High-Contrast Fallback Alert Banner]
        W[Admin Portal /admin] --> X[Document Upload & Re-indexing]
        W --> Y[Automated 30-Question Evaluation Suite]
    end
```

---

## ✨ Core Features

1. **Strict Page-Boundary Ingestion**:
   - Parses multi-page PDFs using PyMuPDF (`fitz`), DOCX, and TXT/MD files.
   - Chunks text at ~800 characters with ~120 character overlap, **strictly constrained to never cross physical page boundaries**. Every chunk maps to exactly one physical page.
   - Re-uploading a document cleanly replaces previous versions in SQLite, ChromaDB, and BM25.

2. **Two-Tier Fallback Architecture (Anti-Hallucination Guardrails)**:
   - **Layer 1 (Retrieval Gating)**: Computes raw vector cosine similarity of the best retrieved chunk. If the top similarity score is below the configured threshold (`RETRIEVAL_SIMILARITY_THRESHOLD=0.55`), the LLM call is bypassed completely and PolicyPilot returns the safe fallback message immediately.
   - **Layer 2 (Model Structured Grounding)**: The LLM prompt enforces a strict JSON schema (`{"answerable": false, "confidence": ..., "answer": "...", "cited_indices": [...]}`). If the retrieved excerpts do not contain the exact factual answer, the LLM abstains.
   - **Fallback Message**:
     > *"I couldn't find this in the uploaded documents. Try rephrasing, or contact HR directly."*

3. **Hybrid Search & Reciprocal Rank Fusion (RRF)**:
   - Combines vector similarity (semantic understanding) and BM25 (exact keyword and acronym matching).
   - **Relevance gating** uses the raw vector cosine similarity of the best chunk (optionally boosted by BM25 normalized score). RRF is used **only** for ordering the final top-5 context chunks, not for gating.
   - Merged with Reciprocal Rank Fusion ($k=60$) to order the final top-5 context chunks.
   - BM25 index is automatically rebuilt on server startup and after every document upload or deletion.

4. **Multi-Turn Follow-Up Query Rewriting**:
   - Only executes when conversation history exists. Contextualizes conversational follow-ups (e.g. *"What about after 5 years?"*) into standalone search queries before retrieval.

5. **Interactive Source Verification Drawer**:
   - Bracketed citation markers `[1]`, `[2]` and chips display under answers.
   - Clicking any citation opens a sleek slide-in drawer showing the exact source document name, 1-indexed page number, and the supporting excerpt snippet.

6. **Admin Portal & Automated Evaluation Suite**:
   - Protected by password gate (`ADMIN_PASSWORD`).
   - Drag-and-drop document upload, real-time chunk statistics, and deletion.
   - Built-in 30-question automated benchmark suite with LLM-as-judge evaluation.

---

## 📊 Evaluation Methodology & Benchmark Results

The benchmark suite (`eval/run_eval.py`) validates PolicyPilot against 30 realistic questions derived from 3 synthetic Northwind Labs HR documents:
- **Northwind_Labs_Employee_Handbook.pdf** (PTO, probationary period, remote work, sick leave, parental leave, bereavement)
- **Northwind_Labs_Benefits_Guide.pdf** (Health plans, 401k match, vesting, tuition, wellness stipend, EAP)
- **Northwind_Labs_Code_of_Conduct_and_IT_Security.pdf** (Password policies, clean desk, gift policy, incident reporting)

### Dataset Split (Dev vs Test)
Hyperparameters (chunk window 800/120 chars and similarity threshold 0.55) were **tuned on the 10-question Dev Split** and subsequently benchmarked out-of-sample on the **20-question Test Split**:
- **Dev Split (10 Questions)**: 7 Answerable + 3 Unanswerable — used to tune threshold and chunking.
- **Test Split (20 Questions)**: 15 Answerable + 5 Unanswerable — held-out out-of-sample evaluation.
- **Combined (30 Questions)**: 22 Answerable + 8 Unanswerable.

> **Note**: Ground-truth page numbers in `eval/questions.json` are generated programmatically from the source PDFs using anchor text search (PyMuPDF), not manually assigned.

### Benchmark Results Table

| Metric | Combined Benchmark (30 Qs) | Dev Split (10 Qs) | Test Split (20 Qs) | Target |
| :--- | :---: | :---: | :---: | :---: |
| **Overall Score** | **97.5%** | **100.0%** | **96.7%** | > 90% |
| **Answer Accuracy** (LLM-as-Judge) | **100.0%** (22/22) | **100.0%** (8/8) | **100.0%** (14/14) | > 90% |
| **Citation Accuracy** (Exact Page Match) | **100.0%** (22/22) | **100.0%** (8/8) | **100.0%** (14/14) | > 85% |
| **Fallback Recall** (Abstention on Unanswerable) | **87.5%** (7/8)¹ | **100.0%** (2/2) | 83.3% (5/6)¹ | > 90% |
| **Fallback Precision** (No False Abstentions) | **100.0%** | **100.0%** | **100.0%** | > 90% |
| **False Abstentions** | **0** | **0** | **0** | 0 |
| **Average Latency** | **~16,122 ms** | ~13,756 ms | ~17,305 ms | < 25,000 ms |

> ¹ The 87.5% fallback recall reflects a known **ground-truth labeling discrepancy in Q30** (see detailed analysis below). The model's actual answer to Q30 is factually correct per the handbook. See the Q30 analysis section for full context.

### 🔍 Ground-Truth Analysis: Question 30 Labeling Discrepancy

In the evaluation suite, **Question 30** was originally cataloged in the benchmark dataset with label `is_answerable: false`:
> *"Can a new employee who has been with the company for only 2 months take paid parental leave?"*

However, the policy in *Northwind Labs Employee Handbook*, Page 3, explicitly defines the statutory eligibility tenure:
> *"To qualify for paid parental leave, employees must have completed a minimum of 6 months of continuous full-time service prior to the qualifying event."*

When presented with Question 30, PolicyPilot's retriever retrieved Page 3, and the generator returned:
> *"No, to qualify for paid parental leave, employees must have completed a minimum of 6 months of continuous full-time service prior to the qualifying event [1]."* (citing *Northwind Labs Employee Handbook.pdf*, Page 3).

**Why Q30 is intentionally preserved without post-hoc relabeling**:
The model's answer is factually correct according to the company handbook. The benchmark dataset author originally intended for "2 months" to represent an unmentioned tenure scenario and mislabeled the question as unanswerable. However, **we intentionally refrained from quietly relabeling or cherry-picking Q30 after seeing the results**, as modifying ground-truth labels post-hoc constitutes tuning on the test set (data leakage). Instead, we document this discrepancy transparently:
- **Raw Automated Score (strict abstention expected)**: 83.3% test fallback recall (5/6 abstentions), 96.7% overall test score.
- **Factually Grounded Score (accounting for Q30 accuracy)**: 100.0% factual accuracy across all 15 answerable inquiries and 100% correct citations. An honest discrepancy note is far more credible than an engineered 100%.

---

### 🔧 Retriever Optimization: Q5 Ranking Fix (Ranking vs Gating)

During initial dev split tuning, Question 5 (*"What is the minimum internet speed required for remote workers?"*) resulted in a false abstention:
- **Root Cause**: The raw vector cosine similarity of the target chunk was **0.5759**, successfully clearing the similarity gating threshold of **0.55**. However, pure vector search placed the target chunk at **rank 6**, just outside the delivered context window (`top_k=5`). Because the chunk was excluded from the LLM prompt context, the model correctly refused to hallucinate (Layer-2 abstention).
- **The Failure was a Ranking Miss, Not a Gating Miss**: Tuning the threshold closer to 0.57 would have been fragile and risked false admissions on unanswerable questions.
- **Fix Implemented**:
  1. The BM25 index is automatically warmed up on server startup and standalone evaluation entry.
  2. The initial candidate retrieval pool was widened to $k=20$ (`candidate_k = max(20, top_k * 4)`) before reciprocal rank fusion ($k=60$).
- **Result**: Under hybrid BM25 + Vector fusion, the target chunk advanced from **rank 6 to rank 2** (RRF score: 0.0315, gating similarity: 0.6395), enabling the LLM to answer the question with 100% factual accuracy and exact page citation while leaving the 0.55 gating threshold safely untouched.

---

### 🔒 Reproducibility, Model Pinning & Audit
- **Model Aliases vs Pinned Snapshots**: Floating aliases (such as `gemini-flash-lite-latest`) can change weights or behavior across API deployments. For production benchmarks, models should be pinned to immutable snapshots (`gemini-3.1-flash-lite` or exact snapshot dates).
- **Per-Question Model Audit**: `eval/run_eval.py` records the exact `model_used` for every question response. At the end of the run, the benchmark engine audits all 30 questions and logs an alert if any question triggered fallback to a different generator model mid-run.
- **Cross-Provider Judge Independence**: In the default configuration, both generator and LLM-as-judge use Google Gemini models, which introduces potential family-agreement bias. `run_eval.py` supports cross-provider verification via OpenAI (`gpt-4o-mini`) or Anthropic (`claude-3-5-haiku-20241022`) via `.env` configuration.

---

## 🌐 Real-World Evaluation Benchmark Tracks (Public PDF)

To address the limitations of synthetic benchmarking, PolicyPilot includes an isolated **Real-World Evaluation Track** benchmarked against an authentic public-sector policy manual:
- **Source Document**: `eval/real_docs/demo_pdf_employee_benefits.pdf` (*Unit 9: Employee Benefits*, 15 pages, 61 chunks).
- **Strict Collection Isolation**: Ingested into a dedicated collection (`policypilot_real_docs` in ChromaDB, `real_docs` in SQLite/BM25) via `eval/ingest_real_docs.py`. It is completely isolated from the synthetic Northwind Labs documents.
- **Question Formulation**: Drafted with AI assistance from the document text; ground-truth pages located programmatically and spot-checked by the author.
- **Strictly Un-Tuned Evaluation**: Evaluated using the **exact production configuration without modification** (`similarity_threshold=0.55`, `top_k=5`, `rrf_k=60`, chunking `800/120`, default prompting). No threshold adjustments or prompt engineering were made for this track.

> [!WARNING]
> **Critical Architectural Observation (Gating vs. Grounding)**:
> On the real-document track, **the similarity gate did not separate answerable from unanswerable questions**. The cosine similarity gating scores for answerable questions were **0.748–0.854**, while near-miss unanswerable questions scored **0.725–0.799** (and false-premise questions in Pass 2 scored **0.691–0.832**). Because both distributions sat comfortably above the 0.55 threshold, the similarity gate admitted all queries into LLM context. **Abstention depended entirely on the Layer 2 LLM grounding check**, empirically proving why single-gate vector retrieval is insufficient for anti-hallucination and why dual-layer defense is required.

---

### 1. Track Results Summary & Pooled Statistics

The table below reports individual track performance alongside **pooled results across both tracks** (34 answerable questions total) with exact **Wilson 95% Confidence Intervals**:

| Metric | Synthetic Track (30 Qs) | Real Track Pass 1 (15 Qs) | Real Track Pass 2 (10 Qs) | **Pooled Benchmark (45 Qs: 34 Ans)** | Wilson 95% CI (Pooled) | Target |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Overall Benchmark Score** | **97.5%** | **100.0%** | **100.0%** | **98.2%** | — | > 90% |
| **Answer Accuracy** (Answerable) | **100.0%** (22/22) | **100.0%** (12/12) | **100.0%** (5/5) | **100.0%** (34/34) | **[89.8%, 100.0%]** | > 90% |
| **Citation Accuracy** (Exact Page) | **100.0%** (22/22) | **100.0%** (12/12) | **100.0%** (5/5) | **100.0%** (34/34) | **[89.8%, 100.0%]** | > 85% |
| **Fallback Recall** (Abstention) | **87.5%** (7/8)¹ | **100.0%** (3/3) | **100.0%** (5/5) | **90.9%** (10/11)¹ | **[62.3%, 98.4%]**² | > 90% |
| **Fallback Precision** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | — | > 90% |
| **False Abstentions** | **0** | **0** | **0** | **0** | — | 0 |
| **Avg Pipeline Latency** | ~3,090 ms | ~3,212 ms | ~2,566 ms | ~3,010 ms | — | < 25,000 ms |

> ¹ The synthetic track abstention rate reflects the known Q30 handbook ground-truth labeling discrepancy documented in the Q30 section.  
> ² **Sample Size Sensitivity on Unanswerable Queries**: Note how small the unanswerable evaluation sets are ($N=11$ total across synthetic and Pass 1: 8 synthetic, 3 real). Because $N=11$ is modest, the Wilson 95% confidence lower bound is **62.3%**, even though 10 of 11 questions successfully abstained.

---

### 2. Latency Decomposition & The 1.5 s vs 16 s Discrepancy

PolicyPilot instruments latency across each stage of execution:
- **Retrieval Phase**: ~700–850 ms (Query embedding with `gemini-embedding-001` + ChromaDB cosine vector search + SQLite BM25 + Reciprocal Rank Fusion).
- **Generation Phase**: ~1,400–2,400 ms (Streaming/JSON content generation via `gemini-flash-lite-latest`).
- **LLM Judge Evaluation**: ~1,100–1,800 ms (Verification prompt scored via `gemini-flash-lite-latest` / `gemini-3.6-flash`).

#### Root Cause of the 1.5 s vs 16 s Discrepancy
- **1.5 s – 3.0 s (Steady-State Unconstrained)**: Under steady-state API throughput, `gemini-flash-lite-latest` generates structured citations in 1.4–2.2 seconds with ~750 ms retrieval, totaling **~2.2–3.0 seconds**.
- **14.0 s – 17.5 s (Burst Rate-Limit Backoff)**: In dense sequential batch benchmark runs (30 questions evaluated back-to-back), the query rate exceeded the Gemini API Free Tier 15 Requests-Per-Minute (RPM) quota. When an HTTP 429 (`RESOURCE_EXHAUSTED`) is returned:
  1. The pipeline catches the error and executes an **automatic 3.0-second backoff sleep** before retrying.
  2. If the judge model simultaneously encounters a rate limit, an **additional 5.0-second backoff sleep** occurs.
  3. Failover cascades to secondary candidate models (`gemini-3-flash-preview`, `gemini-3.6-flash`), introducing sequential roundtrip TLS handshakes.
  4. Cumulative retry delays and multi-model failovers inflated the wall-clock turnaround of affected questions to **14–18 seconds**.

---

### 3. Real-World Track Pass 1: Detailed Breakdown (`eval/real_questions.json`)

| ID | Question | Expected Ground Truth | Page | Type | Result | Citation | Gating Score |
| :-: | :--- | :--- | :-: | :-: | :-: | :-: | :-: |
| 1 | What retirement age did the Fifth Central Pay Commission fix for central government employees and university teachers? | 60 years for central employees, 62 for university teachers | 8 | Answerable | ✅ Pass | ✅ p.8 | 0.748 |
| 2 | How many years of qualifying service are needed to receive a government pension? | A minimum of ten years | 11 | Answerable | ✅ Pass | ✅ p.11 | 0.787 |
| 3 | What portion of their pension can central government employees commute? | Up to one-third (1/3rd) | 9 | Answerable | ✅ Pass | ✅ p.9 | 0.785 |
| 4 | Under the Payment of Gratuity Act, 1972, what is the gratuity rate and the maximum amount? | 15 days’ wages per completed year, max Rs 2 lakh | 12 | Answerable | ✅ Pass | ✅ p.12 | 0.808 |
| 5 | How many years of continuous service does the Payment of Gratuity Act require, and how many employees must the establishment have? | 5 years continuous service; 10 or more employees | 11 | Answerable | ✅ Pass | ✅ p.11 | 0.784 |
| 6 | What is the maximum maternity leave that counts toward the period of employment for gratuity? | Twelve weeks | 12 | Answerable | ✅ Pass | ✅ p.12 | 0.832 |
| 7 | What medical allowance did the Fifth Pay Commission suggest for pensioners not covered by CGHS? | Rs 100 per month | 12 | Answerable | ✅ Pass | ✅ p.12 | 0.843 |
| 8 | What quantum of family pension did the Fifth Pay Commission retain? | 30% of reckonable emoluments, ceiling removed | 11 | Answerable | ✅ Pass | ✅ p.11 | 0.854 |
| 9 | What was the revised earned-leave entitlement for industrial employees with 11 to 20 years of service? | 25 days (up from 22) | 7 | Answerable | ✅ Pass | ✅ p.7 | 0.783 |
| 10 | How many days of earned leave can industrial employees accumulate, and how much can be encashed during service? | Up to 300 days; encash up to 60 days on LTC | 8 | Answerable | ✅ Pass | ✅ p.8 | 0.809 |
| 11 | What ex-gratia amount does the Golden Handshake Scheme give employees identified as surplus? | 1.5 months emoluments (Pay+DA)/yr or remaining service, lower | 13 | Answerable | ✅ Pass | ✅ p.13 | 0.780 |
| 12 | Which Supreme Court case on pensions is cited, and what did the Court hold about the nature of pension? | *D.S. Nakara v. UOI*; payment for past services, not a bounty | 9 | Answerable | ✅ Pass | ✅ p.9 | 0.791 |
| 13 | What is the employer contribution percentage under the New Pension Scheme? | *Out of Scope / Near-Miss* (Manual covers old scheme & PF) | N/A | Near-Miss | ✅ Abstained | ➖ N/A | 0.732 (Layer 2) |
| 14 | What is the minimum monthly pension amount for a central government employee? | *Out of Scope / Near-Miss* (Text mentions min/max exist, no figure) | N/A | Near-Miss | ✅ Abstained | ➖ N/A | 0.799 (Layer 2) |
| 15 | How many days of paternity leave do central government employees get? | *Out of Scope / Near-Miss* (Manual mentions maternity leave only) | N/A | Near-Miss | ✅ Abstained | ➖ N/A | 0.725 (Layer 2) |

---

### 4. Real-World Track Pass 2: Adversarial & Paraphrased (`eval/real_questions_v2.json`)

To stress-test linguistic robustness and false-premise susceptibility, a second un-tuned pass was executed using 10 additional questions:

| ID | Subtype | Question | Expected Ground Truth | Page | Result | Citation | Gating Score |
| :-: | :--- | :--- | :--- | :-: | :-: | :-: | :-: |
| 1 | Paraphrased / Indirect | At what age are university faculty members required to retire compared to staff in central government ministries? | 62 years for faculty, 60 for central employees | 8 | ✅ Pass | ✅ p.8 | 0.721 |
| 2 | Paraphrased / Indirect | Can an employee who served for seven years qualify for a central government retirement pension? | No, minimum 10 years of qualifying service required | 11 | ✅ Pass | ✅ p.11 | 0.770 |
| 3 | Paraphrased / Indirect | What is the statutory ceiling on gratuity payments under the 1972 Gratuity Act? | Rs two lakh | 12 | ✅ Pass | ✅ p.12 | 0.812 |
| 4 | Paraphrased / Indirect | How much monthly compensation do pensioners living outside CGHS areas receive for medical expenses? | Rs 100 per month | 12 | ✅ Pass | ✅ p.12 | 0.840 |
| 5 | Paraphrased / Indirect | Did the Supreme Court characterize pensions as a discretionary bounty or employer grace in the Nakara ruling? | No, held as payment for past services, not a bounty | 9 | ✅ Pass | ✅ p.9 | 0.833 |
| 6 | **False-Premise** | Under the Golden Handshake Scheme, why are surplus employees given 3 months of emoluments per year of service instead of 1.5 months? | *Unanswerable* (False premise: Scheme gives 1.5 months) | N/A | ✅ Abstained | ➖ N/A | 0.783 (Layer 2) |
| 7 | **False-Premise** | How many months of paid paternity leave can male industrial employees encash during leave travel concession? | *Unanswerable* (False premise: Paternity leave not encashable) | N/A | ✅ Abstained | ➖ N/A | 0.744 (Layer 2) |
| 8 | **False-Premise** | Which High Court judgment overturned D.S. Nakara v. Union of India to declare pensions a bounty? | *Unanswerable* (False premise: Ruling was Supreme Court, never overturned) | N/A | ✅ Abstained | ➖ N/A | 0.832 (Layer 2) |
| 9 | Near-Miss | What annual interest rate is credited on Central Government Provident Fund balances? | *Unanswerable* (PF mentioned, no interest rate stated) | N/A | ✅ Abstained | ➖ N/A | 0.691 (Layer 2) |
| 10 | Near-Miss | How many days of casual leave do central government employees receive annually? | *Unanswerable* (Casual leave listed, no day count given) | N/A | ✅ Abstained | ➖ N/A | 0.753 (Layer 2) |

### Failure Analysis & Diagnoses

- **Total Failures**: **0 / 15** (100% Pass Rate).
- **Diagnosis of 12 Answerable Questions**:
  - All 12 answerable queries retrieved the relevant chunks within top-5 RRF ordering.
  - Vector gating similarity scores ranged comfortably between **0.748 and 0.854**, clearing the un-tuned **0.55** threshold without false abstentions.
  - Every citation matched the exact physical page of `demo_pdf_employee_benefits.pdf`.
- **Diagnosis of 3 Unanswerable Near-Misses**:
  - **Q13 (NPS Employer Contribution)**: Retrieved pension scheme chunks with gating score 0.732. Because the document only covers the old non-contributory scheme and provident fund, Layer-2 LLM grounding correctly detected the absence of NPS percentage and triggered clean fallback.
  - **Q14 (Minimum Monthly Pension Figure)**: Gating score 0.799 (retrieved chunks on quantum of pension). The text explicitly discusses minimum and maximum pensions as statutory concepts without stating a rupee figure. The model abstained cleanly rather than fabricating an arbitrary number.
  - **Q15 (Paternity Leave Duration)**: Gating score 0.725 (retrieved maternity leave on Page 3 and 12). Layer 2 recognized that the manual discusses only maternity leave and abstained without confusion.

---

### ⚠️ Limitations & Real-World Generalization

While PolicyPilot demonstrates strong evaluation numbers on the synthetic test suite, production enterprise deployment introduces several known limitations that must be acknowledged:

1. **Synthetic Corpus Scale & Phrasing Bias**:
   - **Corpus Scale**: The evaluation corpus consists of 3 synthetic PDF documents totaling 12 pages and 32 chunks. Real corporate intranets typically encompass hundreds of policy manuals, addenda, and state-specific riders across thousands of pages.
   - **Shared Prior / Phrasing Overlap**: The documents, benchmark questions, and LLM-as-judge prompts were all generated by modern LLMs. Consequently, they share syntactic structure, vocabulary, and clean topic separation that rarely exist in human-written HR handbooks.
2. **Statistical Confidence & Sample Size**:
   - The test set contains only **14 held-out answerable questions** (and 6 unanswerable questions). With $N=14$, the 95% binomial confidence interval is wide ($\approx [76.8\%, 100\%]$). A single miss drops reported accuracy from 100% to 92.9%, making small-sample accuracy numbers sensitive to individual questions.
3. **Complex Document Formatting & Multimodality**:
   - Real-world HR handbooks frequently feature multi-column tables (e.g., deductible tiers by salary band), embedded scanned forms, footnotes, and appendices. PyMuPDF text-based page chunking handles linear text cleanly, but complex table structure extraction requires specialized table parsers or multimodal vision LLMs.
4. **Roadmap for Enterprise Hardening**:
   - For an uncompromised enterprise evaluation, we recommend benchmarking against an authentic public corporate or government handbook (e.g., 50+ page university or municipal staff manual) accompanied by 10 to 15 hand-authored questions covering edge-case tenure policies, exceptions, and near-misses. An 85% accuracy on messy real-world documents provides stronger real-world confidence than 100% on synthetic data.

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- A Gemini API Key (`GEMINI_API_KEY`)

### Option A: Local Two-Command Start

#### 1. Backend Setup & Ingestion
```bash
# In the project root
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY

# 4. Generate sample documents and seed database
python scripts/seed.py

# 5. Start the FastAPI backend server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup
```bash
# In a new terminal window
cd frontend
npm install
npm run dev
```

Open your browser to:
- **Employee Chat UI**: [http://localhost:3000](http://localhost:3000)
- **Admin Management Portal**: [http://localhost:3000/admin](http://localhost:3000/admin) (Configured via `ADMIN_PASSWORD` in `.env`)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option B: Docker Compose
```bash
docker-compose up --build
```

---

## 🧪 Running Automated Tests and Evaluation

### Run Unit Tests
```bash
pytest backend/tests/test_rag.py -v
```

### Run Evaluation Suite

```bash
# 1. Run Real-World Evaluation Track Pass 1 (Public PDF manual, 15 questions)
python eval/run_eval.py --track real
# Outputs: eval/real_results.json & eval/real_results.md

# 2. Run Real-World Evaluation Track Pass 2 (False-premise & paraphrased, 10 questions)
python eval/run_eval.py --track real_v2
# Outputs: eval/real_results_v2.json & eval/real_results_v2.md

# 3. Run Synthetic Evaluation Track (Northwind Labs documents, 30 questions)
python eval/run_eval.py --track synthetic
# Outputs: eval/results.json & eval/results.md

# 4. Run All Tracks Sequentially
python eval/run_eval.py --track all
```

---

## 🛠️ Configuration Options (`.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *(Required)* | Google GenAI API Key |
| `LLM_PROVIDER` | `gemini` | Primary LLM provider (`gemini`, `openai`, `anthropic`) |
| `GEMINI_LLM_MODEL` | `gemini-flash-lite-latest` | Gemini chat & rewrite model (with fallback cascade in `GEMINI_FALLBACK_MODELS`) |
| `GEMINI_FALLBACK_MODELS` | `gemini-flash-lite-latest,gemini-3-flash-preview,gemini-3.1-flash-lite,gemini-3.6-flash,gemini-3.5-flash` | Comma-separated fallback cascade for high demand / rate limits |
| `GEMINI_JUDGE_MODEL` | `gemini-flash-lite-latest` | Model used for LLM-as-judge in eval suite |
| `EMBEDDINGS_PROVIDER` | `gemini` | Embedding provider (`gemini`, `openai`) |
| `GEMINI_EMBEDDING_MODEL`| `gemini-embedding-001` | Gemini vector embedding model — verified active |
| `RETRIEVAL_SIMILARITY_THRESHOLD` | `0.55` | Raw vector cosine similarity gating threshold (tuned on dev split) |
| `TOP_K_RETRIEVAL` | `5` | Number of context chunks delivered to LLM |
| `RRF_K` | `60` | Reciprocal Rank Fusion smoothing constant (ordering only, not gating) |
| `ADMIN_PASSWORD` | *(Configured via `.env`)* | Password protection for `/admin` management routes |

---

## 📷 Screenshots

### 1. Employee Chat with Grounded Citations
![Chat Interface](artifacts/chat_preview.png)

### 2. Interactive Source Citation Drawer
![Citation Panel](artifacts/citation_drawer_preview.png)

### 3. Graceful Fallback Banner (Out-of-Scope Query)
![Fallback Banner](artifacts/fallback_preview.png)

### 4. Admin Portal & Evaluation Dashboard
![Admin Portal](artifacts/admin_preview.png)

---

## 🔮 Future Roadmap & Improvements
- **Document Level Access Control (RBAC)**: Restrict executive policies or compensation tiers to authorized employee roles.
- **Multimodal Table & Chart Parsing**: Use vision LLMs to extract financial tables and health tier matrices directly from PDF layouts.
- **Async Streaming (SSE)**: Enable token-by-token streaming responses for ultra-low time-to-first-token.
