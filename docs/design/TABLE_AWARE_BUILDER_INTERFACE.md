# Table-Aware Chunk Builder Interface (P3-5)

## Why this was generalized

P3-2 / P3-3 proved table-aware retrieval helps dense tables:

```text
generic 300/60 baseline:        60 / 60 / 80
table-aware chunks:             80 / 80 / 100
table-aware chunks + ranking:   80 / 100 / 100   (hit@1 / hit@3 / hit@5)
```

The first builder hardcoded the `memory_map` slice (section title, source,
doc-id, page range, output name). The chunking logic was reusable but the
interface was not.

`scripts/build_table_aware_chunks.py` keeps the exact same chunking behavior and
exposes it through flags, so the same experiment can be pointed at other
table-heavy slices.

This is still an **experimental builder, not the normal ingest pipeline**.
`scripts/chunk_pages.py` and `scripts/ingest_document.py` are unchanged, and the
row/table heuristics remain tuned to AURIX-style address-map tables.

## CLI example

```bash
.venv/bin/python scripts/build_table_aware_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_table_aware_memory_map.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-102 \
  --section-title "Memory Maps (MEMMAP)" \
  --group-size 4 \
  --residual-chunk-size 300 \
  --residual-overlap 60
```

| Flag | Required | Default | Meaning |
| --- | :---: | --- | --- |
| `--input` | no | `data/raw_pages.jsonl` | Extracted pages JSONL |
| `--output` | yes | — | Output chunks JSONL (generated, not committed) |
| `--doc-id` | yes | — | `doc_id` written into chunk metadata |
| `--source` | yes | — | Source document path for metadata |
| `--page-ranges` | yes | — | Pages to include (see syntax below) |
| `--section-title` | no | `""` | Title repeated per chunk + stripped as running header |
| `--group-size` | no | `4` | Max table rows per `table_row_group` chunk |
| `--residual-chunk-size` | no | `300` | Token window for non-table text |
| `--residual-overlap` | no | `60` | Token overlap for non-table text |

## Supported page-range syntax

```text
90-102            single inclusive range
90-94,96,100-102  comma list of ranges and single pages
```

Page-range parsing is intentionally minimal (no open-ended or step syntax).

## Output chunk schema

JSONL, one chunk per line, compatible with `scripts/embed_chunks.py`.

Pipeline-required fields:

```text
chunk_id, doc_id, source, page_start, page_end,
page_chunk_index, chunk_index, token_count, text
```

Experimental table metadata:

```text
chunk_type        "table_row_group" | "generic_residual"
section_title     value of --section-title
table_title       e.g. "Table 24 Address Map of Segment 0 to 14 (cont’d)"
table_context     e.g. "Segment 8"   (empty for residual)
column_headers    list (empty for residual)
row_count         table rows in this chunk (0 for residual)
```

`table_row_group` chunks carry the address-map rows with section title, table
title, segment context and column headers repeated per chunk. `generic_residual`
chunks hold the remaining non-table text (prose, acronym lists, footnotes) so
page coverage stays complete for the page-level retrieval eval.

A `table_row_group` chunk looks like:

```text
Memory Maps (MEMMAP)
Table 24 Address Map of Segment 0 to 14 (cont’d)
Segment: 8
Columns: Segment | Address Range | Size | Description | Read | Write

8000 0000H - 802F FFFFH | 3 Mbyte | Program Flash 0 (PF0) | Access | SRIBE
8030 0000H - 805F FFFFH | 3 Mbyte | Program Flash 1 (PF1) | Access | SRIBE
...
```

## Reproduction

```bash
# 1. build
.venv/bin/python scripts/build_table_aware_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_table_aware_memory_map.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-102 \
  --section-title "Memory Maps (MEMMAP)" \
  --group-size 4 --residual-chunk-size 300 --residual-overlap 60

# 2. embed
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma --collection technical_docs --reset

# 3. evaluate
.venv/bin/python scripts/eval_retrieval.py --mode bm25 \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma --collection technical_docs

.venv/bin/python scripts/eval_retrieval.py --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma --collection technical_docs
```

## memory_map validation result

Output is byte-equivalent to the old memory-map-specific builder output except
for the cosmetic `chunk_id` prefix (102 chunks, 91 `table_row_group` + 11
`generic_residual`, 298 rows, 31/31 segment markers accepted). `chunk_id` is not
used by `embed_chunks.py` (it derives its own id from source/page/indices), so
retrieval is identical:

| Mode | hit@1 | hit@3 | hit@5 |
| --- | ---: | ---: | ---: |
| `bm25` | 80% | 80% | 100% |
| `bm25_table_boost` | 80% | 100% | 100% |

Behavior preserved.

## Safety / error handling

- `--residual-overlap >= --residual-chunk-size` exits with a clear error.
- A missing `--input` exits with a clear error.
- A `--page-ranges` value matching no pages in the input exits with a clear error.

## Current limitations

- AURIX-specific heuristics: running-header boilerplate, `Table NN` title lines,
  the `Segm`/`ent`/... header block, and the multiline address-row shape are tuned
  to this manual. They are not a general table detector.
- Row field separation is best-effort; multiline cells are joined with `|`. All
  tokens are preserved, which is what matters for retrieval.
- Segment detection is best-effort and guarded (accepted/skipped counts are
  printed; a warning is shown if any marker is skipped).
- `--section-title` is repeated verbatim; there is no automatic section detection.

## Status of the old script

The memory-map-specific builder was superseded by this generalized builder
(verified equivalent for `memory_map`) and removed in P3-6A. Use
`scripts/build_table_aware_chunks.py` for table-aware chunk experiments.

## Non-goals

No changes to `chunk_pages.py` / `ingest_document.py` / answer generation, no
model calls, no parent-child retrieval, no reranker, no PyMuPDF `find_tables()`,
no general PDF table parser. Integrating table-aware chunks + `bm25_table_boost`
into the answer/retrieval path is a separate future slice.
