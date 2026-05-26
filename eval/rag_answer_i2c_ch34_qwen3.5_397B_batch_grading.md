# Manual RAG Answer Grading — I2C Ch34 / Qwen 3.5 397B FP8 (alias: chat)

Run metadata:
```
eval file:          eval/i2c_ch34_eval.json
output jsonl:       eval/rag_answer_i2c_ch34_qwen3.5_397B_batch.jsonl
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

## Per-Question Grading

### i2c-001 -- PASS
**Question:** Which I2C operating modes are supported by the AURIX TC3xx I2C module?
**Answer:** Lists master, multi-master (with restrictions), and slave modes with citations [S1], [S3].
**Notes:** Correct, concise, grounded.

### i2c-002 -- PASS
**Question:** Which I2C speed ranges are supported and what are their maximum data rates?
**Answer:** Lists standard (100 kbit/s), fast (400 kbit/s), high-speed (3.4 Mbit/s) with exact ranges.
**Notes:** Complete and accurate.

### i2c-003 -- PASS
**Question:** What address formats are supported by the I2C module?
**Answer:** Describes 7-bit and 10-bit addressing, mentions compatibility and simultaneous use.
**Notes:** Accurate, well-structured.

### i2c-004 -- PASS
**Question:** What low-level I2C bus tasks can the module execute automatically?
**Answer:** Lists (de)serialization, start/stop, ACK, bus state detection, arbitration, address recognition, general call, repeated start.
**Notes:** Complete enumeration from S1/Feature List.

### i2c-005 -- PARTIAL
**Question:** How are SDA and SCL used and what is their idle state?
**Answer:** Detailed explanation of SDA/SCL usage (data transmission, timing, start/stop conditions, ACK, clock stretching, arbitration). **Idle state:** Notes that bus is "free" after stop condition but context doesn't explicitly state static voltage levels.
**Notes:** 1438 chars — very detailed on usage, but idle state ("both lines high") is not in retrieved chunks. Model correctly flags insufficient context rather than hallucinating. Same issue as Qwen 3.6 — retrieval problem, not model.

### i2c-006 -- PASS
**Question:** What role does the FIFO play in I2C transmit and receive data transfer?
**Answer:** Comprehensive — 2623 chars covering buffering (8 stages, 32-bit), flow control, TX/RX data staging, packet management, request generation (BREQ/LBREQ/SREQ/LSREQ), error handling, DMA integration.
**Notes:** Best answer in the set — more detailed than Qwen 3.6 (1664 chars). Excellent multi-source synthesis.

### i2c-007 -- PASS
**Question:** Which interrupt categories or sources are described for the I2C module?
**Answer:** Three categories (DTR_INT, ERR_INT, P_INT) with signal names and source lists.
**Notes:** Accurate and well-organized.

### i2c-008 -- PARTIAL
**Question:** How is the I2C kernel clock and bit rate generated?
**Answer:** "Derived from system clock via a prescaler. Subsequently, an additional fractional divider is used to generate the desired bit rate [S1]." (164 chars)
**Notes:** Same short answer as Qwen 3.6. Retrieval problem — page 1383 (FDIVCFG, FDIVHIGHCFG, TIMCFG details) not in top-5. Feature list summary (page 1377) has only high-level mention.

### i2c-009 -- PASS
**Question:** What does the documentation say about multi-master operation and arbitration?
**Answer:** Covers arbitration mechanism (wired AND, SDA comparison), stages, outcome (AL request, LISTENING state), functional restrictions (master collision, hold time violation, high-speed mode limitation).
**Notes:** Excellent — 2328 chars, includes functional restrictions.

### i2c-010 -- PASS
**Question:** What are the main CPU offload benefits of the I2C module?
**Answer:** Covers time-critical task relief, automatic low-level tasks, FIFO buffering with DMA support, interrupt handling.
**Notes:** Good synthesis across multiple sources.

---

## Summary

| Result   | Count | IDs                                      |
|----------|-------|------------------------------------------|
| PASS     | 8     | 001, 002, 003, 004, 006, 007, 009, 010 |
| PARTIAL  | 2     | 005, 008                                |
| FAIL     | 0     | —                                        |
| **Total**| **10**|                                          |

**Pass rate (PASS + PARTIAL): 100%**
**Strict pass rate (PASS only): 80%**

---

## Comparison: Qwen 3.5 vs Qwen 3.6

| Question | Qwen 3.6 (code) | Qwen 3.5 (chat) | Notes |
|----------|-----------------|-----------------|-------|
| i2c-001 | 483 chars | 374 chars | Both PASS |
| i2c-002 | 344 chars | 581 chars | Qwen 3.5 more detailed |
| i2c-003 | 815 chars | 677 chars | Both PASS |
| i2c-004 | 471 chars | 774 chars | Qwen 3.5 more detailed |
| i2c-005 | 1221 chars | 1438 chars | Both PARTIAL (idle state missing) |
| i2c-006 | 1664 chars | 2623 chars | Qwen 3.5 significantly more detailed |
| i2c-007 | 913 chars | 1333 chars | Qwen 3.5 more detailed |
| i2c-008 | 154 chars | 164 chars | Both PARTIAL (retrieval issue) |
| i2c-009 | 2285 chars | 2328 chars | Both PASS |
| i2c-010 | 1108 chars | 1044 chars | Both PASS |

**Total chars:** Qwen 3.6: ~8,400 | Qwen 3.5: ~10,300

Qwen 3.5 produces more verbose answers overall, especially on i2c-006 (FIFO) which is 57% longer.

---

## Findings

1. **Strengths:** Qwen 3.5 produces grounded, well-structured answers with consistent citations. Multi-source synthesis is excellent (i2c-006, i2c-009). Correctly flags insufficient context (i2c-005) rather than hallucinating.
2. **i2c-005 (SDA/SCL):** Idle state ("both lines pulled high") is in the PDF but not in top-5 retrieved chunks. Same issue as Qwen 3.6 — retrieval problem.
3. **i2c-008 (clock/bitrate):** Same one-line answer as Qwen 3.6. Retrieval brings only Feature List summary (page 1377), not detailed baudrate generation section (page 1383).
4. **No hallucinations detected** across all 10 answers.
5. **Citation format:** Consistent [S1], [S2], etc. throughout.
6. **Verbosity:** Qwen 3.5 is ~23% more verbose overall, with significantly more detail on FIFO (i2c-006) and interrupts (i2c-007).

---

## Recommendations

- **max_tokens=2000** is required for reasoning models in this family.
- **i2c-005 & i2c-008:** Both are retrieval failures, not model failures. Re-chunking with smaller chunk_size (e.g., 500 tokens instead of 800) may create denser chunks where idle state and baudrate details are more prominent for retrieval.
- **Overall:** Qwen 3.5 397B is a strong performer for this RAG task. Hybrid retrieval at top-k=5 / candidate-k=12 is a good default.
