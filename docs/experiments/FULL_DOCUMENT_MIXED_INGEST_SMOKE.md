# Full-Document Mixed Ingest Smoke Test

## Goal

Run a conservative, full-document smoke test for detector-driven mixed ingest:

- no detector tuning
- no chunking changes
- no retrieval tuning
- no answer/model API calls

This is validation of plumbing and rough behavior under full-document scale, not
production readiness.

## Command Used

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --doc-id aurix_tc3xx_full_mixed_smoke \
  --collection technical_docs \
  --chunk-mode mixed \
  --section-title "AURIX TC3xx Full Mixed Smoke" \
  --reset
```

## Ingest Summary

From the mixed ingest report:

- pages extracted: `2080`
- table candidate pages emitted: `135`
- candidate page types:
  - `address_map_table`: `22`
  - `generic_table`: `113`
- `table_row_group` routed pages: `22`
  - pages: `[91..110]` and `[553, 554]`
- chunks written (JSONL lines): `2593`
- chunk types:
  - `generic_page`: `2406`
  - `table_row_group`: `164` (`575` total parsed rows)
  - `generic_residual`: `23`
- rough runtime: embedding phase completed in about `9-10 minutes` for `2593`
  chunks (batch size `32`).

### Artifact Cleanup Behavior

Default mixed cleanup behaved as intended:

- kept: `data/chunks_aurix_tc3xx_full_mixed_smoke.jsonl`
- deleted after successful embed:
  - `data/raw_pages_aurix_tc3xx_full_mixed_smoke.jsonl`
  - `data/table_page_candidates_aurix_tc3xx_full_mixed_smoke.jsonl`

## Chroma Metadata Inspection

Quick inspection via `chromadb.PersistentClient(...).get_collection(...).get(...)`
shows persisted scalar metadata includes `chunk_type` (and table scalars):

- `chunk_type`
- `section_title`
- `table_title`
- `table_context`
- `row_count`

As expected, `column_headers` is not present (list-valued).

## Retrieval Smoke (Auto Mode)

All retrieval evals used the full mixed corpus chunks:

`--chunks data/chunks_aurix_tc3xx_full_mixed_smoke.jsonl`

### memory_map (auto)

- hit@1: `10/10` (100%)
- hit@3: `10/10` (100%)
- hit@5: `10/10` (100%)

### boot_bmhd (auto)

- hit@1: `5/10` (50%)
- hit@3: `8/10` (80%)
- hit@5: `10/10` (100%)

Notes:
- This is weaker than the focused/shared corpus runs, which is expected due to
  higher retrieval competition in the full document.
- This slice is smoke-only; no tuning was performed.

### dma_cache (auto)

- hit@1: `8/10` (80%)
- hit@3: `10/10` (100%)
- hit@5: `10/10` (100%)

### interrupt_routing (auto)

- hit@1: `7/10` (70%)
- hit@3: `10/10` (100%)
- hit@5: `10/10` (100%)

## ask_chunks Dry-Run (No API)

Command:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/ask_chunks.py \
  --question "What address range maps to Program Flash 0?" \
  --chunks data/chunks_aurix_tc3xx_full_mixed_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --mode auto \
  --dry-run \
  --show-context \
  --top-k 5
```

Observed behavior:

- auto selected `bm25_table_boost`
- retrieved context included the expected Table 24 address map rows for Program
  Flash 0 (PF0)

## Known Limitations (Observed/Expected)

- Full-document retrieval introduces more competition; hit@1/hit@3 can degrade
  relative to focused slices even when hit@5 remains stable.
- Mixed detection routed a small fraction of pages to `table_row_group` (22 out
  of 2080), which is reasonable for this document but still heuristic.
- This run does not validate production performance, memory requirements, or
  detector precision across arbitrary large manuals.

## Verdict

Full-document mixed ingest works end-to-end:

- completes successfully
- intermediate cleanup behavior is correct by default
- Chroma metadata includes `chunk_type`
- retrieval and `--mode auto` behavior remains correct
- retrieval quality remains strong for table-heavy slices (memory_map), while
  some prose-heavy slices show the expected competition effects

## Recommended Next Step

P3-25: README/CLI polish for the now-integrated user-facing workflow, including
one canonical full-document mixed smoke command and one canonical shared-corpus
command, plus expected report/guardrail outputs.

