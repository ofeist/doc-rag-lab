# P3-20 Task - Ingest Report Summary and Guardrail Warnings

## Context

P3-19 implemented `ingest_document.py --chunk-mode mixed` end-to-end
(extract -> detect_table_pages -> build_mixed_chunks -> embed). P3-17 said mixed
ingest should surface a detector summary, chunk-type counts, and guardrail
warnings. P3-20 is an observability/UX slice only.

## Goal

Improve `scripts/ingest_document.py` mixed-mode console output. No change to
retrieval, chunking, detector logic, answer generation, or Chroma metadata.

## Required output (mixed mode)

After embedding, print a clear final report:

- Ingest summary: chunk_mode, doc_id, page range, raw pages path, table candidates
  path, chunks path, db path, collection, pages extracted, chunks written.
- Table detection: candidate pages emitted, address_map_table count,
  generic_table count, table_row_group routed pages.
- Chunk types: generic_page, table_row_group, generic_residual counts.

## Guardrail warnings (print, never fail)

- `table_row_group` count == 0:
  `WARNING: no table_row_group chunks were produced. Mixed mode behaved like generic ingest.`
- routed pages / total pages > 0.60:
  `WARNING: more than 60% of pages were routed to table_row_group. Check detector over-selection.`

## Non-goals

No detector scoring change, no chunking change, no retrieval eval change, no
persisting `chunk_type` to Chroma, no auto retrieval selection, no
`--keep-intermediate-artifacts`, no model/API calls. Do not modify
`detect_table_pages.py` or `build_mixed_chunks.py` unless a real bug appears.

## Verification

1. `py_compile scripts/ingest_document.py`.
2. Generic smoke (`90-91`): still works, no mixed report/warnings.
3. Mixed smoke (shared ranges): report includes detector summary + chunk-type
   counts, no false failure.
4. Optional warning smoke (prose-only range): if `table_row_group` == 0, confirm
   warning appears; do not tune the detector.
5. `git diff --check`, `git status --short`; no `data/` or `vector_db/` committed.

## Docs

- New `docs/experiments/MIXED_INGEST_REPORTING_EXPERIMENT.md`: what was added,
  example report, warnings, verification commands, non-goals.
- Short P3-20 done note in `docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md`.

## Commit

```text
git add scripts/ingest_document.py \
        docs/experiments/MIXED_INGEST_REPORTING_EXPERIMENT.md \
        docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md \
        tasks/35-P3-20-Ingest-report-summary-and-guardrail-warnings.md
git commit -m "Add mixed ingest reporting guardrails"
```

## Done Criteria

- mixed ingest prints detector summary + chunk-type counts
- warning when no table_row_group chunks produced
- warning when too many pages table-routed
- generic ingest still works
- no retrieval/chunking behavior changes
