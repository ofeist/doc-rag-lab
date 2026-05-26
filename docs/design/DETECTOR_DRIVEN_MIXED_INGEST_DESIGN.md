# Detector-Driven Mixed Ingest Integration (P3-17, design-only)

This document designs how the experimental detector-driven mixed chunking path
should move toward the normal user-facing ingest command. It changes no code and
no pipeline behavior. It is a design contract for the thin implementation slices
that follow (P3-18..P3-22).

Phase 3 has proven the experimental path: P3-13 showed strong retrieval on one
shared mixed corpus, and P3-16 showed 39 PASS / 1 PARTIAL / 0 FAIL answer quality
on that corpus. The path works, but it is still manual and explicit. The question
is how to expose it as a single ingest mode without disturbing the proven generic
pipeline.

## 1. Current state

### Normal ingest (proven, default)

| script | responsibility |
| --- | --- |
| `scripts/extract_pages.py` | extract raw page text -> `data/raw_pages.jsonl` |
| `scripts/chunk_pages.py` | page-aware token-window chunks -> `data/chunks.jsonl` |
| `scripts/embed_chunks.py` | embed chunks into ChromaDB |
| `scripts/ingest_document.py` | wrapper: extract -> chunk -> embed (`--reset`) |

`ingest_document.py` runs a fixed three-step chain (extract, `chunk_pages`,
`embed_chunks`) and adds `doc_id` to every record. It has no concept of table
detection or chunk modes today.

### Experimental mixed path (proven, manual)

| script | responsibility |
| --- | --- |
| `scripts/detect_table_pages.py` | score pages; emit candidate JSONL with `page_type` + `recommended_chunker` |
| `scripts/build_table_aware_chunks.py` | parse address-map rows into `table_row_group` + `generic_residual` chunks |
| `scripts/build_mixed_chunks.py` | combine `generic_page` chunks (non-table pages) with table-aware chunks (detected pages) |

The mixed path is run by hand as four explicit steps:

```text
extract_pages.py
  -> detect_table_pages.py     (writes data/table_page_candidates_*.jsonl)
  -> build_mixed_chunks.py     (writes data/chunks_mixed_*.jsonl)
  -> embed_chunks.py
```

`detect_table_pages.py` classifies each page into `page_type` ∈
{`address_map_table`, `generic_table`, `prose`, `unknown`} and sets
`recommended_chunker` to `table_row_group` only for `address_map_table`.
`build_mixed_chunks.py` selects a page for table-aware chunking when
`recommended_chunker == "table_row_group"` **and** `table_likelihood >=
--min-table-score` (default `0.5`); every other page becomes `generic_page`.

This works but has three rough edges that integration must address:

- It is four manual commands with hand-managed intermediate file paths.
- The mixed chunk schema is richer than the generic schema (see section 5).
- `embed_chunks.safe_metadata()` persists only 7 fields to Chroma today and drops
  `chunk_type` and all table fields (see sections 5 and 6).

## 2. Desired ingest modes

A single `--chunk-mode` selector on `ingest_document.py`:

| mode | behavior | chunk types emitted |
| --- | --- | --- |
| `generic` | current behavior; page-aware token-window chunks only | `generic_page` |
| `table-aware` | table-aware chunks for explicitly selected table pages only | `table_row_group`, `generic_residual` |
| `mixed` | detector-driven: `generic_page` for non-table pages, `table_row_group` + `generic_residual` for detected table pages | all three |

`--detect-tables` controls whether the detector runs. It is implied by `mixed`.
For `table-aware` the caller selects pages explicitly (via `--page-ranges` or a
candidate file) rather than relying on the detector.

**Default: `generic`.** `mixed` is opt-in. Rationale: `generic` is the proven,
fast, low-risk path that the answer layer already handles for prose; `mixed` adds
a detector and a richer schema whose global BM25 effects we are still
characterizing (P3-16 saw a one-rank BM25 shift purely from a shorter section
title). Keeping `generic` default means integrating `mixed` cannot regress
existing behavior unless explicitly requested.

