# PolicyPilot — Technical Audit Report

**Date:** 2026-11-01  
**Auditor:** Senior Software Architect (AI-assisted, evidence-grounded)  
**Effort assumption for all estimates:** One mid-level developer, full-time (8 h/day).  
**Codebase snapshot:** git HEAD `b22d6f7` — "Connect PolicyPilot frontend to Render API"  
**Report filename rule:** No prior `PROJECT_TECHNICAL_AUDIT.md` existed; this is the first run.

---

## 1. Project Overview & Identity

### Name
**PolicyPilot** — HR Policy RAG Chatbot with Citation Verification

### Plain-English Summary
PolicyPilot is a Retrieval-Augmented Generation (RAG) chatbot that lets employees ask natural-language questions about company HR policy documents and receive answers strictly grounded in the uploaded source material with clickable, page-level citations. It ingests PDF/DOCX/TXT documents, chunks them respecting page boundaries, embeds them with a configurable embedding provider (Gemini, OpenAI), stores vectors in ChromaDB, and answers questions through a two-layer fallback pipeline: (1) cosine-similarity gating before calling the LLM, (2) LLM grounding check that refuses to hallucinate. An admin portal handles document management and eval result surfacing.

### Target Audience & Environment
- **Primary users:** HR teams and employees at a single company.
- **Environment:** Web application — Next.js 14 (App Router) frontend + FastAPI backend, both containerised (Docker/Docker Compose). Backend is currently deployed to Render; frontend connects via `NEXT_PUBLIC_API_URL`.

### Tech Stack
| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), React, Tailwind CSS, lucide-react |
| Backend | FastAPI 0.115, Python 3.12, Uvicorn |
| Vector DB | ChromaDB 0.5+ (persistent, HNSW/cosine) |
| Keyword search | rank-bm25 (in-process, rebuilt on startup) |
| Metadata/chunks | SQLite (stdlib `sqlite3`) |
| PDF parsing | PyMuPDF (fitz) |
| DOCX parsing | python-docx |
| LLM | Gemini (google-genai SDK), OpenAI, Anthropic (provider-switchable) |
| Embeddings | Gemini `gemini-embedding-001`, OpenAI `text-embedding-3-small` |
| Containerisation | Docker, Docker Compose 3.8 |
| Testing | pytest 8/9, httpx |
| CI/CD | **None** — no CI configuration found in repo |
| Deployment | Render (backend), Vercel/static (frontend) |

### Project Boundaries

| Category | Items |
|---|---|
| **Implemented** | PDF/DOCX/TXT ingestion; page-boundary chunking (800/120); Gemini + OpenAI + Anthropic LLM providers; Gemini + OpenAI embedding providers; hybrid retrieval (ChromaDB vector + BM25 + RRF); two-layer fallback (gating + LLM grounding); conversational query rewrite; source-page citations; citation side-panel; admin portal (upload, delete, reindex); collection isolation (`default` / `real_docs`); eval framework (synthetic + real Pass 1 + Pass 2); Docker Compose; 6 unit tests; README |
| **Partial** | Auth (shared-secret password only — no JWT, no sessions, no user identity); rate-limit handling (retry logic in Gemini provider, no global back-pressure); eval trigger from admin UI (runs subprocess synchronously, blocking the HTTP request); DOCX page-number heuristic (2 500-char threshold — imprecise) |
| **Out-of-scope / Vision only** | Multi-tenant / multi-company isolation; SSO/SAML; per-user conversation history persistence; streaming responses; document access controls; audit log; analytics dashboard; RBAC; payment/billing; mobile app |

---

## 2. Current Functionality & Use Cases (What Works TODAY)

### Feature Status Table

| Feature | Status | Evidence |
|---|---|---|
| Chat endpoint `POST /api/chat` | UNVERIFIED (live API call required) | Code reviewed in `backend/app/routers/chat.py`; logic complete |
| Two-layer RAG fallback pipeline | UNVERIFIED | Full code path traced; no HTTP test executed |
| Conversational query rewrite | UNVERIFIED | `llm.py:192-216` — last 4 turns, then Gemini call |
| Hybrid retrieval (vector + BM25 + RRF) | VERIFIED | `test_reciprocal_rank_fusion` PASSED — audit run, 2026-11-01 |
| Page-boundary chunking | VERIFIED | `test_chunking_keeps_page_boundaries`, `test_chunking_single_page_boundary` PASSED |
| Layer-1 fallback gating | VERIFIED | `test_fallback_triggers_below_threshold` PASSED |
| Citation index mapping | VERIFIED | `test_citation_page_mapping` PASSED |
| Collection isolation | VERIFIED | `test_collection_isolation` PASSED; SQLite confirmed: 32 chunks `default`, 61 chunks `real_docs` |
| Admin: document list | UNVERIFIED | `GET /api/admin/documents` behind password gate; code complete |
| Admin: file upload + ingest | UNVERIFIED | `POST /api/admin/upload`; requires Gemini API key |
| Admin: document delete | UNVERIFIED | `DELETE /api/admin/documents/{id}`; code complete |
| Admin: eval trigger | UNVERIFIED | `POST /api/admin/run-eval`; runs `eval/run_eval.py` as blocking subprocess |
| Frontend chat UI build | VERIFIED | `npm run build` succeeded (prior session, 2026-10-30) |
| Citation side-panel | UNVERIFIED | `CitationPanel.tsx` complete; no link to open original PDF |
| PDF parsing | UNVERIFIED | `parser.py:extract_pages_from_pdf` — PyMuPDF; no scanned-PDF OCR |
| Docker Compose deploy | UNVERIFIED | `docker-compose.yml` reviewed; no build run in this audit |
| Eval framework | VERIFIED (prior session) | 3 tracks run; results present in `eval/*.json` (2026-10-30) |

