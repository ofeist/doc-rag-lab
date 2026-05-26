# Mixed Ingest Invariant Tests (P3-20B)

A small pytest layer that locks the invariants introduced in P3-18..P3-20 before
the next slices (P3-21 artifact cleanup, P3-22 Chroma metadata + auto retrieval).
Test-only: no production code changed.

## Why these tests exist

P3-19/P3-20 made two structural promises the later slices must not silently break:

1. Generic chunks are schema-compatible with mixed chunks (one common schema).
2. Mixed ingest reports an accurate detector / chunk-type summary and warns on the
   two guardrail conditions.

These are cheap, deterministic invariants that do not need Chroma, embeddings, or
the LLM, so they are worth pinning with fast unit tests.

## What they lock

`tests/test_chunk_schema.py`
- `chunk_pages.build_chunks` emits `chunk_type="generic_page"` plus empty table
  fields (`section_title`, `table_title`, `table_context`, `column_headers`,
  `row_count`) and all 14 common schema keys (`doc_id` is added later by ingest).

`tests/test_ingest_reporting.py`
- `summarize_chunks` counts chunk types and returns the pages routed to
  `table_row_group`.
- `summarize_table_candidates` counts `address_map_table` / `generic_table`
  candidates.
- `print_mixed_report` prints the no-`table_row_group` warning.
- `print_mixed_report` prints the >60%-pages-routed over-selection warning.

`tests/test_ingest_cli.py`
- `ingest_document.py --help` exposes `--chunk-mode` with `generic` and `mixed`.

## What they intentionally do not test

Chroma persistence, embeddings, OpenAI/LLM answer generation, full-PDF ingestion,
detector scoring accuracy, and retrieval hit@k. Those are covered (or deliberately
left manual) elsewhere and are slow or non-deterministic.

## API note

The originally-proposed tests assumed `summarize_chunks` returned a dict and
`print_mixed_report` took a `chunk_summary=` argument. The actual P3-20 helpers use
`summarize_chunks(path) -> (collections.Counter, list[int])` and
`print_mixed_report(..., chunk_types=, routed_pages=)`. The tests were adapted to
the real signatures rather than refactoring `ingest_document.py` for the tests.

## Running

```bash
.venv/bin/python -m pytest tests
```

Result: `6 passed`. `pytest` is the only added dependency, pinned in
`requirements-dev.txt` (it is not needed to run the pipeline itself). Imports
resolve `scripts/` via a `sys.path` insert at the top of each test module.
