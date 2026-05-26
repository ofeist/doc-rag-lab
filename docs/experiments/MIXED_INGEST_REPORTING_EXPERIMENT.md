# Mixed Ingest Reporting and Guardrails (P3-20)

This adds operator-friendly console output to `scripts/ingest_document.py
--chunk-mode mixed`. It is an observability/UX slice only: no change to the
detector, chunking, retrieval, answer generation, or Chroma metadata. Generic mode
keeps its existing JSON summary.

## What was added

After embedding, mixed mode prints a three-part final report plus guardrail
warnings, computed by small helpers in `ingest_document.py`:

- `load_jsonl_records(path)` — read a JSONL file into dicts.
- `summarize_table_candidates(path)` — candidate count + `address_map_table` /
  `generic_table` counts from the detector output.
- `summarize_chunks(path)` — chunk-type counts + the distinct pages routed to
  `table_row_group`.
- `print_mixed_report(...)` — render the report and warnings.

The report sections:

- **Ingest summary** — chunk_mode, doc_id, page range, pdf, raw pages path, table
  candidates path, chunks path, db path, collection, pages extracted, chunks
  written.
- **Table detection** — candidate pages emitted, `address_map_table` count,
  `generic_table` count, `table_row_group` routed pages (count + page list).
- **Chunk types** — `generic_page`, `table_row_group`, `generic_residual` counts.

## Example report (shared eval ranges)

```text
Ingest summary:
  chunk_mode       : mixed
  doc_id           : p3_20_mixed_shared
  page_range       : 90-126,257-259,307-314,1364-1397,1435-1455,1483-1488
  pdf              : docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
  raw_pages        : data/raw_pages_p3_20_mixed_shared.jsonl
  table_candidates : data/table_page_candidates_p3_20_mixed_shared.jsonl
  chunks           : data/chunks_p3_20_mixed_shared.jsonl
  db               : vector_db/chroma
  collection       : technical_docs
  pages_extracted  : 109
  chunks_written   : 269

Table detection:
  candidate pages emitted : 24
  address_map_table       : 20
  generic_table           : 4
  table_row_group routed  : 20 pages [91, 92, ..., 110]

Chunk types:
  generic_page     : 96
  table_row_group  : 152
  generic_residual : 21
```

## Guardrail warnings

Warnings print but never fail the ingest (exit stays 0):

- `table_row_group` count == 0:
  `WARNING: no table_row_group chunks were produced. Mixed mode behaved like generic ingest.`
- routed pages / pages extracted > 0.60
  (`TABLE_ROUTED_PAGE_WARN_RATIO`):
  `WARNING: more than 60% of pages were routed to table_row_group. Check detector over-selection.`

## Verification

Syntax: `.venv/bin/python -m py_compile scripts/ingest_document.py` — OK.

Generic smoke (`--page-ranges 90-91 --chunk-mode generic`): unchanged JSON
summary, no mixed report or warnings, exit 0.

Mixed smoke (shared eval ranges, `--section-title "P3-20 Mixed Shared Corpus"`):
full report as above, no warnings (152 `table_row_group` chunks; routed ratio
20/109 ≈ 18%), exit 0.

Zero-table warning smoke (`--page-ranges 115-126`, boot prose): 0 `table_row_group`
chunks, no-table warning printed, exit 0.

```text
Chunk types:
  generic_page     : 12
  table_row_group  : 0
  generic_residual : 0

WARNING: no table_row_group chunks were produced. Mixed mode behaved like generic ingest.
```

Over-selection warning smoke (`--page-ranges 91-100`, dense address maps): all 10
pages routed (ratio 100% > 60%), over-selection warning printed, exit 0.

```text
Chunk types:
  generic_page     : 0
  table_row_group  : 82
  generic_residual : 10

WARNING: more than 60% of pages were routed to table_row_group. Check detector over-selection.
```

Generated `data/` and `vector_db/` artifacts are not committed.

## Non-goals

No detector scoring change, no chunking change, no retrieval-eval change, no
persisting `chunk_type` to Chroma, no automatic retrieval-mode selection, no
`--keep-intermediate-artifacts`, no model/API calls. The warning thresholds are
descriptive aids for the operator, not gates.

## Next step

- **P3-21**: `--keep-intermediate-artifacts` and default cleanup of intermediate
  JSONL.
- **P3-22**: persist `chunk_type` to Chroma and design automatic retrieval-mode
  selection.
