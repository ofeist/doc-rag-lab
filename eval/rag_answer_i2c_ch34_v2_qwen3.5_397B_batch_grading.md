# Manual RAG Answer Grading — I2C Ch34 v2 (colleague questions) / Qwen 3.5 397B FP8 (alias: chat)

Run metadata:
```
eval file:          eval/i2c_ch34_eval_v2.json
output jsonl:       eval/rag_answer_i2c_ch34_v2_qwen3.5_397B_batch.jsonl
chunks file:        data/chunks_i2c_ch34.jsonl
embedding model:    BAAI/bge-small-en-v1.5
focused index:      I2C Ch34 (pages 1375-1458)
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
hit@1: 9/10 = 90.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%
```

---

## Per-Question Grading

### i2c-v2-001 -- PASS
**Question:** Is the master mode supported?
**Answer (865 chars):** Yes, master mode supported (master-transmitter/receiver). Details on bus control, start conditions, baud rate registers.
**Notes:** More detailed than Qwen 3.6 (355 chars). Correct.

### i2c-v2-002 -- PASS
**Question:** What are the supported data transfer rates?
**Answer (310 chars):** Standard (100 kbit/s), Fast (400 kbit/s), High-speed (3.4 Mbit/s) with ranges.
**Notes:** Correct, same quality as Qwen 3.6.

### i2c-v2-003 -- PASS
**Question:** How are the start and stop conditions realized?
**Answer (595 chars):** High-to-low (start), low-to-high (stop) on SDA while SCL high.
**Notes:** Correct, slightly shorter than Qwen 3.6 (782 chars) but complete.

### i2c-v2-004 -- PASS
**Question:** How to do the 10-bit slave addressing?
**Answer (1754 chars):** Step-by-step: ADR field in ADDRCFG, TBAM bit, protocol with preamble.
**Notes:** Excellent — more detailed than Qwen 3.6 (1550 chars).

### i2c-v2-005 -- FAIL
**Question:** Which register is used to select the operational mode?
**Answer (563 chars):** "Context not sufficient" — doesn't identify RUN bit.
**Notes:** Qwen 3.6 correctly answered RUN bit (312 chars). Qwen 3.5 missed it even though page 1429 was retrieved (RUN bit description is there). This is a model miss.

### i2c-v2-006 -- PASS
**Question:** Which bit is used to trigger the data transmission?
**Answer (598 chars):** TPS bit-field in TPSCTRL register.
**Notes:** Correct, similar to Qwen 3.6 (423 chars).

### i2c-v2-007 -- PASS
**Question:** What is the address of the Identification Register?
**Answer (277 chars):** MODID at 10004H, ID at 00008H.
**Notes:** Correct, concise.

### i2c-v2-008 -- PARTIAL
**Question:** What does GCE bit of ADDRCFG register represent?
**Answer (286 chars):** Says GCE not in context. Mentions MCE, SOPE instead.
**Notes:** Same as Qwen 3.6 — GCE description likely in a chunk not retrieved. Retrieval issue.

### i2c-v2-009 -- PARTIAL
**Question:** Which interrupts are recommended to be enabled?
**Answer (978 chars):** Says context doesn't state "recommended". Lists reset defaults.
**Notes:** Valid gap — manual describes defaults, not recommendations. Same as Qwen 3.6.

### i2c-v2-010 -- PASS
**Question:** If the receive interrupt is not being triggered, what should be checked first?
**Answer (939 chars):** Check IMSC (Interrupt Mask Control Register) first.
**Notes:** **Better than Qwen 3.6** — Qwen 3.6 said "context not sufficient" (63 chars). Qwen 3.5 found the answer about RIS vs MIS registers.

---

## Summary

| Result   | Count | IDs                                      |
|----------|-------|------------------------------------------|
| PASS     | 7     | v2-001, v2-002, v2-003, v2-004, v2-006, v2-007, v2-010 |
| PARTIAL  | 2     | v2-008, v2-009                          |
| FAIL     | 1     | v2-005                                  |
| **Total**| **10**|                                          |

**Pass rate (PASS + PARTIAL): 90%**
**Strict pass rate (PASS only): 70%**

---

## Comparison: Qwen 3.5 vs Qwen 3.6 (v2 questions)

| Question | Qwen 3.6 | Qwen 3.5 | Notes |
|----------|----------|----------|-------|
| v2-001 | PASS (355) | PASS (865) | Qwen 3.5 more detailed |
| v2-002 | PASS (307) | PASS (310) | Same |
| v2-003 | PASS (782) | PASS (595) | Both correct |
| v2-004 | PASS (1550) | PASS (1754) | Qwen 3.5 more detailed |
| v2-005 | PASS (312) | **FAIL** (563) | Qwen 3.5 missed RUN bit |
| v2-006 | PASS (423) | PASS (598) | Both correct |
| v2-007 | PASS (406) | PASS (277) | Both correct |
| v2-008 | PARTIAL (609) | PARTIAL (286) | Both retrieval issue |
| v2-009 | PARTIAL (903) | PARTIAL (978) | Both valid gap |
| v2-010 | PARTIAL (63) | PASS (939) | Qwen 3.5 found answer |

**Total chars:** Qwen 3.6: ~5,600 | Qwen 3.5: ~7,100

Qwen 3.5 is more verbose overall (+27%) but missed one question (v2-005) that Qwen 3.6 got right.

---

## Findings

1. **v2-005 (RUN bit):** Qwen 3.5 failed where Qwen 3.6 succeeded. Page 1429 was retrieved but model didn't extract the RUN bit info. This is a model reasoning gap.
2. **v2-010 (receive interrupt):** Qwen 3.5 succeeded where Qwen 3.6 failed. Found IMSC/RIS/MIS register relationship.
3. **v2-008 (GCE bit):** Both models have the same retrieval issue — chunk with GCE description not in top-5.
4. **No hallucinations** — both models flag insufficient context appropriately.

---

## Recommendations

- **v2-005:** Consider if "operational mode" question is ambiguous (could mean master/slave OR config/run). If RUN bit is the expected answer, re-chunking might help surface it.
- **v2-008:** Re-chunk with smaller size (500/80) to capture ADDRCFG register description in one chunk.
- **Model choice:** Qwen 3.6 is more reliable for register-level questions; Qwen 3.5 is better for troubleshooting synthesis. Trade-off.