### Real-World Use Cases Possible Today
1. **Employee self-service FAQ** — "How many vacation days do I get?" → page-cited answer from uploaded handbook.
2. **HR policy audit** — HR team uploads updated policies; old vectors cleanly replaced via `delete_by_filename`.
3. **Out-of-scope abstention** — Off-topic questions receive a safe fallback instead of hallucinated answers.
4. **Eval-driven QA** — Internal team runs eval tracks to measure accuracy before releasing a new doc corpus.

### End-to-End User Flow

```
User types question (frontend/src/app/page.tsx:handleSend)
  → POST /api/chat {question, history}  [utils/api.ts:apiFetch]
  → chat.py: rewrite_query() if history exists  [LLM call #1]
  → embeddings.py: embed_query(search_query)  → 768-dim vector
  → retriever.py: HybridRetriever.retrieve()
      → vector_store.py: VectorStore.query(embedding, top_k=20)  [ChromaDB cosine]
      → bm25_store.py: BM25Store.search(query, top_k=20)  [in-memory BM25Okapi]
      → reciprocal_rank_fusion()  → top-5 chunks
      → gating_similarity = best cosine sim (BM25 boost if norm > 0.4)
  → LAYER 1: if gating < 0.55  → return FALLBACK_MESSAGE immediately
  → llm.py: generate_chat_response(question, chunks)  [LLM call #2]
      → Gemini candidate cascade: primary → fallback models on 429/error
      → Returns JSON {answerable, confidence, answer, cited_indices}
  → LAYER 2: if answerable=false  → return FALLBACK_MESSAGE
  → chat.py: map cited_indices → CitationItem list (filename, page, 220-char snippet)
  → Return ChatResponse {answer, citations, answerable, confidence, gating_score}
  → Frontend: [n] citation buttons → CitationPanel.tsx on click
```

### Mock & Hardcoded Data Audit

| Location | What is fake / hardcoded |
|---|---|
| `frontend/src/app/page.tsx:30-51` — `STARTER_QUESTIONS` | Hardcoded to "Northwind Labs" domain |
| `frontend/src/app/page.tsx:175` | Static string "Northwind Labs HR Corpus Active (3 Ingested Documents)" — not dynamic |
| `frontend/src/components/Navbar.tsx:26` | "Northwind Labs" brand label hardcoded |
| `sample_docs/` — 3 PDFs | Synthesised by `scripts/generate_sample_docs.py` (reportlab); fictional company |
| `backend/app/config.py:38` | `ADMIN_PASSWORD: str = "change_me_in_env"` — default fallback if env var not set |
| `docker-compose.yml:21` | `ADMIN_PASSWORD=${ADMIN_PASSWORD:-change_me_in_env}` — same default leaks into container |
| `backend/app/embeddings.py:80-87` | `_fallback_vector()` — SHA-256 hash vector returned silently when Gemini embedding API fails |

---

## 2B. Future Scope (What It SHOULD Do)

### Half-Built / Gap Items Found in Code

| Location | Issue |
|---|---|
| `admin.py:252` — `subprocess.run(..., check=True)` | Synchronous inside async FastAPI handler; long eval run blocks the event loop and can time out HTTP clients |
| `chat.py:54` — `if history_dicts and len(history_dicts) > 0` | Redundant double-check (minor code smell) |
| `llm.py:192-216` — `rewrite_query` | Duplicates fallback loop from `generate_chat_response` (DRY violation) |
| `embeddings.py:65` — silent fallback vector | No error propagated to caller; retrieval quality silently corrupted |
| `bm25_store.py` — in-process, non-persistent | Rebuilt in-memory on every restart; no persistence; O(n) on large corpora |
| `parser.py:61` — DOCX page heuristic | `run._r.xml` introspection is brittle; 2 500-char fallback is approximate |
| `vector_store.py:10` — `COLLECTION_NAME` | Unused module-level alias — dead code |
| `retriever.py:96-97` — gating BM25 boost | Magic-number blend formula with no comment justification |
| No streaming | `generate_chat_response` returns full text; users see blank screen for 2–5 s |
| No conversation persistence | History is client-side React state only; refresh loses context |

