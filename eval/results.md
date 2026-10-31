# Synthetic Benchmark (Northwind Labs Track)

*Run timestamp: 2026-10-30T17:20:16.023559+00:00*  
*Collection: `default`*  
*Configuration: LLM=`gemini-flash-lite-latest`, Embeddings=`gemini-embedding-001`, Cosine Threshold=`0.55`, Top-K=`5`*

---

## 1. Executive Summary Performance

| Metric | Combined (30 Qs) | Dev Split (10 Qs) | Test Split (20 Qs) | Wilson 95% CI (Combined) |
| :--- | :---: | :---: | :---: | :---: |
| **Overall Benchmark Score** | **97.5%** | **100.0%** | **96.7%** | — |
| **Answer Accuracy** (Answerable Qs) | 100.0% | 100.0% | 100.0% | [85.1%, 100.0%] |
| **Citation Accuracy** (Exact Page Match) | 100.0% | 100.0% | 100.0% | [85.1%, 100.0%] |
| **Fallback Recall** (Abstention Rate) | 87.5% | 100.0% | 83.3% | [52.9%, 97.8%] |
| **Fallback Precision** | 100.0% | 100.0% | 100.0% | — |
| **False Abstentions** | 0 | 0 | 0 | — |
| **Average Pipeline Latency** | 3089.7 ms | 2231.7 ms | 3518.7 ms | Retrieval: 823.0ms, Gen: 1966.6ms |

---

## 2. Per-Question Detailed Breakdown

