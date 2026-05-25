# Memory Map Chunk-Size Experiment

## Goal

Test whether smaller chunks improve retrieval for the table-heavy `memory_map` eval slice.

```text
slice id: memory_map
page range: 90-102
eval file: eval/memory_map_eval.json
document: docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
```

No answer-generation/model calls were made. This experiment only ran local ingest,
embedding, and retrieval eval.

## Hypothesis

The default page-local chunks are too large for dense address-map tables. Smaller chunks
may improve exact row/range retrieval because fewer unrelated table rows compete inside
the same chunk.

## Settings Tested

| Setting | Chunk tokens | Overlap tokens | Chunk count |
| --- | ---: | ---: | ---: |
| baseline | 800 | 120 | 23 |
| variant A | 500 | 80 | 35 |
| variant B | 300 | 60 | 53 |

All settings used the same focused ingest:

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-102 \
  --doc-id memory_map \
  --collection technical_docs \
  --reset \
  --chunk-tokens <chunk_tokens> \
  --overlap-tokens <overlap_tokens>
```

## Retrieval Results

| Chunk setting | Mode | hit@1 | hit@3 | hit@5 |
| --- | --- | ---: | ---: | ---: |
| 800/120 | vector | 20% | 40% | 40% |
| 800/120 | BM25 | 40% | 60% | 70% |
| 800/120 | hybrid/RRF | 40% | 40% | 40% |
| 800/120 | bm25_first_hybrid | 40% | 60% | 70% |
| 500/80 | vector | 20% | 40% | 50% |
| 500/80 | BM25 | 60% | 60% | 70% |
| 500/80 | hybrid/RRF | 20% | 50% | 60% |
| 500/80 | bm25_first_hybrid | 60% | 60% | 70% |
| 300/60 | vector | 30% | 40% | 40% |
| 300/60 | BM25 | 60% | 60% | 80% |
| 300/60 | hybrid/RRF | 30% | 50% | 50% |
| 300/60 | bm25_first_hybrid | 60% | 60% | 80% |

## Observations

- Smaller chunks helped BM25 hit@1: baseline 40%, variants 60%.
- The 300/60 setting produced the best hit@5: 80% for BM25 and `bm25_first_hybrid`.
- Standard RRF hybrid improved slightly at 500/80 but still underperformed BM25-first.
- Vector retrieval did not materially improve. The issue is still not solved by smaller
  chunks alone.
- `bm25_first_hybrid` continues to match BM25 because it preserves BM25 ordering and only
  fills unused slots with vector candidates.

## Remaining Failures

Even with 300/60, the eval is not strong:

```text
best hit@3: 60%
best hit@5: 80%
```

The persistent misses are still likely caused by:

- repeated similar table rows across device-family variants,
- hex address tokens that are not semantically meaningful to vector embeddings,
- flattened table extraction that loses row/header binding,
- broad multi-row questions such as all PF0-PF5 ranges in segment 8.

## Recommendation

Use 300/60 as the current preferred setting for the `memory_map` table-heavy stress slice
when running retrieval experiments. It improves BM25 and BM25-first hit@5 without adding a
new parser or retrieval architecture.

Do not treat this as a global default yet. The next useful experiments are:

1. BM25-weighted fusion rather than strict BM25-first ordering.
2. Table-aware chunking that preserves table title, column headers, and row groups.
3. Hex address normalization so queries and extracted text share stable address forms.
4. Parent-child retrieval: search small row-level chunks, return page/table context.