### Feature Ranking

**Must-have (for any paying customer):**
- Config-driven company name/branding (not hardcoded "Northwind Labs")
- Real-time document count from backend
- Async eval trigger (background task + polling)
- `hmac.compare_digest` for password comparison
- File-size upload limit
- Input sanitisation / max question length

**Should-have:**
- Streaming responses (Server-Sent Events)
- Server-side conversation history (SQLite `conversations` table)
- CI/CD pipeline (GitHub Actions)
- Integration tests with mocked LLM
- Scanned PDF OCR support

**Nice-to-have:**
- Multi-tenant isolation
- SSO/SAML
- Per-user answer feedback feeding into eval
- Analytics dashboard

---

## 3. Architecture & Data Flow

### Layer Overview

```
┌─────────────────────────────────────────────┐
│  Browser  (Next.js 14 App Router)           │
│  page.tsx · admin/page.tsx                  │
│  CitationPanel.tsx · Navbar.tsx             │
│  utils/api.ts  (typed fetch wrapper)        │
└──────────────┬──────────────────────────────┘
               │ HTTP (CORS-controlled)
               │ NEXT_PUBLIC_API_URL
┌──────────────▼──────────────────────────────┐
│  FastAPI (Uvicorn, Python 3.12)             │
│  main.py · routers/chat.py                 │
│  routers/admin.py                          │
└──┬──────────┬────────────┬──────────────────┘
   │          │            │
   ▼          ▼            ▼
ChromaDB   SQLite      Gemini / OpenAI
(data/)  (data/)      / Anthropic API
HNSW     documents,   (LLM + Embeddings)
cosine   chunks
   ▲
   │  in-process
BM25Okapi (rebuilt from SQLite on startup)
```

### Key Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|---|---|---|
| Page-boundary chunking | Citations map to exact page numbers | Small pages may produce tiny chunks with poor BM25 recall |
| Two-layer fallback | Prevents hallucination; gating avoids unnecessary LLM calls | Gating scores overlap between answerable/unanswerable for near-miss queries (0.725–0.854 documented) |
| BM25 in-memory | Fast keyword recall, zero infrastructure | Non-persistent; rebuilt on restart; linear scan on large corpora |
| SQLite for metadata | Zero-ops, file-based, suits single-server | No horizontal scaling; concurrent writes serialised |
| Multi-provider LLM/embeddings | Portability, cost flexibility | OpenAI/Anthropic paths UNVERIFIED |
| Shared-secret admin auth | Simple to deploy | No per-user identity; no session expiry; susceptible to brute force |

### System Weaknesses

1. **Single point of failure** — All state (SQLite + ChromaDB) on one container volume; no backup, no replication.
2. **BM25 cold-start** — `bm25_store.rebuild()` in lifespan blocks startup on large corpora.
3. **Synchronous eval subprocess** — Blocks async event loop; can kill the HTTP server under load.
4. **Silent embedding failure** — `_fallback_vector()` stores junk vectors without alerting the caller (`embeddings.py:65`).
5. **No rate limiting** — `/api/chat` accepts unlimited requests; Gemini quota exhaustion risk.
6. **Admin password in plain-text header** — `X-Admin-Password` visible in network without TLS enforcement at application layer; no `hmac.compare_digest`.
7. **No upload size limit** — `await file.read()` unbounded; large files could OOM the process.
8. **Hardcoded Northwind Labs branding** — Any new customer/demo requires code edits.

---

## 4. File-by-File Inventory

### Backend

