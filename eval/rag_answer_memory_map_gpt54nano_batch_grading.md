# Memory Map Answer Batch Grading

## Run Metadata

```text
slice: memory_map
model: gpt-5.4-nano
mode: bm25
chunk setting: 300/60
top_k: 5
candidate_k: 10
output: eval/rag_answer_memory_map_gpt54nano_batch.jsonl

This is a table-heavy stress eval. The goal is not only to count PASS/FAIL, but to identify whether failures come from retrieval/context, flattened table layout, or answer synthesis.

Summary
PASS:    6
PARTIAL: 2
FAIL:    2
TOTAL:   10

Overall result: acceptable for a first table-heavy stress test, but not production-stable for dense memory-map/register-table lookup.

The model usually answers well when the correct table chunk is present in context. Failures are mostly caused by missing or incomplete target chunks in the top-k context.

Per-question grading
memory-map-001 — PASS

Question: Acronym meanings for BBBBE, SPBBE, SRIBE, and Access.

The answer correctly defines all four acronyms and cites page 90 chunks. This is a clean lookup success.

memory-map-002 — PASS

Question: Segments allowing access to PSPR, DSPR, PCACHE, DCACHE, and TAG SRAMs.

The answer correctly identifies segments 1 and 3–7 and includes the relevant cache-disabled caveats. Good context and good synthesis.

memory-map-003 — PASS

Question: CPU0 DSPR address range and size.

The answer gives:

7000 0000H – 7003 BFFFH
240 Kbyte

This appears correct and is sourced from page 93. However, the target page appears only as source S5, so this is a retrieval-near-miss rescued by top_k=5.

memory-map-004 — FAIL

Question: CPU0 PSPR address range and size.

The answer says the provided context does not include the CPU0 PSPR entry. This is a good abstention, but the task answer is missing.

Failure type: retrieval/context failure.

The expected page is not present in the retrieved sources. This shows that even with 300/60 chunks and BM25, exact table-row lookup can still miss.

memory-map-005 — PARTIAL

Question: Segment 8 Program Flash 0 through Program Flash 5 ranges.

The answer retrieves the relevant page 94 only as S5 and combines it with SOTA-related chunks from page 97.

The answer is partially useful, but should be reviewed carefully against the original table because PF4/PF5 ordering and ranges may be vulnerable to confusion between standard segment 8 mapping and alternate SOTA mappings.

Failure type: mixed context / similar table confusion.

memory-map-006 — FAIL

Question: Boot ROM address range and read/write access types in segment 8.

The answer correctly refuses to invent an exact range, but it does not answer the question.

Failure type: retrieval/context failure.

The retrieved context includes general BROM/PFLASH wording, but not the precise Boot ROM row needed for the answer.

memory-map-007 — PASS

Question: Data Flash 0 EEPROM, UCB, CFS, and Data Flash 1 EEPROM ranges.

The answer gives specific ranges and sizes from page 96. Good table lookup success.

memory-map-008 — PARTIAL

Question: Compare segment 9 and segment 11 ranges for CPU0 DLMU and LMU0 LMURAM.

The answer provides some useful ranges, but it is not fully confident and says the context is insufficient for a complete consistent comparison.

Failure type: multi-page / multi-row comparison issue.

This question likely needs better parent/table context, because the answer spans multiple related rows and pages.

memory-map-009 — PASS

Question: TC39x alternate SOTA segment 8 PFLASH mapping.

The answer correctly maps:

8000 0000H -> PF2
8030 0000H -> PF3
8060 0000H -> PF0
8090 0000H -> PF1

Good table lookup success.

memory-map-010 — PASS

Question: TC38x alternate SOTA segment 10 PFLASH mapping.

The answer gives a coherent mapping for A000 0000H through A0BF FFFFH from page 100. Good table lookup success.

Findings

The answer layer is not the primary weakness. When the correct chunk is present, the model usually answers correctly and cites sources.

Main remaining problems:

Exact table-row retrieval is still unstable.
Similar repeated address-map tables confuse retrieval.
Some correct chunks appear only at rank 5.
Multi-row or multi-page comparison questions need better context packing.
Flattened tables lose row/header binding.
Recommendation

Do not treat the current setup as production-stable for dense memory-map/register-table QA.

Recommended next technical direction:

P3 — improve table-heavy retrieval

Most promising next experiments:

table-aware chunking / row-group chunking
parent-child retrieval: search small chunks, return page/table context
hex/address normalization
BM25-weighted fusion or reranking
