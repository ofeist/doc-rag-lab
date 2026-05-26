# P3-19 Task - Schema-Compatible Mixed Ingest End-to-End

## Context

P3-17 designed mixed ingest integration; P3-18 added the `--chunk-mode
{generic,mixed}` skeleton (`mixed` exited as not-implemented). P3-17 documented
two gaps: (1) generic chunks are not schema-compatible with mixed chunks; (2)
`embed_chunks.safe_metadata()` does not persist `chunk_type` to Chroma. P3-19
closes gap 1 and implements mixed ingest end-to-end. Gap 2 (persist `chunk_type`)
stays deferred to P3-22 (auto retrieval-mode selection).

## Goal

Implement `--chunk-mode mixed` in `scripts/ingest_document.py`, running
`extract_pages -> detect_table_pages -> build_mixed_chunks -> embed_chunks`, and
make generic ingest output schema-compatible without changing its retrieval
behavior.

## Required behavior

- default (no `--chunk-mode`) = generic, unchanged.
- `--chunk-mode generic` works; output carries `chunk_type=generic_page` + empty
  table fields.
- `--chunk-mode mixed` works end-to-end and produces `generic_page`,
  `table_row_group`, `generic_residual` chunks.

## CLI additions (mixed)

`--section-title ""`, `--min-table-score 0.5`, `--table-group-size 4`,
`--table-residual-chunk-size 300`, `--table-residual-overlap 60`. Reuse existing
`--chunk-size` / `--overlap` for generic chunks. No `--keep-intermediate-artifacts`
(that is P3-21).

## Schema (all chunks)

`chunk_id, doc_id, source, page_start, page_end, page_chunk_index, chunk_index,
token_count, text, chunk_type, section_title, table_title, table_context,
column_headers, row_count`. Generic chunks use `chunk_type=generic_page` and empty
table fields.

## Non-goals

No `--keep-intermediate-artifacts`, no auto retrieval-mode selection, no answer
eval, no changes to `ask_chunks.py` / `eval_retrieval.py` (unless a real
compatibility bug), no reranker / parent-child / PDF layout parser, no model/API
calls. Do not persist `chunk_type` to Chroma in this slice.

## Verification

1. `py_compile` ingest_document, chunk_pages, detect_table_pages,
   build_mixed_chunks, embed_chunks.
2. Generic smoke (`90-91`): chunks JSONL has `chunk_type: generic_page` + empty
   table fields.
3. Default smoke (no flag): identical.
4. Mixed smoke on shared eval ranges
   (`90-126,257-259,307-314,1364-1397,1435-1455,1483-1488`): all three chunk types
   present.
5. Run four retrieval evals against `data/chunks_<doc_id>.jsonl`; compare to
   P3-13/P3-16 baseline. Document hit@1 differences; do not tune.
6. `git diff --check`, `git status --short`; no `data/` or `vector_db/` committed.

## Docs

- Status note in `docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md`.
- New `docs/experiments/MIXED_INGEST_END_TO_END_EXPERIMENT.md`: commands, chunk
  distribution, generic schema-compat result, retrieval results, remaining gap
  (chunk_type not persisted to Chroma), verdict, next step.

## Commit

```text
git add scripts/ingest_document.py scripts/chunk_pages.py
git add docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md
git add docs/experiments/MIXED_INGEST_END_TO_END_EXPERIMENT.md
git add tasks/34-P3-19-Schema-compatible-mixed-ingest-end-to-end.md
git commit -m "Implement schema-compatible mixed ingest"
```

## Done Criteria

- default + `--chunk-mode generic` work; generic output schema-compatible
- `--chunk-mode mixed` works end-to-end with all three chunk types
- four retrieval evals run against mixed output; results documented
- generated `data/` and `vector_db/` artifacts not committed
- auto retrieval selection not implemented