| File | Responsibility & Key Symbols | Inputs / Outputs | Dependencies | Status |
|---|---|---|---|---|
| `backend/app/main.py` | App factory; CORS; lifespan (init DB, rebuild BM25); `GET /api/health` | FastAPI app | config, db, bm25_store, routers | Complete |
| `backend/app/config.py` | `Settings` (pydantic-settings); all env vars with defaults; `sqlite_full_path`, `chroma_full_path` properties | `.env` / env vars | pydantic-settings | Complete |
| `backend/app/routers/chat.py` | `POST /api/chat`; `ChatRequest`, `ChatResponse`, `CitationItem`; 5-step pipeline | JSON body → JSON | llm, embeddings, retriever, config | Complete |
| `backend/app/routers/admin.py` | Document CRUD; eval trigger+results; `verify_admin_password` | Upload, JSON | db, chunker, parser, vector_store, bm25_store, embeddings | Complete; **bug**: sync subprocess in async handler |
| `backend/app/llm.py` | `LLMProvider` ABC; `GeminiLLMProvider`, `OpenAILLMProvider`, `AnthropicLLMProvider`; `get_llm_provider()`; `SYSTEM_PROMPT`, `REWRITE_PROMPT` | chunks + question → JSON dict | google-genai, openai, anthropic | Complete; OpenAI/Anthropic UNVERIFIED |
| `backend/app/embeddings.py` | `EmbeddingProvider` ABC; `GeminiEmbeddingProvider`, `OpenAIEmbeddingProvider`; `_fallback_vector()` | texts/query → float vectors | google-genai, openai | Complete; **bug**: silent fallback on API error |
| `backend/app/retriever.py` | `HybridRetriever`; `reciprocal_rank_fusion()`; `get_retriever()` | query + embedding → chunk dict | vector_store, bm25_store | Complete |
| `backend/app/vector_store.py` | `VectorStore`; add/delete/query; `get_vector_store()` | chunks + embeddings ↔ ChromaDB | chromadb | Complete; dead `COLLECTION_NAME` alias |
| `backend/app/bm25_store.py` | `BM25Store`; `rebuild()`, `search()`; `get_bm25_store()` | SQLite chunks → BM25Okapi | rank-bm25, db | Complete; non-persistent |
| `backend/app/chunker.py` | `chunk_text_page()`; `create_chunks_for_document()` | page text → chunk dicts | — | Complete |
| `backend/app/parser.py` | `parse_document()`; PDF/DOCX/TXT extractors | file bytes → page list | fitz, python-docx | Complete; no OCR; DOCX heuristic imprecise |
| `backend/app/db.py` | SQLite CRUD: `init_db`, `upsert_document`, `save_chunks`, `delete_document`, `list_documents`, `get_all_chunks`, `update_document_status` | `data/policypilot.db` | sqlite3 | Complete; migration guards for `collection` column present |
| `backend/tests/test_rag.py` | 6 pytest tests: chunking, fallback, citations, RRF, collection isolation | backend.app.* | pytest | Complete (all VERIFIED passing) |
| `backend/Dockerfile` | python:3.12-slim; installs requirements; CMD: seed → uvicorn | Docker build context | requirements.txt, seed.py | Complete; seeds on every container start |
| `backend/requirements.txt` | 19 dependencies with `>=` lower bounds | pip install | — | Complete; no lock file (unpinned upper bounds) |

### Frontend

| File | Responsibility & Key Symbols | Inputs / Outputs | Dependencies | Status |
|---|---|---|---|---|
| `frontend/src/app/page.tsx` | Chat UI; `handleSend`, `renderFormattedAnswer`, `STARTER_QUESTIONS` | User input → messages | api.ts, CitationPanel, Navbar | Complete; **hardcoded "Northwind Labs" in 3 places** |
| `frontend/src/app/admin/page.tsx` | Admin portal (775 lines); auth, doc management, 3-track eval switcher | Admin API | api.ts, Navbar | Complete; large monolith |
| `frontend/src/components/CitationPanel.tsx` | Slide-in source panel; `CitationData` interface | `CitationData` prop | lucide-react | Complete; snippet only — no PDF link |
| `frontend/src/components/Navbar.tsx` | Top nav; PolicyPilot brand; "Northwind Labs" label | pathname | next/link | Complete; **hardcoded "Northwind Labs"** |
| `frontend/src/utils/api.ts` | `apiUrl()`, `apiFetch()`, `isChatResponse()` type guard; validates `NEXT_PUBLIC_API_URL` | env var + fetch | — | Complete |
| `frontend/Dockerfile` | Multi-stage Node 20 Alpine; bakes `NEXT_PUBLIC_API_URL` at build time | Docker ARG | package.json | Complete; **URL baked at build time** — different deploy URLs require rebuild |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL=http://localhost:8000` | — | — | Complete (gitignored correctly) |

### Eval & Scripts

| File | Responsibility | Status |
|---|---|---|
| `eval/run_eval.py` | Eval harness; `--track synthetic\|real\|real_v2\|all`; Wilson CIs; latency breakdown; Markdown reports | Complete (29 KB) |
| `eval/generate_questions.py` | AI-assisted question generation against sample docs | Complete (14 KB) |
| `eval/ingest_real_docs.py` | Ingests `eval/real_docs/*.pdf` into `real_docs` collection | Complete |
| `eval/questions.json` | 30 synthetic questions (22 answerable, 8 unanswerable) | Complete |
| `eval/real_questions.json` | 15 real-doc questions Pass 1 | Complete |
| `eval/real_questions_v2.json` | 10 real-doc questions Pass 2 (5 answerable, 5 unanswerable) | Complete |
| `eval/results.json`, `real_results.json`, `real_results_v2.json` | Eval output with per-question latency | Present (2026-10-30) |
| `scripts/seed.py` | DB init + doc ingestion + BM25 rebuild; Docker CMD entry point | Complete |
| `scripts/generate_sample_docs.py` | reportlab-based fake PDF generator | Complete (30 KB) |

---

## 5. Security, Reliability & Quality Assessment

