# P3-22A Task - Persist chunk_type Metadata to Chroma

## Context

P3-17 documented integration gap 2:

```text
embed_chunks.safe_metadata() persists only:
doc_id, source, page_start, page_end, chunk_index, page_chunk_index, token_count

It drops:
chunk_type and table-related metadata
```

P3-19 closed gap 1: all chunks are now schema-compatible. P3-20/P3-21 stabilized
mixed ingest reporting and artifact cleanup.

Before automatic retrieval mode selection, Chroma metadata must expose at least
`chunk_type`.

## Goal

Update `scripts/embed_chunks.py` so Chroma metadata keeps safe scalar chunk
metadata needed by future retrieval logic.

Persist:

- `chunk_type`
- `section_title`
- `table_title`
- `table_context`
- `row_count`

Keep existing metadata fields unchanged:

- `doc_id`
- `source`
- `page_start`
- `page_end`
- `chunk_index`
- `page_chunk_index`
- `token_count`

Do not implement automatic retrieval mode selection.

## Chroma Scalar Constraint

Chroma metadata should only contain scalar values:

- `str`
- `int`
- `float`
- `bool`
- `None`

Do not persist `column_headers` as a list. Prefer omitting it for this slice.

## Tests

Add tests for `safe_metadata()`:

- preserves `chunk_type` and scalar table metadata
- preserves generic chunk default metadata
- omits `text`
- omits `column_headers`

## Documentation

Create:

- `docs/experiments/CHROMA_CHUNK_TYPE_METADATA_EXPERIMENT.md`

Update:

- `docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md`

## Verification

Run:

```bash
.venv/bin/python -m pytest tests
.venv/bin/python -m py_compile scripts/embed_chunks.py
git diff --check
git status --short
```

Also run small generic and mixed ingest smokes and inspect Chroma metadata for
`chunk_type` if practical.

## Non-goals

Do not:

- implement automatic retrieval mode selection
- change retrieval modes
- change `ask_chunks.py`
- change `eval_retrieval.py`
- persist `column_headers` as a list
- run model/API calls

## Commit

```bash
git commit -m "Persist chunk type metadata in Chroma"
```
