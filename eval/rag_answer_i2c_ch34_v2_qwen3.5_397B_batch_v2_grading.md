# Manual RAG Answer Grading — I2C Ch34 v2 (colleague questions) / Qwen 3.5 397B FP8 (alias: chat) — v2 chunks (500/80)

Run metadata:
```
eval file:          eval/i2c_ch34_eval_v2.json
output jsonl:       eval/rag_answer_i2c_ch34_v2_qwen3.5_397B_batch_v2.jsonl
chunks file:        data/chunks_i2c_ch34_v2.jsonl (500/80 chunking)
embedding model:    BAAI/bge-small-en-v1.5
focused index:      I2C_Ch34_v2
retrieval mode:     hybrid (RRF)
top_k: 5, candidate_k: 12, rrf_k: 60
model:              chat (Qwen 3.5 397B FP8)
base_url:           http://106.106.152.161:4000/v1
max_tokens:         2000
date:               2026-05-26
grader:             manual
```

---

## Retrieval Baseline

```
mode: hybrid, top-k: 5, candidate-k: 12, rrf-k: 60
hit@1: 8/10 = 80.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%
```

---

## Per-Question Grading

### i2c-v2-001 -- PASS
**Question:** Is the master mode supported?
**Answer:** Yes, master mode supported with details on states, restrictions, multi-master collision handling.
**Notes:** Correct, comprehensive answer.

### i2c-v2-002 -- PASS
**Question:** What are the supported data transfer rates?
**Answer:** Standard (100 kbit/s), Fast (400 kbit/s), High-speed (3.4 Mbit/s) with ranges.
**Notes:** Correct.

### i2c-v2-003 -- PASS
**Question:** How are the start and stop conditions realized?
**Answer:** High-to-low (start), low-to-high (stop) on SDA while SCL high.
**Notes:** Correct.

### i2c-v2-004 -- PASS
**Question:** How to do the 10-bit slave addressing?
**Answer:** Step-by-step with preamble, TBAM bit, protocol details.
**Notes:** Excellent detailed answer.

### i2c-v2-005 -- FAIL
**Question:** Which register is used to select the operational mode?
**Answer:** "Context not sufficient" — doesn't identify RUN bit.
**Notes:** **Model miss** — stranica 1429 je na #1 u retrievalu, sadrži RUN bit opis. Qwen 3.5 ne ekstrahira informaciju.

### i2c-v2-006 -- FAIL
**Question:** Which bit is used to trigger the data transmission?
**Answer:** "Context not sufficient" — ne identificira TPS bit.
**Notes:** **Model miss** — stranica 1396 je u top-5, TPSCTRL register je spomenut ali model ne prepoznaje TPS bit-field kao odgovor.

### i2c-v2-007 -- PASS
**Question:** What is the address of the Identification Register?
**Answer:** MODID at 10004H, ID at 00008H.
**Notes:** Correct.

### i2c-v2-008 -- PASS ✅
**Question:** What does GCE bit of ADDRCFG register represent?
**Answer:** GCE = General Call Enable, enables reaction to general call address (0x00).
**Notes:** **FIXED!** Prije (800/120 chunking) retrieval miss — sada s 500/80 chunkingom GCE opis je u chunku i model ga nalazi.

### i2c-v2-009 -- PARTIAL
**Question:** Which interrupts are recommended to be enabled?
**Answer:** Context doesn't state "recommended", lists reset defaults.
**Notes:** Valid gap — manual describes defaults, not recommendations.

### i2c-v2-010 -- PARTIAL
**Question:** If the receive interrupt is not being triggered, what should be checked first?
**Answer:** "Context not sufficient" — no troubleshooting procedure in manual.
**Notes:** Valid gap — manual doesn't have troubleshooting sections.

---

## Summary

| Result   | Count | IDs                                      |
|----------|-------|------------------------------------------|
| PASS     | 6     | v2-001, v2-002, v2-003, v2-004, v2-007, v2-008 |
| PARTIAL  | 2     | v2-009, v2-010                          |
| FAIL     | 2     | v2-005, v2-006                          |
| **Total**| **10**|                                          |

**Pass rate (PASS + PARTIAL): 80%**
**Strict pass rate (PASS only): 60%**

---

## Comparison: Qwen 3.5 v2 chunks (500/80) vs original (800/120)

| Question | Original (800/120) | v2 chunks (500/80) | Notes |
|----------|-------------------|-------------------|-------|
| v2-001 | PASS | PASS | Same |
| v2-002 | PASS | PASS | Same |
| v2-003 | PASS | PASS | Same |
| v2-004 | PASS | PASS | Same |
| v2-005 | FAIL | FAIL | Isti model miss — RUN bit |
| v2-006 | PASS | **FAIL** | **Regression!** TPS bit sada miss |
| v2-007 | PASS | PASS | Same |
| v2-008 | **FAIL** (retrieval) | **PASS** ✅ | **FIXED!** GCE bit sada u chunku |
| v2-009 | PARTIAL | PARTIAL | Same |
| v2-010 | PARTIAL | PARTIAL | Same |

**Total chars:** Original: ~7,100 | v2 chunks: ~6,800

---

## Findings

1. **v2-008 (GCE bit) — FIXED:** Re-chunking na 500/80 je riješio retrieval problem. GCE opis je sada u chunku koji se retrieva.

2. **v2-006 (TPS bit) — REGRESSION:** S 800/120 na 500/80, TPS bit informacija je vjerojatno razbijena na više chunkova ili manje istaknuta. Model ne ekstrahira.

3. **v2-005 (RUN bit) — PERSISTENT MODEL MISS:** Stranica 1429 je na #1 u retrievalu, ali Qwen 3.5 ne ekstrahira RUN bit informaciju. Ovo je model reasoning gap, ne retrieval problem.

4. **Retrieval je savršen (100% hit@3):** Sve očekivane stranice su u top-5. Preostala 2 FAIL-a su čisti model miss-ovi.

---

## Recommendations

1. **v2-005 (RUN bit):** Prompt engineering — dodati eksplicitnu instrukciju: "When asked about operational/configuration/run mode, search for RUN, CONFIG, ENABLE bits in retrieved chunks."

2. **v2-006 (TPS bit):** Provjeriti chunking — TPSCTRL register description je vjerojatno razbijen. Možda koristiti 600/100 umjesto 500/80 za bolši balance.

3. **Model choice za register-level questions:** Qwen 3.6 27B je pouzdaniji za bit-level identifikaciju (7/10 PASS strict vs Qwen 3.5: 6/10 s 500/80 chunkingom).

4. **Najbolji put do 10/10:**
   - Qwen 3.6 27B + 500/80 chunking = vjerojatno 9-10/10 PASS
   - Ili Qwen 3.5 + prompt tweak za register questions