### Code Quality
- **Type annotations:** Consistent throughout backend and TypeScript frontend. Good.
- **Abstraction:** `LLMProvider` ABC, `EmbeddingProvider` ABC, factory functions — well-structured provider pattern. Retriever/store singletons use module-level dicts — functional but not thread-safe for multi-worker deployments.
- **Code smells:** `admin/page.tsx` = 775 lines (should be split). `rewrite_query` duplicates fallback loop from `generate_chat_response`. Dead `COLLECTION_NAME` alias in `vector_store.py:10`. Magic-number gating boost in `retriever.py:96-97`.

### Testing (VERIFIED)

**Command:** `.venv\Scripts\python.exe -m pytest backend/tests -v --tb=short`  
**Result:** **6/6 PASSED in 3.30 s** (Python 3.12.13, pytest 9.1.1, 2026-11-01)

```
PASSED  test_chunking_keeps_page_boundaries
PASSED  test_chunking_single_page_boundary
PASSED  test_fallback_triggers_below_threshold
PASSED  test_citation_page_mapping
PASSED  test_reciprocal_rank_fusion
PASSED  test_collection_isolation
```

**Coverage gaps (UNVERIFIED):**
- Zero integration tests against `/api/chat` or `/api/admin/*` via HTTP.
- No tests for `parser.py`, `embeddings.py`, `llm.py`, `admin.py`.
- No tests for OpenAI/Anthropic provider paths.
- No frontend tests (no Jest, Playwright, or Cypress configured).
- `test_fallback_triggers_below_threshold` tests threshold logic in isolation — not through the actual retriever.
- `test_collection_isolation` passes vacuously if the DB is empty.

### Security & Privacy

| Risk | Location | Severity |
|---|---|---|
| Plain-text password in HTTP header | `admin.py:35`, `admin/page.tsx:106` | Medium |
| Non-constant-time password comparison | `admin.py:35` — Python `==` (not `hmac.compare_digest`) | Low-Medium |
| Default admin password | `config.py:38`, `docker-compose.yml:21` — `"change_me_in_env"` | **High** if unchanged in production |
| No upload size limit | `admin.py:83` — `await file.read()` unbounded | Medium |
| No rate limiting on `/api/chat` | `main.py` — no middleware | Medium |
| No HTTPS enforcement in code | Platform (Render) handles TLS; not enforced at application layer | Medium |
| Wildcard CORS methods/headers | `main.py:58` — `allow_methods=["*"]` | Low (origins explicitly listed) |
| No input length validation | `chat.py:44` — no max-length check | Low |
| No real secrets in git history | `git log -S "AIza"` → **no output** (VERIFIED) | ✅ Clean |
| Password placeholder in git history | `git log -S "password"` → `change_this_to_a_secure_password` only (VERIFIED) | ✅ OK (placeholder only) |
| `.env` gitignored | `.gitignore:41` | ✅ Clean |
| `data/` gitignored | `.gitignore:28` | ✅ Clean |

### Error Handling & State

| Scenario | Handling | Quality |
|---|---|---|
| Gemini 429 rate limit | `llm.py:154-175` — 3 s sleep + retry once, then cascade to next model | Adequate; no jitter/exponential backoff |
| Gemini daily quota | `llm.py:151-153` — immediately skips to next candidate | Good |
| All LLM candidates fail | `llm.py:181-190` — returns `answerable=False` (graceful degradation) | Good |
| Embedding API failure | `embeddings.py:65` — silent SHA-256 fallback vector | **Poor** — corrupts retrieval silently |
| ChromaDB empty | `vector_store.py:76-77` — returns `[]` | Good |
| Unsupported file format | `parser.py:150` — raises `ValueError` (caught in upload handler) | Good |
| Wrong admin password | `admin.py:44-47` — 401 HTTP | Good |
| Eval subprocess failure | `admin.py:273` — 500 with detail | Acceptable; blocks event loop |
| Frontend fetch error | `page.tsx:122-132` — error message in chat | Good |
| `NEXT_PUBLIC_API_URL` missing | `api.ts:21-25` — throws descriptive `Error` | Good |

---

## 6. Gap Analysis: Prototype → Production Product

| Dimension | Current State | Required End State | Main Gaps & Action Needed | Priority |
|---|---|---|---|---|
| **Real Data Integration** | 3 synthetic + 1 real PDF; Northwind Labs fictional brand | Customer's real policy corpus; config-driven branding | Remove hardcoded brand; config company name; add OCR support | **P0** |
| **Database & Migrations** | SQLite with manual `ALTER TABLE` guards | PostgreSQL + Alembic migrations for multi-instance | No migration framework; SQLite cannot scale past 1 writer | P1 |
| **Auth / Multi-User** | Single shared-secret admin password | JWT auth, per-user sessions, RBAC | Full auth layer build-out | P1 |
| **Security & Secrets** | Default password risk; no timing-safe compare; no rate limit | Startup enforcement; `hmac.compare_digest`; rate limiting middleware | ~1 day | **P0** |
| **Error Handling & Observability** | `logging.basicConfig(INFO)`; no structured logging; no APM | Structured JSON logs; Sentry; latency P95 metrics | Logging upgrade + observability tooling | P1 |
| **Performance & Scalability** | BM25 in-memory; synchronous eval; no streaming | Async eval; streaming SSE; BM25 persistence | ~3–5 days | P1 |
| **Testing** | 6 unit tests; 0 integration; 0 E2E | ≥80% coverage; API integration tests; E2E with Playwright | ~5–8 days | P1 |
| **CI/CD & Infrastructure** | No CI configuration in repo | GitHub Actions: lint + test + build on PR; deploy on merge | ~2 days | P1 |
| **UX / Onboarding** | Good dark-mode UI; hardcoded branding; no streaming; 2–5 s blank wait | Configurable branding; streaming; onboarding flow | ~3–4 days | P1 |
| **Legal / Compliance** | No data processing terms | GDPR/DPDP data processing agreement; Gemini API ToS compliance | External legal review required | P2 (calendar risk) |
| **Documentation** | Strong developer README; no operator runbook | Operator deployment guide; OpenAPI reference; security guide | ~2 days | P2 |

