# Mixed Chunk Corpus Experiment (P3-9)

## Purpose

P3-8 proved that detector output can drive the table-aware builder. The next
step is one combined chunk file that can contain both normal prose chunks and
table-aware chunks.

This is an experimental mixed corpus builder. It does not yet replace the normal
ingest pipeline.

## Script

```text
scripts/build_mixed_chunks.py
```

The script reads:

```text
data/raw_pages.jsonl
data/table_page_candidates_memory_map.jsonl
```

It writes one combined chunks JSONL, for example:

```text
data/chunks_mixed_memory_map.jsonl
```

## Chunk Types

The output can contain:

```text
generic_page
table_row_group
generic_residual
```

Meaning:

| chunk_type | Source pages | Purpose |
| --- | --- | --- |
| `generic_page` | pages not selected by detector | normal prose/token-window coverage |
| `table_row_group` | detected table pages | table rows with repeated table/header context |
| `generic_residual` | detected table pages | non-table text from table-heavy pages |

Every chunk keeps the schema expected by `embed_chunks.py`:

```text
chunk_id
doc_id
source
page_start
page_end
page_chunk_index
chunk_index
token_count
text
```

and table-aware metadata:

```text
chunk_type
section_title
table_title
table_context
column_headers
row_count
```

## CLI Example

```bash
.venv/bin/python scripts/build_mixed_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_mixed_memory_map.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_memory_map.jsonl \
  --min-table-score 0.5 \
  --section-title "Memory Maps (MEMMAP)" \
  --chunk-size 800 \
  --overlap 120 \
  --table-group-size 4 \
  --table-residual-chunk-size 300 \
  --table-residual-overlap 60
```

## Memory Map Validation

Detector result:

```text
input pages: 13
detected table pages: 13
generic pages: 0
selected pages: 90-102
```

Mixed builder output:

```text
chunks: 102
generic_page chunks: 0
table_row_group chunks: 91
generic_residual chunks: 11
table rows: 298
segment markers: accepted=31 skipped=0
```

For this focused `memory_map` slice, all pages are selected by the detector. The
mixed output therefore behaves like the detector-driven table-aware output. That
is acceptable for this slice; the interface is meant for larger documents where
many pages will remain generic.

Retrieval result:

| Corpus | Mode | hit@1 | hit@3 | hit@5 |
| --- | --- | ---: | ---: | ---: |
| table-aware only | bm25 | 80% | 80% | 100% |
| table-aware only | bm25_table_boost | 80% | 100% | 100% |
| mixed corpus | bm25 | 80% | 80% | 100% |
| mixed corpus | bm25_table_boost | 80% | 100% | 100% |

The mixed corpus preserves the known `memory_map` retrieval result.

## Limitations

- This is not wired into `scripts/ingest_document.py`.
- It does not build a production corpus manifest.
- It does not auto-select retrieval mode.
- It does not add parent-child retrieval, reranking, or PDF table parsing.
- The current validation slice selects all pages as table-heavy, so future
  validation should use a broader page range with both prose and table pages.

## Next Recommendation

P3-10 should test mixed chunking on a broader range or full document section
where detector output includes both:

```text
generic prose pages
table-heavy pages
```

After that, the next useful step is automatic retrieval mode selection:

```text
normal/hybrid retrieval for prose-heavy queries
bm25_table_boost when table_row_group chunks and table-like queries are present
```