| ID | Question | Type | Answer | Citation | Pipeline Latency | Retrieval / Gen | Gating Score | Generator Model |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
| 1 | How many days of paid vacation do new employees receive per year? | Answerable | ✅ Pass | ✅ Pass | 2899ms | 1088ms / 1811ms | 0.7789 | `gemini-flash-lite-latest` |
| 2 | How long is the initial probationary period for new hires at Northwind Labs? | Answerable | ✅ Pass | ✅ Pass | 2274ms | 653ms / 1621ms | 0.8432 | `gemini-flash-lite-latest` |
| 3 | What are the core collaboration hours when employees must be online? | Answerable | ✅ Pass | ✅ Pass | 1986ms | 651ms / 1335ms | 0.7229 | `gemini-flash-lite-latest` |
| 4 | How many days per week are hybrid employees permitted to work remotely? | Answerable | ✅ Pass | ✅ Pass | 2338ms | 609ms / 1729ms | 0.6984 | `gemini-flash-lite-latest` |
| 5 | What is the minimum internet speed required for remote workers? | Answerable | ✅ Pass | ✅ Pass | 2821ms | 689ms / 2132ms | 0.6395 | `gemini-flash-lite-latest` |
| 6 | How many unused vacation days can be rolled over to the next calendar year? | Answerable | ✅ Pass | ✅ Pass | 3610ms | 654ms / 2955ms | 0.7333 | `gemini-flash-lite-latest` |
| 7 | How many paid sick days do full-time employees receive annually? | Answerable | ✅ Pass | ✅ Pass | 2730ms | 1026ms / 1704ms | 0.7416 | `gemini-flash-lite-latest` |
| 8 | When is a doctor's note required for consecutive sick leave absences? | Answerable | ✅ Pass | ✅ Pass | 2325ms | 655ms / 1670ms | 0.6769 | `gemini-flash-lite-latest` |
| 9 | How many weeks of paid parental leave do primary caregivers receive? | Answerable | ✅ Pass | ✅ Pass | 7169ms | 577ms / 3591ms | 0.78 | `gemini-3-flash-preview` |
| 10 | How many days of paid bereavement leave are provided for immediate family members? | Answerable | ✅ Pass | ✅ Pass | 2005ms | 953ms / 1052ms | 0.7474 | `gemini-flash-lite-latest` |
| 11 | How much paid leave does Northwind Labs provide for jury duty? | Answerable | ✅ Pass | ✅ Pass | 6818ms | 995ms / 5823ms | 0.8459 | `gemini-flash-lite-latest` |
| 12 | What is the individual deductible under the Premier PPO medical plan? | Answerable | ✅ Pass | ✅ Pass | 1845ms | 651ms / 1194ms | 0.7256 | `gemini-flash-lite-latest` |
| 13 | How much does the company contribute annually to an individual HSA under the HDHP? | Answerable | ✅ Pass | ✅ Pass | 2562ms | 934ms / 1627ms | 0.8028 | `gemini-flash-lite-latest` |
| 14 | What percentage does Northwind Labs match on employee 401(k) contributions? | Answerable | ✅ Pass | ✅ Pass | 2338ms | 997ms / 1341ms | 0.8512 | `gemini-flash-lite-latest` |
| 15 | What is the vesting schedule for employer 401(k) matching contributions? | Answerable | ✅ Pass | ✅ Pass | 2254ms | 975ms / 1279ms | 0.7175 | `gemini-flash-lite-latest` |
| 16 | What is the monthly reimbursement amount for the wellness and fitness stipend? | Answerable | ✅ Pass | ✅ Pass | 2045ms | 960ms / 1084ms | 0.7828 | `gemini-flash-lite-latest` |
| 17 | What is the annual reimbursement limit for tuition and professional learning? | Answerable | ✅ Pass | ✅ Pass | 4685ms | 748ms / 3937ms | 0.7239 | `gemini-flash-lite-latest` |
| 18 | How many free counseling sessions are provided through Lyra Health EAP? | Answerable | ✅ Pass | ✅ Pass | 1555ms | 645ms / 910ms | 0.7676 | `gemini-flash-lite-latest` |
| 19 | What is the maximum allowed value for gifts received from vendors or clients? | Answerable | ✅ Pass | ✅ Pass | 4531ms | 1004ms / 3527ms | 0.7669 | `gemini-flash-lite-latest` |
| 20 | What are the corporate requirements for employee password length and complexity? | Answerable | ✅ Pass | ✅ Pass | 1662ms | 594ms / 1068ms | 0.7618 | `gemini-flash-lite-latest` |
| 21 | Within how many minutes of inactivity must corporate laptops automatically lock? | Answerable | ✅ Pass | ✅ Pass | 2361ms | 940ms / 1422ms | 0.7342 | `gemini-flash-lite-latest` |
| 22 | Within how many hours must a suspected security incident or breach be reported? | Answerable | ✅ Pass | ✅ Pass | 1607ms | 651ms / 956ms | 0.7254 | `gemini-flash-lite-latest` |
| 23 | What is Northwind Labs' stock ticker symbol on NASDAQ? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 2144ms | 661ms / 1483ms | 0.7099 | `gemini-flash-lite-latest` |
| 24 | Can employees bring pet dogs into the office on Casual Fridays? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 1551ms | 595ms / 955ms | 0.6665 | `gemini-flash-lite-latest` |
| 25 | What is the corporate reimbursement policy for business class international flights? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 2247ms | 1254ms / 992ms | 0.6562 | `gemini-flash-lite-latest` |
| 26 | Does Northwind Labs offer a relocation assistance package for moving to the Tokyo office? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 2359ms | 1030ms / 1329ms | 0.7244 | `gemini-flash-lite-latest` |
| 27 | What is the personal mobile phone number of the Chief Executive Officer? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 2252ms | 932ms / 1321ms | 0.673 | `gemini-flash-lite-latest` |
| 28 | How much corporate discount do employees get when buying Apple MacBooks through the company store? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 7123ms | 956ms / 3166ms | 0.646 | `gemini-3-flash-preview` |
| 29 | Does Northwind Labs provide free catered lunch on Wednesdays? | Unanswerable (standard) | ✅ Pass | ✅ Pass | 7899ms | 978ms / 3921ms | 0.7618 | `gemini-flash-lite-latest` |
| 30 | Can a new employee who has been with the company for only 2 months take paid parental leave? | Unanswerable (standard) | ❌ Fail | ➖ N/A | 2697ms | 636ms / 2061ms | 0.7504 | `gemini-flash-lite-latest` |

---

## 3. Failure Analysis & Diagnoses

Found **1 failure(s)** during this evaluation run:

### Question 30: Can a new employee who has been with the company for only 2 months take paid parental leave?
- **Type**: `Unanswerable`
- **Diagnosis**: False Positive (Failed to Abstain): Question 30 was expected to trigger fallback, but the system generated an answer (model gemini-flash-lite-latest). Gating similarity score 0.7504 exceeded threshold 0.55, and Layer 2 grounding did not recognize out-of-scope/false-premise boundaries.
- **Expected**: Fallback abstention message
- **Actual**: No, to qualify for paid parental leave, employees must have completed a minimum of 6 months of continuous full-time service prior to the qualifying event [1].

