# P3-12 Task - Large-Section Mixed Ingest Smoke Test

## Context

P3-11 tightened table page detector precision.

Current accepted behavior:

```text
address_map_table -> table_row_group
generic_table     -> generic
```

P3-11 result:

```text
row-group selected pages: 23 -> 20
memory_map + bm25_table_boost: 100 / 100 / 100
boot_bmhd + hybrid: 70 / 90 / 100
```

We now want to test the full mixed pipeline on a larger document section.

Important: this is still a smoke test, not production ingest.

## Goal

Run a larger mixed-corpus smoke test over a broader page range to observe:

- detector behavior
- chunk type distribution
- retrieval stability
- false positives / false negatives
- runtime / artifact size

Suggested range:

```text
90-200
```

This should include memory_map tables, boot/BMHD pages, and additional
prose/semi-structured technical sections.

Do not run the whole PDF unless explicitly justified.

## Non-goals

Do not:

- replace `ingest_document.py`
- modify normal ingest pipeline
- change answer generation
- run model/API calls
- run answer eval
- add reranking
- add parent-child retrieval
- add Camelot / Unstructured / Docling
- tune detector heavily
- commit generated JSONL/vector DB artifacts

## Commands

1. Extract large section

```bash
.venv/bin/python scripts/extract_pages.py \
  docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-200 \
  --out data/raw_pages_large_section.jsonl
```

2. Detect table-heavy pages

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages_large_section.jsonl \
  --output data/table_page_candidates_large_section.jsonl \
  --page-ranges 90-200 \
  --min-score 0.5
```

3. Build mixed chunks

```bash
.venv/bin/python scripts/build_mixed_chunks.py \
  --input data/raw_pages_large_section.jsonl \
  --output data/chunks_mixed_large_section.jsonl \
  --doc-id large_section_90_200 \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_large_section.jsonl \
  --min-table-score 0.5 \
  --section-title "Large Section Mixed Smoke Test" \
  --chunk-size 800 \
  --overlap 120 \
  --table-group-size 4 \
  --table-residual-chunk-size 300 \
  --table-residual-overlap 60
```

4. Embed

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_mixed_large_section.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

5. Run retrieval evals

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_large_section.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode hybrid \
  --eval eval/boot_bmhd_eval.json \
  --chunks data/chunks_mixed_large_section.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8
```

Optional if page ranges match:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode hybrid \
  --eval eval/dma_cache_eval.json \
  --chunks data/chunks_mixed_large_section.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8
```

## Expected Results

Minimum expectations:

- mixed chunks generated successfully
- `generic_page > 0`
- `table_row_group > 0`
- `generic_residual > 0`
- memory_map retrieval remains strong
- boot_bmhd does not materially collapse

Suggested targets:

```text
memory_map: hit@3 >= 90%, hit@5 >= 100%
boot_bmhd: hit@3 >= 80%, hit@5 >= 90%
```

If worse, document likely cause instead of tuning blindly.

## Analysis Questions

In the report, answer:

- How many pages were scanned?
- How many were detected as table-heavy?
- How many were `address_map_table` vs `generic_table`?
- Which pages were routed to `table_row_group`?
- Did detector over-select obvious prose pages?
- Did detector miss obvious table pages?
- What was chunk type distribution?
- Did memory_map retrieval remain stable?
- Did boot_bmhd retrieval remain stable?
- Is the pipeline ready for a larger-range or full-document smoke test?

## Documentation

Create:

```text
docs/LARGE_SECTION_MIXED_INGEST_SMOKE_TEST.md
```

Clearly state:

```text
This is a large-section smoke test. It does not replace the normal ingest pipeline.
```

## Verification

Run syntax checks:

```bash
.venv/bin/python -m py_compile \
  scripts/detect_table_pages.py \
  scripts/build_mixed_chunks.py \
  scripts/eval_retrieval.py
```

Check generated files are ignored:

```bash
git check-ignore -v \
  data/raw_pages_large_section.jsonl \
  data/table_page_candidates_large_section.jsonl \
  data/chunks_mixed_large_section.jsonl \
  vector_db/chroma
```

Run cleanup checks:

```bash
git diff --check
git status --short
```

## Commit

Stage only docs unless a small script bug fix was necessary:

```bash
git add docs/LARGE_SECTION_MIXED_INGEST_SMOKE_TEST.md
git add tasks/27-P3-12-Large-section-mixed-ingest-smoke-test.md
```

Commit:

```bash
git commit -m "Run large-section mixed ingest smoke test"
```
