# P3-13 Task - Multi-Slice Shared Corpus Smoke Test

## Context

P3-12 ran a large-section mixed ingest smoke test over pages 90-200. It was
accepted. The `dma_cache` result there was not actionable because pages 90-200
do not contain the dma_cache pages.

So far each mixed smoke test covered only a contiguous section. We have never
built ONE mixed corpus that contains all four known eval slice ranges at once.

This is still a smoke test, not production ingest.

## Goal

Build one mixed chunk corpus that includes all known eval slice page ranges, then
run all four retrieval evals against that single shared corpus.

Slice ranges:

```text
memory_map:        90-126
boot_bmhd:         115-126
dma_cache:         257-259,307-314,1435-1455,1483-1488
interrupt_routing: 1364-1397
```

Union page range used for extraction:

```text
90-126,257-259,307-314,1364-1397,1435-1455,1483-1488
```

Observe:

- detector behavior across very different sections
- chunk type distribution
- whether all four slices retrieve well from one shared corpus
- whether putting table and prose slices together causes cross-slice interference

## Non-goals

Do not:

- replace `ingest_document.py`
- modify the normal ingest pipeline
- change answer generation
- run model/API calls
- run answer eval
- add reranking
- add parent-child retrieval
- add Camelot / Unstructured / Docling
- tune the detector heavily
- commit generated JSONL/vector DB artifacts

## Commands

1. Extract the union of all slice ranges

```bash
.venv/bin/python scripts/extract_pages.py \
  docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-126,257-259,307-314,1364-1397,1435-1455,1483-1488 \
  --out data/raw_pages_multi_slice.jsonl
```

2. Detect table-heavy pages

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages_multi_slice.jsonl \
  --output data/table_page_candidates_multi_slice.jsonl \
  --min-score 0.5
```

3. Build mixed chunks

```bash
.venv/bin/python scripts/build_mixed_chunks.py \
  --input data/raw_pages_multi_slice.jsonl \
  --output data/chunks_mixed_multi_slice.jsonl \
  --doc-id multi_slice_shared \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_multi_slice.jsonl \
  --min-table-score 0.5 \
  --section-title "Multi-Slice Shared Corpus Smoke Test" \
  --chunk-size 800 \
  --overlap 120 \
  --table-group-size 4 \
  --table-residual-chunk-size 300 \
  --table-residual-overlap 60
```

4. Embed

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

5. Run retrieval evals (all four slices, same shared corpus)

```bash
.venv/bin/python scripts/eval_retrieval.py --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma --collection technical_docs

.venv/bin/python scripts/eval_retrieval.py --mode hybrid \
  --eval eval/boot_bmhd_eval.json \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma --collection technical_docs --top-k 5 --candidate-k 8

.venv/bin/python scripts/eval_retrieval.py --mode hybrid \
  --eval eval/dma_cache_eval.json \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma --collection technical_docs --top-k 5 --candidate-k 8

.venv/bin/python scripts/eval_retrieval.py --mode hybrid \
  --eval eval/interrupt_routing_eval.json \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma --collection technical_docs --top-k 5 --candidate-k 8
```

## Expected Results

Minimum expectations:

- mixed chunks generated successfully
- `generic_page > 0`, `table_row_group > 0`, `generic_residual > 0`
- all four expected page sets are present in the corpus
- each slice retrieves at roughly its known standalone level (no collapse from
  sharing one corpus)

Reference standalone baselines:

```text
memory_map (bm25_table_boost): ~100 / 100 / 100
boot_bmhd (hybrid):            ~60-70 / 80-90 / 90-100
dma_cache (hybrid):            ~90 / 100 / 100
interrupt_routing (hybrid):    ~70 / 100 / 100
```

If a slice is materially worse than its standalone baseline, document the likely
cause (cross-slice interference, detector misrouting, missing pages) instead of
tuning blindly.

## Analysis Questions

In the report, answer:

- How many pages were scanned and detected as table-heavy?
- How many `address_map_table` vs `generic_table`?
- Which pages were routed to `table_row_group`?
- What was the chunk type distribution?
- Are all four expected page sets present in the corpus?
- Did any slice regress versus its standalone baseline?
- Is there evidence of cross-slice interference?
- Is the pipeline ready for a full-document smoke test?

## Documentation

Create:

```text
docs/MULTI_SLICE_SHARED_CORPUS_SMOKE_TEST.md
```

Clearly state:

```text
This is a multi-slice shared-corpus smoke test. It does not replace the normal ingest pipeline.
```

## Verification

```bash
.venv/bin/python -m py_compile \
  scripts/detect_table_pages.py \
  scripts/build_mixed_chunks.py \
  scripts/eval_retrieval.py

git check-ignore -v \
  data/raw_pages_multi_slice.jsonl \
  data/table_page_candidates_multi_slice.jsonl \
  data/chunks_mixed_multi_slice.jsonl \
  vector_db/chroma

git diff --check
git status --short
```

## Commit

Stage only docs and this task file unless a small script bug fix was necessary:

```bash
git add docs/MULTI_SLICE_SHARED_CORPUS_SMOKE_TEST.md
git add tasks/28-P3-13-Multi-slice-shared-corpus-smoke-test.md
git commit -m "Run multi-slice shared corpus smoke test"
```
