# Real-World Benchmark Track Pass 2 (real_questions_v2.json)

*Run timestamp: 2026-10-30T17:22:44.518724+00:00*  
*Collection: `real_docs`*  
*Configuration: LLM=`gemini-flash-lite-latest`, Embeddings=`gemini-embedding-001`, Cosine Threshold=`0.55`, Top-K=`5`*

---

## 1. Executive Summary Performance

| Metric | Track Score (10 Qs) | Wilson 95% Confidence Interval | Benchmark Target |
| :--- | :---: | :---: | :---: |
| **Overall Benchmark Score** | **100.0%** | — | > 85.0% |
| **Answer Accuracy** (Answerable Qs) | **100.0%** (5 Qs) | [56.6%, 100.0%] | > 85.0% |
| **Citation Accuracy** (Exact Page Match) | **100.0%** | [56.6%, 100.0%] | > 80.0% |
| **Fallback Recall** (Abstention on Unanswerable) | **100.0%** (5 Qs) | [56.6%, 100.0%] | > 85.0% |
| **Fallback Precision** | **100.0%** | — | > 90.0% |
| **False Abstentions** | **0** | — | 0 |
| **Average Pipeline Latency** | **2566.2 ms** | Retrieval: 759.8ms, Gen: 1506.3ms | < 25,000 ms |

---

## 2. Per-Question Detailed Breakdown

| ID | Question | Type | Answer | Citation | Pipeline Latency | Retrieval / Gen | Gating Score | Generator Model |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
| 1 | At what age are university faculty members required to retire compared to staff in central government ministries? | Answerable | ✅ Pass | ✅ Pass | 5893ms | 645ms / 2248ms | 0.721 | `gemini-flash-lite-latest` |
| 2 | Can an employee who served for seven years qualify for a central government retirement pension? | Answerable | ✅ Pass | ✅ Pass | 2355ms | 904ms / 1451ms | 0.7697 | `gemini-flash-lite-latest` |
| 3 | What is the statutory ceiling on gratuity payments under the 1972 Gratuity Act? | Answerable | ✅ Pass | ✅ Pass | 2093ms | 927ms / 1166ms | 0.7827 | `gemini-flash-lite-latest` |
| 4 | How much monthly compensation do pensioners living outside Central Government Health Scheme areas receive for medical expenses? | Answerable | ✅ Pass | ✅ Pass | 2029ms | 620ms / 1409ms | 0.756 | `gemini-flash-lite-latest` |
| 5 | Did the Supreme Court characterize pensions as a discretionary bounty or employer grace in the Nakara ruling? | Answerable | ✅ Pass | ✅ Pass | 2105ms | 903ms / 1202ms | 0.8326 | `gemini-flash-lite-latest` |
| 6 | Under the Golden Handshake Scheme, why are surplus employees given 3 months of emoluments per year of service instead of 1.5 months? | Unanswerable (false_premise) | ✅ Pass | ✅ Pass | 1538ms | 616ms / 922ms | 0.7827 | `gemini-flash-lite-latest` |
| 7 | How many months of paid paternity leave can male industrial employees encash during leave travel concession? | Unanswerable (false_premise) | ✅ Pass | ✅ Pass | 3743ms | 924ms / 2820ms | 0.7444 | `gemini-flash-lite-latest` |
| 8 | Which High Court judgment overturned D.S. Nakara v. Union of India to declare pensions a bounty? | Unanswerable (false_premise) | ✅ Pass | ✅ Pass | 1899ms | 550ms / 1349ms | 0.8324 | `gemini-flash-lite-latest` |
| 9 | What annual interest rate is credited on Central Government Provident Fund balances? | Unanswerable (near_miss_unanswerable) | ✅ Pass | ✅ Pass | 1671ms | 597ms / 1074ms | 0.6912 | `gemini-flash-lite-latest` |
| 10 | How many days of casual leave do central government employees receive annually? | Unanswerable (near_miss_unanswerable) | ✅ Pass | ✅ Pass | 2335ms | 912ms / 1422ms | 0.7525 | `gemini-flash-lite-latest` |

---

## 3. Failure Analysis & Diagnoses

🎉 **Zero failures!** All questions passed answer verification, exact citation page matching, and fallback abstention.