### Estimated Monthly Running Cost (Small Scale)

Assumptions: 1 company, 50 active users, 200 queries/day, ~100 chunks ingested, Render + Vercel.

| Item | Basis | Est. Monthly |
|---|---|---|
| Render Web Service (Starter) | KNOWN: \$7/mo | \$7 |
| Vercel (frontend) | KNOWN: Free Hobby | \$0 |
| Gemini API — embeddings | ASSUMED: ~6 000 embed calls/mo | ~\$1–3 |
| Gemini API — LLM (Flash) | ASSUMED: ~12 000 calls/mo × ~800 tokens avg | ~\$1–2 |
| Storage on Render disk | KNOWN: Included in Starter | \$0 |
| **Total** | | **~\$9–12/mo** |

> All cost estimates except Render base price are ASSUMED. Verify against current pricing at https://ai.google.dev/pricing.

---

## 6B. Viability Assessment

### Technical Feasibility — HIGH
Stack is proven; RAG pattern is well-understood. Gaps (auth, CI, streaming, OCR) are standard engineering problems with known solutions. VERIFIED: 6/6 tests pass; build succeeds; eval runs end-to-end.

### Customer Demand — UNVALIDATED
No evidence of customer interviews, LOIs, waitlists, or usage analytics in the repo. The use case (HR policy Q&A) is a real daily pain point for HR teams. However, demand for a *standalone, self-hosted, citation-verified* HR RAG product is UNVALIDATED.

### Differentiation & Defensibility — LOW–MEDIUM (inferred)
**Genuine differentiators:** Two-layer fallback with measurable abstention; page-exact citation panel; open eval framework with Wilson CIs; provider-agnostic.  
**Weaknesses:** Microsoft Copilot for M365, Glean, Guru, and Moveworks offer HR Q&A with citations. These are well-funded and established. RAG pattern is commoditised. No proprietary data moat, network effect, or patent.  
**Niche opportunity (inferred):** SMBs and privacy-sensitive companies wanting self-hosted deployment.

### Commercial Viability — UNVALIDATED
No pricing validation. At \$9–12/mo infrastructure, even a \$15/user/mo model on 50 users yields \$750/mo gross — viable only with low support burden. Legal compliance (GDPR/DPDP, Gemini ToS for HR data) requires external review.

### Minimum Sellable Product
1. Config-driven company name/branding.  
2. Secure admin password (startup enforcement + `hmac.compare_digest`).  
3. One customer's real policy corpus ingested.  
4. Deployed with TLS on a stable public URL.  
5. Basic onboarding documentation for HR admins.  
**Estimated time to MSP:** ~2 weeks (1 mid-level developer).

---

## 7. Prioritized Implementation Roadmap

**Path decision:** Technical feasibility HIGH; commercial viability UNVALIDATED → **Path B (Portfolio) is the immediate priority**. A focused market test should follow if portfolio generates inbound interest.

### Phase 0 — Blockers & Critical Fixes (≤3 days)

| ID | Task | Affected Files | Effort |
|---|---|---|---|
| P0-1 | Fix admin password: startup check rejects default; switch to `hmac.compare_digest` | `admin.py`, `main.py` | 2 h |
| P0-2 | Add upload size limit (e.g. 50 MB) to `POST /api/admin/upload` | `admin.py` | 1 h |
| P0-3 | Surface embedding failure: remove silent `_fallback_vector` or log ERROR + return 500 | `embeddings.py`, `admin.py` | 1 h |
| P0-4 | Fix async eval: use `BackgroundTasks` + polling endpoint instead of blocking subprocess | `admin.py`, `admin/page.tsx` | 4 h |
| P0-5 | Config-driven company name: replace all "Northwind Labs" hardcodes | `page.tsx`, `Navbar.tsx`, `config.py` | 3 h |
| P0-6 | Replace hardcoded document count with dynamic backend query | `page.tsx`, new/existing endpoint | 2 h |

### Phase 1 — Demo Polish & Portfolio Presentation (≤1 week)

