# Detector-Driven Table Chunking Experiment (P3-8)

## Purpose

P3-7 detects likely table-heavy pages. P3-8 connects that detector output to the
experimental table-aware chunk builder.

This connects detection to chunk building, but still does not modify the normal
ingest pipeline.

## What Changed

`scripts/build_table_aware_chunks.py` now supports:

```text
--table-candidates data/table_page_candidates_memory_map.jsonl
--min-table-score 0.5
```

When `--table-candidates` is provided, the builder reads detector JSONL and
selects pages where:

```text
recommended_chunker == "table_row_group"
table_likelihood >= --min-table-score
```

`--page-ranges` and `--table-candidates` are mutually exclusive. Providing both
fails clearly instead of silently merging selections.

## Example

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memory_map.jsonl \
  --page-ranges 90-102 \
  --min-score 0.5

.venv/bin/python scripts/build_table_aware_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_table_aware_memory_map_auto.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_memory_map.jsonl \
  --min-table-score 0.5 \
  --section-title "Memory Maps (MEMMAP)" \
  --group-size 4 \
  --residual-chunk-size 300 \
  --residual-overlap 60
```

## Validation Result

Detector output on `memory_map`:

```text
scanned pages: 13
detected table-heavy pages: 13
detected address-map pages: 12
selected pages: 90-102
```

Detector-driven builder output:

```text
chunks: 102
table_row_group chunks: 91
generic_residual chunks: 11
rows: 298
segment markers: accepted=31 skipped=0
```

Retrieval results:

| Chunk source | Mode | hit@1 | hit@3 | hit@5 |
| --- | --- | ---: | ---: | ---: |
| manual `--page-ranges 90-102` | bm25 | 80% | 80% | 100% |
| manual `--page-ranges 90-102` | bm25_table_boost | 80% | 100% | 100% |
| detector-driven candidates | bm25 | 80% | 80% | 100% |
| detector-driven candidates | bm25_table_boost | 80% | 100% | 100% |

The detector-driven workflow preserves the manual page-range retrieval result
for `memory_map`.

## Notes

The detector initially selected pages 91-102 at `--min-score 0.5`, which removed
page 90 and caused failures for the acronym/segment-summary eval questions. The
detector scoring now gives a small additional signal to pages with multiple
table references, so page 90 is selected as `generic_table` while dense pages
remain classified as `address_map_table`.

This is a useful reminder: detector output should identify pages useful for
table-heavy retrieval, not only pages that contain dense address rows.

## Limitations

- This is still an explicit experimental builder command.
- Normal `scripts/ingest_document.py` behavior is unchanged.
- The detector is heuristic and tuned only against the current `memory_map`
  evidence.
- No mixed prose+table corpus is built yet.
- No PyMuPDF `find_tables()`, Camelot, Docling, reranker, or ML classifier was
  added.

## Next Recommendation

P3-9 should build a mixed ingest experiment:

```text
generic prose chunks + detector-driven table-aware chunks
```

The goal is to preserve broad prose coverage while adding table-row chunks only
for detected table-heavy pages.
