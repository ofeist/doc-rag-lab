# P3-20B Task - Add Unit Tests for Mixed Ingest Invariants

## Context

P3-18 added `--chunk-mode`; P3-19 implemented schema-compatible mixed ingest;
P3-20 added the mixed report + guardrail warnings. Before P3-21/P3-22, lock the
important invariants with a small pytest layer. Test-only slice.

## Goal

Lightweight pytest covering:
- generic chunk schema compatibility (`chunk_pages.build_chunks`)
- table candidate / chunk summary helpers (`summarize_table_candidates`,
  `summarize_chunks`)
- guardrail warnings (`print_mixed_report`)
- CLI help exposes `--chunk-mode`

Do not test Chroma, embeddings, OpenAI/LLM answers, or full PDF ingestion.

## API note

The proposed tests assumed a dict-returning `summarize_chunks` and a
`chunk_summary=` param on `print_mixed_report`. The actual P3-20 helpers use
`summarize_chunks(path) -> (Counter, list[int])` and
`print_mixed_report(..., chunk_types=, routed_pages=)`. Per the lead's note, the
tests are adapted to the real signatures rather than refactoring `ingest_document`.

## Non-goals

No change to ingest / detector / chunking / retrieval behavior; no persisting
`chunk_type` to Chroma; no model/API calls; no expensive full-PDF tests.

## Files

- `tests/test_chunk_schema.py`
- `tests/test_ingest_reporting.py`
- `tests/test_ingest_cli.py`
- `requirements-dev.txt` (pins `pytest`, the only test dependency)

## Verification

```text
.venv/bin/python -m pytest tests
.venv/bin/python -m py_compile scripts/chunk_pages.py scripts/ingest_document.py
```

No Chroma, no embeddings, no OpenAI.

## Docs

- New `docs/experiments/MIXED_INGEST_INVARIANT_TESTS.md`.
- Short P3-20B note in `docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md`.

## Commit

```text
git add tests/test_chunk_schema.py tests/test_ingest_reporting.py \
        tests/test_ingest_cli.py requirements-dev.txt \
        docs/experiments/MIXED_INGEST_INVARIANT_TESTS.md \
        docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md \
        tasks/36-P3-20B-Add-unit-tests-for-mixed-ingest-invariants.md
git commit -m "Add mixed ingest invariant tests"
```

## Done Criteria

- pytest passes
- generic chunk schema invariant tested
- mixed reporting summaries tested
- both warning conditions tested
- CLI help exposes `--chunk-mode`
- no production behavior changes
