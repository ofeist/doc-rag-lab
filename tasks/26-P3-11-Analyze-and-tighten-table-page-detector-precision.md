# P3-11 Task - Analyze and Tighten Table Page Detector Precision

## Context

P3-10 completed the mixed corpus smoke test on pages `90-126`.

Result:

```text
range: 90-126
detector: 37 scanned, 23 table-heavy candidates

mixed chunks:
- total: 194
- generic_page: 14
- generic_residual: 28
- table_row_group: 152

Retrieval results:

memory_map + bm25_table_boost: 100 / 100 / 100
boot_bmhd + hybrid:            60 / 90 / 90
```

Important finding from P3-10:

Detector over-selects some pages as table-heavy:

```text
pages 103-111
page 121
```

This was acceptable for P3-10 because it was a smoke test, not a tuning task.

## Goal

Analyze why the detector over-selects pages `103-111` and `121`, then tighten
the heuristic rules conservatively.

Modify:

```text
scripts/detect_table_pages.py
```

Create/update report:

```text
docs/TABLE_PAGE_DETECTOR_PRECISION_EXPERIMENT.md
```

Do not change:

```text
scripts/build_mixed_chunks.py
scripts/build_table_aware_chunks.py
scripts/chunk_pages.py
scripts/ingest_document.py
scripts/ask_chunks.py
```

## Main Objective

Reduce false positives from the P3-10 mixed smoke range while preserving
detection of important table-heavy pages.

Important pages that must remain detected:

```text
93
94
96
97
100
```

Known false-positive / over-selected pages to inspect:

```text
103-111
121
```

Do not assume all of them are definitely wrong. Inspect their text/signals first
and classify them.

## Required Analysis

Run detector on the mixed smoke range:

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memmap_boot_precision_before.jsonl \
  --page-ranges 90-126 \
  --min-score 0.5
```

Inspect candidate records for:

```text
pages 90-102
pages 103-111
page 121
```

For each over-selected page, record:

```text
page
score
page_type
recommended_chunker
signals
reasons
why it was selected
whether it should remain table-heavy or not
```

## What To Tune

Prefer small, explainable heuristic changes.

Possible tuning directions:

1. Distinguish real address-map tables from prose references.
2. Require stronger address-pair evidence for `address_map_table`.
3. Separate `generic_table` from `address_map_table`.
4. Avoid tuning only for page numbers.

Do not hardcode exclusions like:

```text
if page in 103..111: exclude
```

Use content signals.

## Desired Behavior After Tuning

Run detector again:

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memmap_boot_precision_after.jsonl \
  --page-ranges 90-126 \
  --min-score 0.5
```

Expected:

- pages `93`, `94`, `96`, `97`, `100` remain selected
- some or all over-selected pages `103-111` / `121` are no longer recommended as `table_row_group`

It is acceptable if a few ambiguous pages remain selected, but the report must
explain why.

## Validation With Mixed Builder

After tuning, rebuild mixed chunks:

```bash
.venv/bin/python scripts/build_mixed_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_mixed_memmap_boot_precision.jsonl \
  --doc-id memmap_boot_precision \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_memmap_boot_precision_after.jsonl \
  --min-table-score 0.5 \
  --section-title "Mixed MEMMAP / Boot Precision Test" \
  --chunk-size 800 \
  --overlap 120 \
  --table-group-size 4 \
  --table-residual-chunk-size 300 \
  --table-residual-overlap 60
```

Record chunk counts:

```text
total chunks
generic_page
generic_residual
table_row_group
```

Expected direction:

```text
table_row_group count decreases if false positives were reduced
generic_page count increases
```

## Retrieval Validation

Embed:

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_mixed_memmap_boot_precision.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

Run memory_map eval:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_memmap_boot_precision.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

Target:

```text
memory_map hit@3 >= 90%
memory_map hit@5 >= 100%
```

Run Boot/BMHD eval:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode hybrid \
  --eval eval/boot_bmhd_eval.json \
  --chunks data/chunks_mixed_memmap_boot_precision.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8
```

Target:

```text
boot_bmhd should not regress materially from P3-10:
previous: 60 / 90 / 90
acceptable: hit@3 >= 90%, hit@5 >= 90%
```

If `boot-005` still fails, mention that it was already known weaker.

## Report

Create:

```text
docs/TABLE_PAGE_DETECTOR_PRECISION_EXPERIMENT.md
```

Include:

1. Problem
2. Before tuning
3. Heuristic change
4. After tuning
5. Mixed chunk impact
6. Retrieval impact
7. Verdict
8. Next recommendation

## Non-goals

Do not:

- hardcode page-specific exclusions
- overfit aggressively
- change mixed builder behavior unless a detector output compatibility bug is found
- modify normal ingest pipeline
- modify answer path
- run model/API calls
- run answer eval
- add ML classifiers
- add PyMuPDF `find_tables()`
- add Camelot / Unstructured / Docling
- add parent-child retrieval
- add reranker
- commit generated JSONL chunks
- commit vector DB files

## Verification

Run syntax checks:

```bash
.venv/bin/python -m py_compile \
  scripts/detect_table_pages.py \
  scripts/build_mixed_chunks.py \
  scripts/eval_retrieval.py
```

Run detector before/after, mixed builder, embed, and retrieval evals.

Check generated artifacts are ignored / not staged:

```bash
git check-ignore -v \
  data/table_page_candidates_memmap_boot_precision_before.jsonl \
  data/table_page_candidates_memmap_boot_precision_after.jsonl \
  data/chunks_mixed_memmap_boot_precision.jsonl \
  vector_db/chroma
```

Run cleanup checks:

```bash
git diff --check
git status --short
```

## Commit

Stage only source/docs changes:

```bash
git add scripts/detect_table_pages.py \
        docs/TABLE_PAGE_DETECTOR_PRECISION_EXPERIMENT.md
```

If only the report is needed because no code change was justified:

```bash
git add docs/TABLE_PAGE_DETECTOR_PRECISION_EXPERIMENT.md
```

Commit:

```bash
git commit -m "Tighten table page detector precision"
```

## Done Criteria

Done when:

- over-selected pages from P3-10 were inspected
- detector heuristic was tightened or documented as intentionally unchanged
- important memory_map pages still pass detection
- mixed chunk counts reflect the detector change
- memory_map retrieval remains strong
- Boot/BMHD retrieval does not materially regress
- report documents before/after results
- generated JSONL/vector DB files are not committed
- normal ingest and answer pipelines remain unchanged

## Scope Note

Do not chase perfection. The goal is precision improvement without recall loss,
not a perfect table classifier.
