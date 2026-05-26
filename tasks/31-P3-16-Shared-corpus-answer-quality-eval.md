# P3-16 Task - Shared Corpus Answer Quality Eval

## Context

P3-13 proved that one shared detector-driven mixed corpus supports all known
retrieval eval slices:

```text
memory_map        bm25_table_boost  100 / 100 / 100
boot_bmhd         hybrid             70 / 100 / 100
dma_cache         hybrid            100 / 100 / 100
interrupt_routing hybrid             80 / 100 / 100
```

That proves retrieval, not answer quality. This task asks: when the answer layer
uses the shared corpus context, does it produce grounded, correct answers across
all four slices?

(P3-15 was used for documentation cleanup, so this answer-quality slice is P3-16.)

## Goal

Run answer-quality evaluation on the shared mixed corpus using the existing
`scripts/run_answer_eval.py`. No code changes unless a small CLI/doc bug is found.

## Non-goals

Do not modify chunking, table detection, mixed builder, normal ingest, prompts;
do not run full-document ingest; no reranker, parent-child, or new retrieval
modes; do not commit generated vector DB or temporary data files.

## Corpus

Same page ranges as P3-13:

```text
90-126,257-259,307-314,1364-1397,1435-1455,1483-1488
```

Rebuild: extract -> detect_table_pages -> build_mixed_chunks -> embed
(`--section-title "Multi-Slice Shared Corpus"`).

## Steps

1. Rebuild shared corpus if needed.
2. Confirm retrieval still matches the P3-13 baseline (4 slices).
3. Run answer eval batches with one model (`gpt-5.4-nano`), `--max-tokens 900`,
   omit temperature:
   - memory_map: `bm25_table_boost`, top-k 5, candidate-k 10
   - boot_bmhd / dma_cache / interrupt_routing: `hybrid`, top-k 5, candidate-k 8
   Outputs: `eval/rag_answer_shared_<slice>_gpt54nano.jsonl`
4. Manual grading -> `eval/rag_answer_shared_corpus_gpt54nano_grading.md`
   (PASS / PARTIAL / FAIL, with id, slice, grade, short reason).
5. Report -> `docs/experiments/SHARED_CORPUS_ANSWER_QUALITY_EVAL.md`.

Run a `--limit 1` smoke on one slice before spending credits on all four.

## Expected results

- Minimum: most answers PASS or PARTIAL; no cross-slice contamination; abstains
  when context is insufficient; table-heavy answers stay grounded.
- Desired: >= 80% PASS overall; 0 severe hallucination failures.
- If not achieved, document the failure pattern instead of tuning blindly.

## Done Criteria

- shared corpus rebuilt/confirmed
- four retrieval baselines confirmed
- answer eval run for all four slices
- manual grading completed
- report documents results and failure modes
- generated data/ and vector_db/ artifacts not committed
- normal ingest pipeline unchanged