| ID | Task | Affected Files | Effort |
|---|---|---|---|
| P1-1 | GitHub Actions CI: pytest + eslint + Next.js build on every PR | `.github/workflows/ci.yml` (new) | 3 h |
| P1-2 | Integration tests for `/api/chat` via httpx TestClient with mocked LLM | `backend/tests/test_api.py` (new) | 6 h |
| P1-3 | Rate limiting middleware (e.g. `slowapi`) on `/api/chat` | `main.py`, requirements.txt | 2 h |
| P1-4 | Architecture diagram (Mermaid) in README | `README.md` | 1 h |
| P1-5 | 2-minute demo video: upload doc → 3 questions (1 fallback) → citation panel | — | 2 h |
| P1-6 | Screenshot carousel in README (5 artifact images already exist) | `README.md` | 1 h |
| P1-7 | Confirm live deployment URL on Render; update README prominently | `README.md`, Render/Vercel config | 2 h |

### Phase 2 — Production-Path (if pursuing Path A, 2–4 weeks)

| ID | Task | Effort | External Dependencies |
|---|---|---|---|
| P2-1 | PostgreSQL + Alembic migrations | 3 days | Render PostgreSQL addon (~\$7/mo) |
| P2-2 | JWT auth + RBAC (admin vs employee) | 4 days | None |
| P2-3 | Multi-tenant collection isolation | 2 days | None |
| P2-4 | Streaming SSE responses | 2 days | None |
| P2-5 | Scanned PDF OCR | 2 days | Google Cloud Vision API or Tesseract |
| P2-6 | Structured logging + Sentry | 1 day | Sentry account |
| P2-7 | Playwright E2E tests | 3 days | None |
| P2-8 | Self-service onboarding wizard | 3 days | None |
| P2-9 | GDPR/DPDP compliance + data processing agreement | External | Legal counsel (2–8 weeks calendar risk) |

### First 5 Immediate Actions (execution order)

1. **P0-5** — Remove Northwind Labs hardcoding. Any demo visitor sees "Northwind Labs" and recognises it as a demo immediately. Config-driven name takes <3 hours and has maximum first-impression impact.  
2. **P0-1** — Fix admin password security. Shipping with a default password is a genuine risk if deployed publicly; takes <2 hours.  
3. **P1-1** — Add GitHub Actions CI. A working CI badge is one of the first things a technical recruiter checks; costs nothing; takes <3 hours.  
4. **P1-7** — Confirm live demo URL. Portfolio value is near-zero without a public URL; update README with direct link.  
5. **P1-5** — Record demo video. HR Q&A is visual; a 2-minute video showing the citation panel is far more convincing than a README paragraph.

---

## 8. Final Scorecard & Recommendation

### Ratings (1–10, rule 9 — evidence-grounded)

| Dimension | Score | Evidence Basis |
|---|---|---|
| **Core Functionality** | 7 | Full RAG pipeline traced; two-layer fallback working per eval (97.5% synthetic, 100% real); UNVERIFIED via live HTTP — cannot exceed 7 |
| **Architecture** | 7 | Clean provider abstraction, page-boundary chunking, RRF fusion; penalised for in-memory BM25, SQLite limit, synchronous eval subprocess, hardcoded branding |
| **Code Quality** | 7 | Consistent type annotations, good abstractions; penalised for 775-line admin component, DRY violation, dead variable, silent embedding failure |
| **Security** | 4 | No secrets in git (VERIFIED); plain-text password header; default password in code; no timing-safe compare; no rate limiting; no upload limit |
| **Reliability** | 5 | Graceful LLM fallback cascade (VERIFIED via eval); silent embedding failure is a reliability risk; BM25 non-persistent; synchronous eval blocks server |
| **Scalability** | 3 | SQLite + in-memory BM25 + single ChromaDB node = single-server only; no connection pooling; BM25 rebuild O(n) |
| **Production-Readiness** | 3 | No CI/CD; no structured logging; no APM; no migration framework; hardcoded branding; default password risk; 0 integration tests |
| **Documentation** | 8 | README thorough (29 KB): architecture, eval methodology, Wilson CIs, latency decomposition, Docker guide; no operator runbook or API reference |
| **Technical Feasibility** | 8 | Stack is proven; all gaps are standard problems; eval results show core mechanism works; VERIFIED build + tests passing |
| **Customer Demand** | UNVALIDATED | No customer interviews, no usage data, no LOI — insufficient evidence per rule 9 |
| **Differentiation** | 4 | Page-exact citations + two-layer abstention + eval framework are genuine; crowded market (Copilot, Glean, Guru, Moveworks); no proprietary moat |
| **Commercial Viability** | UNVALIDATED | No pricing validation, no customer discovery, no revenue — insufficient evidence |
| **Portfolio Value** | **9** | Sophisticated RAG with real eval methodology, Wilson CIs, provider abstraction, Docker deployment, citation UX — well above typical portfolio projects |

