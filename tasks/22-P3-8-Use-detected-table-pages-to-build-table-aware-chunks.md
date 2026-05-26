# P3-8 Task - Use Detected Table Pages to Build Table-Aware Chunks

## Context

P3-7 added automatic table-heavy page detection.

New detector:

```text
scripts/detect_table_pages.py
```

P3-7 result on `memory_map`:

```text
pages scanned: 13
table-heavy pages detected: 12
address_map_table pages detected: 12
important pages detected: 93, 94, 96, 97, 100
```

Current generalized table-aware builder:

```text
scripts/build_table_aware_chunks.py
```

Current limitation:

```text
build_table_aware_chunks.py still requires manual --page-ranges.
```

Goal now:

```text
detector output -> table-aware builder input
```

This is the first step toward automatic table-aware chunking for large documents.

## Goal

Extend the table-aware builder so it can consume detector output from:

```text
data/table_page_candidates_*.jsonl
```

and automatically build table-aware chunks for detected pages.

Do not change the normal ingest pipeline yet.

Do not modify:

```text
scripts/chunk_pages.py
scripts/ingest_document.py
scripts/ask_chunks.py
```

## Target Behavior

Add a new optional CLI argument to:

```text
scripts/build_table_aware_chunks.py
```

New flag:

```text
--table-candidates data/table_page_candidates_memory_map.jsonl
```

When this flag is provided, the builder should read candidate pages and use them
instead of manual `--page-ranges`.

Example:

```bash
.venv/bin/python scripts/build_table_aware_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_table_aware_memory_map_auto.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_memory_map.jsonl \
  --section-title "Memory Maps (MEMMAP)" \
  --group-size 4 \
  --residual-chunk-size 300 \
  --residual-overlap 60
```

## Candidate Filtering

Use candidate records where:

```text
recommended_chunker == "table_row_group"
```

and:

```text
table_likelihood >= --min-table-score
```

Add optional flag:

```text
--min-table-score 0.5
```

Default:

```text
0.5
```

If `--table-candidates` is provided, `--page-ranges` should be optional.

If both are provided, fail clearly and ask the user to provide only one of
`--page-ranges` or `--table-candidates`.

## Required Behavior

- Read `--table-candidates` JSONL.
- Extract pages passing the filter.
- Convert selected pages into the same internal page set/ranges used by
  `--page-ranges`.
- Build table-aware chunks exactly as before.
- Preserve output schema.
- Print a clear summary.

Example summary:

```text
Loaded table candidates: 13
Selected table pages: 12
Selection filter: recommended_chunker=table_row_group, min_score=0.5
Selected pages: 90, 91, 92, 93, 94, 96, 97, 98, 99, 100, 101, 102
Wrote 98 chunks to data/chunks_table_aware_memory_map_auto.jsonl
```

## Important Validation

For `memory_map`, the detector-driven builder should produce retrieval results
equivalent or very close to the manual page-range builder.

Manual known result:

```text
bm25:              80 / 80 / 100
bm25_table_boost:  80 / 100 / 100
```

Detector-driven expected result:

```text
bm25_table_boost:
hit@1 >= 80%
hit@3 >= 90%
hit@5 >= 100%
```

Ideally:

```text
80 / 100 / 100
```

If results differ, explain why in the report.

## Commands

1. Generate detector output

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memory_map.jsonl \
  --page-ranges 90-102 \
  --min-score 0.5
```

2. Build table-aware chunks from detector output

```bash
.venv/bin/python scripts/build_table_aware_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_table_aware_memory_map_auto.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_memory_map.jsonl \
  --min-table-score 0.5 \
  --section-title "Memory Maps (MEMMAP)" \
  --group-size 4 \
  --residual-chunk-size 300 \
  --residual-overlap 60
```

3. Embed detector-built chunks

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_table_aware_memory_map_auto.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

4. Evaluate

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_table_aware_memory_map_auto.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

Also compare plain BM25:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25 \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_table_aware_memory_map_auto.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

## Documentation

Create:

```text
docs/DETECTOR_DRIVEN_TABLE_CHUNKING_EXPERIMENT.md
```

Include:

- why detector-driven chunking is needed
- new CLI flag
- candidate filtering logic
- memory_map validation result
- comparison against manual page-range result
- limitations
- next recommendation

Mention clearly:

```text
This connects detection to chunk building, but still does not modify the normal ingest pipeline.
```

## Non-goals

Do not:

- change `scripts/chunk_pages.py`
- change `scripts/ingest_document.py`
- change answer generation
- change `scripts/ask_chunks.py`
- add automatic mixed ingest
- add PyMuPDF `find_tables()`
- add Camelot / Unstructured / Docling
- add ML classifiers
- run model/API calls
- run answer eval
- commit generated JSONL outputs
- commit vector DB files

## Error Handling

Fail clearly if:

- `--table-candidates` file does not exist
- `--table-candidates` and `--page-ranges` are both provided
- no candidate pages pass the filter
- candidate record is missing `page` / `table_likelihood` / `recommended_chunker`
- `--residual-overlap >= --residual-chunk-size`

## Verification

Run syntax checks:

```bash
.venv/bin/python -m py_compile \
  scripts/detect_table_pages.py \
  scripts/build_table_aware_chunks.py \
  scripts/eval_retrieval.py
```

Run detector + builder + retrieval eval.

Expected `memory_map` result:

```text
bm25_table_boost: ideally 80 / 100 / 100
```

Run cleanup checks:

```bash
git diff --check
git status --short
```

Confirm generated artifacts are ignored / not staged:

```bash
git check-ignore -v \
  data/table_page_candidates_memory_map.jsonl \
  data/chunks_table_aware_memory_map_auto.jsonl \
  vector_db/chroma
```

## Commit

Stage only source/docs changes:

```bash
git add scripts/build_table_aware_chunks.py \
        docs/DETECTOR_DRIVEN_TABLE_CHUNKING_EXPERIMENT.md
```

If detector docs need a small reference update, add only the changed doc:

```bash
git add docs/TABLE_PAGE_DETECTION_EXPERIMENT.md
```

Commit:

```bash
git commit -m "Build table-aware chunks from detected table pages"
```

## Done Criteria

Done when:

- `build_table_aware_chunks.py` supports `--table-candidates`
- manual `--page-ranges` still works
- providing both flags fails clearly
- detector output can drive table-aware chunking
- `memory_map` retrieval result is preserved or explained
- docs explain the detector-driven workflow
- generated JSONL/vector DB files are not committed
- normal ingest pipeline remains unchanged

## Scope Note

Do not make mixed ingest in this slice. P3-8 is only:

```text
detector -> table builder
```

Mixed prose+table corpus is the next slice.
