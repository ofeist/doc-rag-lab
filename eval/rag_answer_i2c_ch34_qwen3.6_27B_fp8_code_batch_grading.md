# Manual RAG Answer Grading — I2C Ch34 / code (Qwen 3.6 27B FP8)

Run metadata:
```
eval file:          eval/i2c_ch34_eval.json
output jsonl:       eval/rag_answer_i2c_ch34_qwen3.6_27B_fp8_code_batch.jsonl
chunks file:        data/chunks_i2c_ch34.jsonl
embedding model:    BAAI/bge-small-en-v1.5
focused index:      I2C Ch34 (pages 1375-1458)
retrieval mode:     hybrid (RRF)
top_k: 5, candidate_k: 12, rrf_k: 60
model:              code (Qwen 3.6 27B FP8)
base_url:           http://106.106.152.161:4000/v1
max_tokens:         900
date:               2026-05-26
grader:             manual
```

---

## Per-Question Grading

### i2c-001 -- PASS
**Question:** Which I2C operating modes are supported by the AURIX TC3xx I2C module?
**Retrieved:** pages 1375, 1422, 1383, 1429, 1416
**Answer:** Lists master, multi-master, and slave modes with source citations [S1], [S3].
**Notes:** Correct, concise, grounded in S1 (Feature List). Mentions speed ranges as bonus.

### i2c-002 -- PASS
**Question:** Which I2C speed ranges are supported and what are their maximum data rates?
**Retrieved:** pages 1377, 1382, 1375, 1383, 1376
**Answer:** Lists standard (100 kbit/s), fast (400 kbit/s), high-speed (3.4 Mbit/s) with exact ranges.
**Notes:** Complete and accurate with specific numbers from S1 and S3.

### i2c-003 -- PASS
**Question:** What address formats are supported by the I2C module?
**Retrieved:** pages 1375, 1381, 1429, 1382, 1422
**Answer:** Describes 7-bit and 10-bit addressing, including 10-bit preamble encoding.
**Notes:** Detailed and accurate. S2 (page 1381) provides the 10-bit mechanism detail.

### i2c-004 -- PASS
**Question:** What low-level I2C bus tasks can the module execute automatically?
**Retrieved:** pages 1377, 1391, 1375, 1413, 1392
**Answer:** Lists 8 automatic tasks: (de)serialization, start/stop, ACK, bus state, arbitration, address recognition, general call, repeated start.
**Notes:** Directly from S1 (Feature List, page 1375). Complete enumeration.

### i2c-005 -- PARTIAL
**Question:** How are SDA and SCL used and what is their idle state?
**Retrieved:** pages 1385, 1387, 1379, 1377, 1439
**Answer:** Covers SCL (master clock, stretching, multi-master sync) and SDA (data stability, arbitration, ACK). **Does not answer idle state** — context insufficient.
**Notes:** The "both lines idle high" detail was not in the top-5 retrieved chunks. Model correctly flags insufficient context rather than hallucinating. Good behavior but incomplete answer.

### i2c-006 -- PASS
**Question:** What role does the FIFO play in I2C transmit and receive data transfer?
**Retrieved:** pages 1376, 1400, 1406, 1395, 1401
**Answer:** Comprehensive — covers buffering (8 stages, 32-bit), flow control, TX/RX data staging, packet management, request generation (BREQ/LBREQ/SREQ/LSREQ), error handling.
**Notes:** Best answer in the set. Well-structured, detailed, multi-source synthesis from 5 chunks.

### i2c-007 -- PASS
**Question:** Which interrupt categories or sources are described for the I2C module?
**Retrieved:** pages 1421, 1413, 1415, 1376, 1429
**Answer:** Three categories: Data Transfer (4 sources), Protocol (7 sources), Error (4 sources). Lists specific protocol and error sources with register names.
**Notes:** Accurate and well-organized. Includes interrupt router signal names.

### i2c-008 -- PARTIAL
**Question:** How is the I2C kernel clock and bit rate generated?
**Retrieved:** pages 1377, 1392, 1395, 1406, 1379
**Answer:** "Derived from system clock via prescaler. Fractional divider generates bit rate." (one sentence)
**Notes:** Correct but very brief. The retrieved chunks contained more detail (FDIVCFG, FDIVHIGHCFG, TIMCFG registers, INC/DEC/FS_SCL_LOW parameters) that the model did not use. Likely limited by top-5 retrieval quality — the feature list on page 1377 has a summary but detailed baudrate generation is on page 1383 (not retrieved). Acceptable but thin.

### i2c-009 -- PASS
**Question:** What does the documentation say about multi-master operation and arbitration?
**Retrieved:** pages 1383, 1380, 1379, 1395, 1396
**Answer:** Covers arbitration mechanism (wired AND, SDA comparison), stages (address/RnW/data/ACK), outcome (AL request, LISTENING state), and functional restrictions (master collision, hold time violation, high-speed mode limitation).
**Notes:** Excellent — includes the functional restrictions which are a key differentiator. Well-structured with subsections.

### i2c-010 -- PASS
**Question:** What are the main CPU offload benefits of the I2C module?
**Retrieved:** pages 1377, 1376, 1416, 1429, 1375
**Answer:** Covers time-critical task relief, automatic low-level tasks, FIFO buffering with DMA support, interrupt handling.
**Notes:** Good synthesis across multiple sources. Directly answers the question.

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

## Findings

1. **Strengths:** Model produces grounded, well-structured answers with source citations. Multi-source synthesis is strong (i2c-006, i2c-009). Correctly flags insufficient context (i2c-005 idle state) rather than hallucinating.
2. **i2c-005 (SDA/SCL):** Idle state ("both lines pulled high, bus free") is in the PDF but not in top-5 retrieved chunks. The model handles this gracefully.
3. **i2c-008 (clock/bitrate):** Answer is correct but one-line. The detailed baudrate generation section (page 1383, FDIVCFG/FDIVHIGHCFG) was not in the retrieved set. BM25 ranked page 1377 first (feature list summary) which has only a high-level mention.
4. **No hallucinations detected** across all 10 answers.
5. **Citation format:** Consistent [S1], [S2], etc. references throughout.

## Recommendations

- **i2c-008:** Consider raising candidate-k to 16 to pull in page 1383 (baudrate details) which is at rank 4 in vector but may not make top-12 hybrid.
- **i2c-005:** The "idle state" detail is in the PDF but buried in a chunk not retrieved. Could be addressed by slightly lowering chunk_size (e.g., 500 instead of 800) to create denser chunks.
- **Overall:** Solid baseline. No tuning needed for first slice. Hybrid at top-k=5 / candidate-k=12 is a good default for I2C.