## 3. Proposed CLI

Add to `scripts/ingest_document.py`:

```text
--chunk-mode {generic,table-aware,mixed}   default: generic
--detect-tables                            run detector (implied by mixed)
--min-table-score FLOAT                    detector selection threshold (default 0.5)
--section-title STR                        section label for table-aware chunks
--keep-intermediate-artifacts              keep raw/candidate/chunk JSONL after ingest
```

Existing flags (`--pdf`, `--page-ranges`, `--doc-id`, `--collection`, `--db`,
`--chunk-size`, `--overlap`, `--embedding-model`, `--reset`) are unchanged. This
CLI is a proposal, not final.

### Generic ingest (default, unchanged behavior)

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --doc-id aurix_tc3xx \
  --collection technical_docs \
  --chunk-mode generic \
  --reset
```

### Mixed ingest over selected ranges (the P3-13 / P3-16 eval slices)

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-126,257-259,307-314,1364-1397,1435-1455,1483-1488 \
  --doc-id aurix_tc3xx_eval_slices \
  --collection technical_docs \
  --chunk-mode mixed \
  --detect-tables \
  --section-title "Multi-Slice Shared Corpus" \
  --reset
```

### Full-document mixed ingest

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --doc-id aurix_tc3xx_full \
  --collection technical_docs \
  --chunk-mode mixed \
  --detect-tables \
  --reset
