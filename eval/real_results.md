# Real-World Benchmark (Public PDF Track v1)

*Run timestamp: 2026-10-30T17:21:53.211620+00:00*  
*Collection: `real_docs`*  
*Configuration: LLM=`gemini-flash-lite-latest`, Embeddings=`gemini-embedding-001`, Cosine Threshold=`0.55`, Top-K=`5`*

---

## 1. Executive Summary Performance

| Metric | Track Score (15 Qs) | Wilson 95% Confidence Interval | Benchmark Target |
| :--- | :---: | :---: | :---: |
| **Overall Benchmark Score** | **100.0%** | — | > 85.0% |
| **Answer Accuracy** (Answerable Qs) | **100.0%** (12 Qs) | [75.8%, 100.0%] | > 85.0% |
| **Citation Accuracy** (Exact Page Match) | **100.0%** | [75.8%, 100.0%] | > 80.0% |
| **Fallback Recall** (Abstention on Unanswerable) | **100.0%** (3 Qs) | [43.9%, 100.0%] | > 85.0% |
| **Fallback Precision** | **100.0%** | — | > 90.0% |
| **False Abstentions** | **0** | — | 0 |
| **Average Pipeline Latency** | **3211.9 ms** | Retrieval: 833.1ms, Gen: 2378.7ms | < 25,000 ms |

---

## 2. Per-Question Detailed Breakdown

| ID | Question | Type | Answer | Citation | Pipeline Latency | Retrieval / Gen | Gating Score | Generator Model |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
| 1 | What retirement age did the Fifth Central Pay Commission fix for central government employees and for university teachers? | Answerable | ✅ Pass | ✅ Pass | 2466ms | 642ms / 1824ms | 0.7477 | `gemini-flash-lite-latest` |
| 2 | How many years of qualifying service are needed to receive a government pension? | Answerable | ✅ Pass | ✅ Pass | 2085ms | 613ms / 1472ms | 0.787 | `gemini-flash-lite-latest` |
| 3 | What portion of their pension can central government employees commute? | Answerable | ✅ Pass | ✅ Pass | 4812ms | 912ms / 3900ms | 0.7846 | `gemini-flash-lite-latest` |
| 4 | Under the Payment of Gratuity Act, 1972, what is the gratuity rate and the maximum amount? | Answerable | ✅ Pass | ✅ Pass | 2461ms | 733ms / 1727ms | 0.8081 | `gemini-flash-lite-latest` |
| 5 | How many years of continuous service does the Payment of Gratuity Act require, and how many employees must the establishment have? | Answerable | ✅ Pass | ✅ Pass | 4975ms | 923ms / 4052ms | 0.7844 | `gemini-flash-lite-latest` |
| 6 | What is the maximum maternity leave that counts toward the period of employment for gratuity? | Answerable | ✅ Pass | ✅ Pass | 4392ms | 913ms / 3479ms | 0.8321 | `gemini-flash-lite-latest` |
| 7 | What medical allowance did the Fifth Pay Commission suggest for pensioners not covered by CGHS? | Answerable | ✅ Pass | ✅ Pass | 2337ms | 974ms / 1362ms | 0.8427 | `gemini-flash-lite-latest` |
| 8 | What quantum of family pension did the Fifth Pay Commission retain? | Answerable | ✅ Pass | ✅ Pass | 2115ms | 583ms / 1532ms | 0.8535 | `gemini-flash-lite-latest` |
| 9 | What was the revised earned-leave entitlement for industrial employees with eleven to twenty years of service? | Answerable | ✅ Pass | ✅ Pass | 3030ms | 657ms / 2374ms | 0.783 | `gemini-flash-lite-latest` |
| 10 | How many days of earned leave can industrial employees accumulate, and how much can be encashed during service? | Answerable | ✅ Pass | ✅ Pass | 3602ms | 772ms / 2830ms | 0.8089 | `gemini-flash-lite-latest` |
| 11 | What ex-gratia amount does the Golden Handshake Scheme give employees identified as surplus? | Answerable | ✅ Pass | ✅ Pass | 6645ms | 1597ms / 5048ms | 0.7795 | `gemini-flash-lite-latest` |
| 12 | Which Supreme Court case on pensions is cited, and what did the Court hold about the nature of pension? | Answerable | ✅ Pass | ✅ Pass | 2693ms | 703ms / 1990ms | 0.7911 | `gemini-flash-lite-latest` |
| 13 | What is the employer contribution percentage under the New Pension Scheme? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 2220ms | 1014ms / 1206ms | 0.7321 | `gemini-flash-lite-latest` |
| 14 | What is the minimum monthly pension amount for a central government employee? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 2056ms | 736ms / 1320ms | 0.7988 | `gemini-flash-lite-latest` |
| 15 | How many days of paternity leave do central government employees get? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 2289ms | 725ms / 1564ms | 0.7247 | `gemini-flash-lite-latest` |

---

## 3. Failure Analysis & Diagnoses

🎉 **Zero failures!** All questions passed answer verification, exact citation page matching, and fallback abstention.

