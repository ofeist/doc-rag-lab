# Manual RAG Answer Grading — I2C Ch34 v2 (colleague questions) / Qwen 3.6 27B FP8 (alias: code) — v2 chunks (500/80)

Run metadata:
```
eval file:          eval/i2c_ch34_eval_v2.json
output jsonl:       eval/rag_answer_i2c_ch34_v2_qwen3.6_27B_batch_v2.jsonl
chunks file:        data/chunks_i2c_ch34_v2.jsonl (500/80 chunking)
embedding model:    BAAI/bge-small-en-v1.5
focused index:      I2C_Ch34_v2
retrieval mode:     hybrid (RRF)
top_k: 5, candidate_k: 12, rrf_k: 60
model:              code (Qwen 3.6 27B FP8)
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
**Answer:** Yes, master mode supported with multi-master details and restrictions.
**Notes:** Correct.

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
**Answer:** Step-by-step with preamble, TBAM bit, protocol details including read operation.
**Notes:** Excellent.

### i2c-v2-005 -- PASS ✅
**Question:** Which register is used to select the operational mode?
**Answer:** Identifies CLC1 register for clock control modes (DISR, SPEN) and mentions RUN bit for Configuration/Run mode.
**Notes:** **FIXED!** Qwen 3.6 identificira RUN bit i CLC1 register — Qwen 3.5 je FAIL na istom pitanju i istim chunkovima.

### i2c-v2-006 -- PASS ✅
**Question:** Which bit is used to trigger the data transmission?
**Answer:** MRPS bit-field in MRPSCTRL register for master-receiver, plus TPSCTRL for slave-transmitter.
**Notes:** **FIXED!** Qwen 3.6 identificira oba trigger bita — Qwen 3.5 je FAIL.

### i2c-v2-007 -- PASS
**Question:** What is the address of the Identification Register?
**Answer:** ID at 00008H (primary), MODID at 10004H.
**Notes:** Correct.

### i2c-v2-008 -- PASS ✅
**Question:** What does GCE bit of ADDRCFG register represent?
**Answer:** GCE = general call address matching enable, reacts to general call address (0x00).
**Notes:** **FIXED!** Re-chunking + Qwen 3.6 = PASS.

### i2c-v2-009 -- PARTIAL
**Question:** Which interrupts are recommended to be enabled?
**Answer:** Lists reset states for protocol/error interrupts.
**Notes:** Valid gap — manual ne daje preporuke, samo default vrijednosti.

### i2c-v2-010 -- PARTIAL
**Question:** If the receive interrupt is not being triggered, what should be checked first?
**Answer:** "Context not sufficient" — no troubleshooting procedure.
**Notes:** Valid gap — manual nema troubleshooting sekcije.

---

## Summary

| Result   | Count | IDs                                      |
|----------|-------|------------------------------------------|
| PASS     | 8     | v2-001, v2-002, v2-003, v2-004, v2-005, v2-006, v2-007, v2-008 |
| PARTIAL  | 2     | v2-009, v2-010                          |
| FAIL     | 0     | —                                        |
| **Total**| **10**|                                          |

**Pass rate (PASS + PARTIAL): 100%**
**Strict pass rate (PASS only): 80%**

---

## Comparison: Qwen 3.6 v2 chunks (500/80) vs original (800/120)

| Question | Original (800/120) | v2 chunks (500/80) | Notes |
|----------|-------------------|-------------------|-------|
| v2-001 | PASS | PASS | Same |
| v2-002 | PASS | PASS | Same |
| v2-003 | PASS | PASS | Same |
| v2-004 | PASS | PASS | Same |
| v2-005 | PASS | PASS | Same |
| v2-006 | PASS | PASS | Same |
| v2-007 | PASS | PASS | Same |
| v2-008 | **PARTIAL** | **PASS** ✅ | **FIXED!** GCE bit sada u chunku |
| v2-009 | PARTIAL | PARTIAL | Same |
| v2-010 | PARTIAL | PARTIAL | Same |

**Total chars:** Original: ~5,600 | v2 chunks: ~5,400

---

## Final Comparison Table: Qwen 3.6 vs Qwen 3.5 (500/80 chunks)

| Question | Qwen 3.6 (code) | Qwen 3.5 (chat) | Notes |
|----------|-----------------|-----------------|-------|
| v2-001 | PASS | PASS | Same |
| v2-002 | PASS | PASS | Same |
| v2-003 | PASS | PASS | Same |
| v2-004 | PASS | PASS | Same |
| v2-005 | **PASS** ✅ | FAIL | Qwen 3.6 bolje za bit-level |
| v2-006 | **PASS** ✅ | FAIL | Qwen 3.6 bolje za bit-level |
| v2-007 | PASS | PASS | Same |
| v2-008 | **PASS** ✅ | **PASS** ✅ | Oba PASS s 500/80 |
| v2-009 | PARTIAL | PARTIAL | Same |
| v2-010 | PARTIAL | PARTIAL | Same |

**Qwen 3.6:** 8 PASS, 2 PARTIAL, 0 FAIL (100% pass rate)
**Qwen 3.5:** 6 PASS, 2 PARTIAL, 2 FAIL (80% pass rate)

---

## Findings

1. **Qwen 3.6 27B + 500/80 chunks = 100% pass rate** — najbolja kombinacija
2. **v2-005 (RUN bit):** Qwen 3.6 ga nalazi, Qwen 3.5 ne — iako je retrieval identičan (stranica 1429 na #1)
3. **v2-006 (TPS bit):** Qwen 3.6 identificira MRPS i TPSCTRL, Qwen 3.5 ne
4. **v2-008 (GCE bit):** Re-chunking na 500/80 je riješio retrieval problem za oba modela
5. **v2-009, v2-010:** Inherentni gap-ovi u dokumentaciji, ne RAG problem

---

## Recommendations

1. **Koristiti Qwen 3.6 27B (code)** za register-level/bit-level pitanja — pouzdaniji za bit-level ekstrakciju
2. **Zadržati 500/80 chunking** — popravlja GCE bit retrieval bez regressija na ostalim pitanjima
3. **v2-009, v2-010:** Prihvatiti kao PARTIAL — nisu odgovarajuća pitanja za ovu dokumentaciju
4. **Qwen 3.5 (chat)** je manje pouzdan za bit-level zadatke (2 FAIL na 10) — koristiti oprezno