### Aggregates

**Technical Readiness** (Core Functionality, Architecture, Code Quality, Security, Reliability, Scalability, Production-Readiness, Documentation, Technical Feasibility):  
`(7 + 7 + 7 + 4 + 5 + 3 + 3 + 8 + 8) / 9 = 52 / 9 =` **5.8 / 10** — 9 of 9 dimensions scored

**Commercial Potential** (Customer Demand, Differentiation, Commercial Viability):  
Customer Demand and Commercial Viability are UNVALIDATED (excluded). Only Differentiation scored (4/10).  
**→ Not computed (insufficient evidence)** — only 1 of 3 dimensions scored. Differentiation alone = 4/10.

**Portfolio Value:** **9 / 10** (standalone dimension)

---

### Final Verdict

## ✦ KEEP AS PORTFOLIO PROTOTYPE

*(with a concrete market test option if inbound interest emerges)*

**Decision criteria:**

| Criterion | Assessment |
|---|---|
| Strength of core use case | Strong — HR policy Q&A is a real daily pain point |
| Production gaps | Significant — no CI, no auth, hardcoded branding, no rate limiting, SQLite-only |
| Defensibility | Weak — established, funded competitors dominate (Copilot, Glean, Guru) |
| Cost to finish MSP | ~2 weeks — achievable, but requires buyer validation first |
| Buyer evidence | **None** — no interviews, no LOI, no usage data |
| Validation risk | High — market is crowded; buyer budget typically goes to bundled M365/GWS tools |

**BUILD TO SELL** and **SELL AFTER REFACTOR** cannot be chosen: the evidence cap requires credible buyer evidence, which does not exist.

**SCALE DOWN TO MVP AND TEST THE MARKET** is a valid *next step* — but only after the portfolio is published and generates inbound interest. The project is not yet at a state where showing it to a buyer is compelling (no live demo, hardcoded branding, no auth).

**Recommended path:**
1. Complete Phase 0 fixes (~3 days): remove hardcoded branding, fix password security, add upload limit.
2. Confirm live deployment; add URL to README; record demo video.
3. Publish as a portfolio project. If inbound interest generates 2+ companies willing to pilot, escalate to SELL AFTER REFACTOR with a proper 30-day pilot experiment.
4. If no inbound interest within 3 months of publishing, the 9/10 portfolio value stands on its own merit for career purposes.

---

## 9. Assumptions, Blocked Items & Open Questions

### Assumptions Made
1. Backend is currently deployed to Render (inferred from commit message `b22d6f7`); live URL was not confirmed in this audit.
2. TLS is handled at the platform level (Render/Vercel) and not enforced at the application layer — assumed correct per standard practice.
3. Gemini API pricing estimates are ASSUMED based on publicly known Flash model tiers; verify at https://ai.google.dev/pricing.
4. "Northwind Labs" is a demo persona confirmed by `scripts/generate_sample_docs.py` using reportlab to synthesise PDFs.
5. OpenAI and Anthropic provider paths are functionally complete by code inspection but UNVERIFIED by test execution.
6. The real `.env` admin password differs from the `change_me_in_env` default — assumed, not confirmed.

### Blocked Items

| Item | What is Needed to Unblock |
|---|---|
| Live `/api/chat` end-to-end test | Running Gemini API key + live backend URL |
| Admin upload/delete/reindex test | Same + admin password |
| OpenAI/Anthropic path verification | OpenAI or Anthropic API key |
| Docker Compose build verification | Docker daemon + Gemini API key |
| Scanned PDF handling | Test scanned PDF; OCR not implemented |
| Competitor pricing verification | Web access to current Glean/Guru/Moveworks pricing pages |
| Gemini API ToS for HR data | Legal review of Google AI ToS |
| GDPR/DPDP compliance | Legal counsel |

### Files Created or Changed as Side Effects of This Audit
- **Created:** `PROJECT_TECHNICAL_AUDIT.md` (this file) — only file written per rule 4.
- `.pytest_cache/` contents updated by pytest run (pre-existing directory, cache files only — not source files).
- No source files were modified, deleted, or overwritten.

### Open Questions Whose Answers Would Change This Report
1. **Is there a live public deployment URL?** If yes, portfolio value increases and commercial validation becomes testable.
2. **Has the admin password been changed from the default in the deployed environment?** If not, this is a P0 security blocker before any public sharing.
3. **Are there real users (even informal testers) using this today?** Even 1 non-developer user changes the commercial viability assessment.
4. **Which model names are valid in the current Gemini API?** `config.py` references `gemini-3.6-flash`, `gemini-3.5-flash` — validate against https://ai.google.dev/gemini-api/docs/models.
5. **Is `eval/real_docs/demo_pdf_employee_benefits.pdf` a real public government document?** This affects whether the real-track eval proves generalisation.
6. **What is the intended deployment model?** SaaS (multi-tenant) vs. self-hosted (single-tenant) fundamentally changes the auth/database architecture needed.