```

Internally, `mixed` runs extract -> detect -> build_mixed -> embed; `generic` runs
the current extract -> chunk -> embed; `table-aware` runs extract -> build
table-aware (over selected pages) -> embed. The wrapper owns the intermediate file
paths so the user never passes them by hand.

## 4. Intermediate artifacts policy

The mixed path produces three intermediate files: `data/raw_pages_*.jsonl`,
`data/table_page_candidates_*.jsonl`, `data/chunks_*.jsonl`.

Options considered:

- **A — keep explicit intermediate files** always (current manual behavior).
- **B — temp dir**, deleted after a successful ingest.
- **C — user-selectable** via a flag.

**Recommendation: C, biased to clean.** Default to writing the stable chunk JSONL
output only and removing the raw-page and candidate intermediates after a
successful embed; `--keep-intermediate-artifacts` retains all of them for
debugging the detector or chunker. The chunk JSONL is the one artifact worth
keeping by default because it is what was embedded and what BM25 loads at query
time.

In all cases: **never commit generated `data/` or `vector_db/` artifacts.** They
are already gitignored and that must not change.

## 5. Output chunk schema

All chunk modes must emit a single compatible schema. Table fields are empty for
non-table chunks rather than absent.

| field | type | generic_page | table_row_group | generic_residual |
| --- | --- | --- | --- | --- |
| `chunk_id` | str | yes | yes | yes |
| `doc_id` | str | yes | yes | yes |
| `source` | str | yes | yes | yes |
| `page_start` | int | yes | yes | yes |
| `page_end` | int | yes | yes | yes |
| `page_chunk_index` | int | yes | yes | yes |
| `chunk_index` | int | yes | yes | yes |
| `token_count` | int | yes | yes | yes |
| `text` | str | yes | yes | yes |
| `chunk_type` | str | `generic_page` | `table_row_group` | `generic_residual` |
| `section_title` | str | `""` | set | set |
| `table_title` | str | `""` | set | `""` |
| `table_context` | str | `""` | e.g. `Segment 8` | `""` |
| `column_headers` | list[str] | `[]` | set | `[]` |
| `row_count` | int | `0` | n | `0` |

`build_mixed_chunks.py` already emits exactly this schema. **Two gaps to close
during implementation, not now:**

1. `chunk_pages.py` (generic path) emits the first nine fields only — no
   `chunk_type` or table fields, and `doc_id` is injected later by
   `ingest_document.add_doc_id()`. To make `generic` schema-compatible, generic
   chunks must also carry `chunk_type="generic_page"` and empty table fields.
2. `embed_chunks.safe_metadata()` persists only `doc_id, source, page_start,
   page_end, chunk_index, page_chunk_index, token_count` to Chroma. It drops
   `chunk_type` and the table fields. Any retrieval feature that wants to filter
   or boost by `chunk_type` from the vector store needs `chunk_type` (at least)
   added to the persisted metadata. `column_headers` is a list and Chroma metadata
   is scalar-only, so it would be stored as a joined string or omitted.

These gaps do not block this design; they are why the migration plan sequences
schema work before retrieval work.

## 6. Retrieval mode implications (design only)

Current manual mode selection per slice:

```text
memory_map        bm25_table_boost
boot_bmhd         hybrid
dma_cache         hybrid
interrupt_routing hybrid
```

Future direction (not implemented here):

- `hybrid` stays the default for general / prose queries.
- `bm25_table_boost` applies when the corpus contains `table_row_group` chunks
  **and** the query looks table-like (address / register / hex / segment terms).

Signals already available for a future auto-selector:

- corpus signal: presence of `chunk_type == table_row_group` chunks. From the
  chunks JSONL this is direct; from Chroma it requires the section-5 metadata fix.
- query signal: the table-like keyword set already used by
  `bm25_table_boost_search` (address / table / register / hex / segment-like
  terms).

Do not build automatic retrieval-mode selection yet. The note here only records
the signals so the later slice (P3-22) does not have to rediscover them.

## 7. Failure modes and guardrails

Expected problems:

- detector over-selects pages (prose routed as `table_row_group`);
- detector misses real table pages (tables fall back to `generic_page`);
- a `generic_table` page is misrouted;
- large PDFs produce many intermediate artifacts;
- full-document ingest is slow;
- BM25 / global statistics shift when corpus size or chunk text changes (observed
  in P3-16: a shorter `--section-title` moved one dma_cache question from rank 1
  to rank 2 with no change to hit@3 / hit@5);
- answer quality tracks retrieval quality (P3-16: the single PARTIAL was the one
  question with incomplete retrieval).

Guardrails for `mixed` mode:

- print the detector summary (scanned pages, detected table pages, page types);
- print chunk-type counts (`generic_page`, `table_row_group`, `generic_residual`);
- warn if `table_row_group` count is 0 (detector selected nothing — likely the
  wrong page ranges or threshold);
- warn if too many pages are table-routed (e.g. above a configurable fraction —
  likely over-selection);
- `generic` remains the fallback / default, so a misbehaving detector never
  silently degrades a plain ingest.

`build_mixed_chunks.py` already prints the detector and chunk-type summary and
warns when no table pages are selected; integration should preserve and surface
these through `ingest_document.py`.

## 8. Migration plan (thin slices)

Conservative sequence, each slice independently shippable:

- **P3-18** — add `--chunk-mode {generic,mixed}` to `ingest_document.py`,
  `generic` default. Wire `generic` to the current chain; `mixed` may be a stub
  that errors with a clear message until P3-19. No behavior change for default.
- **P3-19** — make `mixed` ingest write a schema-compatible chunk JSONL (close
  section-5 gap 1: generic chunks carry `chunk_type` + empty table fields) and
  embed it end to end. Re-confirm the P3-13 / P3-16 baselines.
- **P3-20** — add the ingest report summary (detector summary + chunk-type counts
  + guardrail warnings) to `ingest_document.py` output.
- **P3-21** — add `--keep-intermediate-artifacts`; default to writing the chunk
  JSONL only and cleaning raw/candidate intermediates.
- **P3-22** — design and implement automatic retrieval-mode selection using the
  section-6 signals (requires section-5 gap 2: persist `chunk_type` to Chroma).

## 9. Non-goals

This design does not introduce, and the slices above do not build:

- a reranker;
- parent-child retrieval;
- an ML table classifier;
- Camelot / Unstructured / Docling / any PDF layout parser;
- automatic answer grading;
- production full-document indexing as a guaranteed/tuned deliverable.

The detector stays the same heuristic scorer it is today. This document only
defines how to expose the proven experimental path as a normal ingest mode, with
`generic` remaining the safe default.
