# Shared Corpus Answer Quality Eval (P3-16)

This evaluates answer quality on the experimental shared mixed corpus. It does not
replace the normal ingest pipeline.

## Goal

P3-13 proved retrieval (hit@k) on one shared detector-driven mixed corpus. This
slice asks the next question: when the answer layer uses that shared corpus
context, does it produce grounded, correct answers across all four slices?

## Corpus used

Rebuilt with the P3-13 page ranges:

```text
90-126,257-259,307-314,1364-1397,1435-1455,1483-1488
```

Pipeline: `extract_pages -> detect_table_pages -> build_mixed_chunks -> embed`,
`--section-title "Multi-Slice Shared Corpus"`. Result:

```text
total chunks      : 269
generic_page      : 96
table_row_group   : 152  (527 rows)
generic_residual  : 21
detected table pages (address_map_table -> row_group): 20  (p91-110)
```

Generated `data/` and `vector_db/` artifacts are not committed.

## Retrieval baseline (re-confirmed before answer eval)

| slice | mode | hit@1 | hit@3 | hit@5 | P3-13 |
| --- | --- | ---: | ---: | ---: | --- |
| memory_map | bm25_table_boost | 100% | 100% | 100% | 100/100/100 |
| boot_bmhd | hybrid | 70% | 100% | 100% | 70/100/100 |
| dma_cache | hybrid | 80% | 100% | 100% | 100/100/100 |
| interrupt_routing | hybrid | 80% | 100% | 100% | 80/100/100 |

One small difference from P3-13: `dma_cache` hit@1 is 80% (was 100%). The
section title was `"Multi-Slice Shared Corpus"` here vs `"Multi-Slice Shared
Corpus Smoke Test"` in P3-13; the shorter title changes table-chunk text, which
shifts global BM25 statistics (avg doc length / IDF) enough to drop one dma_cache
question from rank 1 to rank 2. hit@3 and hit@5 are unchanged at 100%, so the
top-5 answer context is unaffected.

## Model and commands

Model: `gpt-5.4-nano` via `https://api.openai.com/v1`, `--max-tokens 900`,
temperature omitted (the runner only sends temperature when set).

```bash
# memory_map - table-aware retrieval
.venv/bin/python scripts/run_answer_eval.py --eval eval/memory_map_eval.json \
  --mode bm25_table_boost --top-k 5 --candidate-k 10 \
  --chunks data/chunks_mixed_multi_slice.jsonl --db vector_db/chroma \
  --collection technical_docs --model gpt-5.4-nano \
  --base-url https://api.openai.com/v1 --max-tokens 900 \
  --output-jsonl eval/rag_answer_shared_memory_map_gpt54nano.jsonl --overwrite

# boot_bmhd / dma_cache / interrupt_routing - hybrid, top-k 5, candidate-k 8
# (same form, --mode hybrid)
```

Outputs:

```text
eval/rag_answer_shared_memory_map_gpt54nano.jsonl
eval/rag_answer_shared_boot_bmhd_gpt54nano.jsonl
eval/rag_answer_shared_dma_cache_gpt54nano.jsonl
eval/rag_answer_shared_interrupt_routing_gpt54nano.jsonl
```

## Grading summary

Full per-item grading: `eval/rag_answer_shared_corpus_gpt54nano_grading.md`.

| slice | PASS | PARTIAL | FAIL |
| --- | ---: | ---: | ---: |
| memory_map | 10 | 0 | 0 |
| boot_bmhd | 9 | 1 | 0 |
| dma_cache | 10 | 0 | 0 |
| interrupt_routing | 10 | 0 | 0 |
| **total** | **39** | **1** | **0** |

PASS rate 39/40 = 97.5%. This meets the desired target (>= 80% PASS, 0 severe
hallucinations).

## Per-slice observations

- **memory_map (table-heavy):** All 10 PASS. Dense address-map answers (PFLASH
  ranges, Boot ROM access types, alternate SOTA maps) stayed grounded and exact.
  Spot-checked memory-map-009/010 against the raw pages - correct. The
  `bm25_table_boost` + `table_row_group` chunks carry enough table context for the
  model to read exact hex ranges and sizes.
- **boot_bmhd (procedural prose):** 9 PASS, 1 PARTIAL. The PARTIAL (boot-005,
  "process BMHDs and their copies") is the one question whose expected pages were
  not fully retrieved; the answer correctly described original-vs-copy processing
  and honestly flagged where the context ran out instead of inventing steps.
- **dma_cache (config prose):** All 10 PASS. Register-level answers (PMA0/PMA1,
  DSYNC/ISYNC ordering, PCON1.PCINV, CHCSR.SCH) correct and grounded.
- **interrupt_routing (register/procedure):** All 10 PASS. Bit-field and encoding
  answers (SRPN, TOS map, SETR/CLRR, ACCEN split, register address spaces) correct;
  TOS encodings verified against the raw page.

## Common failure / risk modes observed

- **Answer quality tracks retrieval quality.** The single non-PASS aligns exactly
  with the single question that lost expected pages in retrieval. The answer layer
  did not compensate by hallucinating - it stayed within retrieved context.
- **No cross-slice contamination.** For dma-cache-004, irq-004, irq-010 the shared
  corpus surfaced a few off-slice memory_map pages as low-ranked candidates, but
  the model grounded its answers only in the correct slice pages. Mixing four
  slices into one corpus did not pollute answers.
- **Graceful boundaries.** Where context was incomplete (boot-005) the model
  stated the limit rather than fabricating.

## Is shared-corpus answer quality acceptable?

Yes. One shared mixed corpus produced grounded, correct answers across table-heavy
and prose slices at 97.5% PASS with zero hallucinations and no cross-slice
contamination. The answer layer behaves correctly on the shared corpus.

## Next recommendation

- The remaining weakness is retrieval recall on procedural prose (boot-005), not
  answer generation. A future slice could improve recall for multi-page procedural
  questions (e.g. higher candidate-k or query expansion) rather than changing the
  answer layer.
- With retrieval and answer quality both proven on a shared multi-slice corpus,
  the next structural step is either a full-document smoke test or ingest
  integration design (detector-driven mixed chunking + automatic retrieval-mode
  selection moving from experimental scripts toward the normal pipeline).

This remains an experiment. The normal ingest and answer pipelines are unchanged.
