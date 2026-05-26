# Phase 3 Table Retrieval Summary

## Status

Phase 3 has proven the table-heavy retrieval path as a lab workflow.

The normal ingest pipeline is still unchanged. All table-specific work remains
experimental and explicit.

## What Phase 3 Proved

Dense table-heavy technical content needs different handling than prose or
semi-structured sections.

For the `memory_map` slice, the best current measured result is:

```text
bm25:              80 / 80 / 100
bm25_table_boost:  80 / 100 / 100
```

The practical result is:

```text
detected table pages -> table-aware chunks -> bm25_table_boost -> answer path
```

## Completed Slices

| Slice | Result |
| --- | --- |
| P3-2 table chunks | Added table-aware row-group chunks for `memory_map`; improved dense table retrieval over generic 300/60 chunks. |
| P3-3 table ranking | Added `bm25_table_boost`; improved table-heavy ranking to `80 / 100 / 100`. |
| P3-5 generalized builder | Replaced the memory-map-specific builder with `scripts/build_table_aware_chunks.py`. |
| P3-6B answer path | Added `bm25_table_boost` support to `ask_chunks.py` and `run_answer_eval.py`. |
| P3-7 detector | Added `scripts/detect_table_pages.py` to identify table-heavy candidate pages from extracted text. |
| P3-8 detector-driven builder | Added `--table-candidates` support to `build_table_aware_chunks.py`. |
| P3-9 mixed chunks | Added `scripts/build_mixed_chunks.py` to produce one combined chunk JSONL with generic and table-aware chunk types. |

## Current Experimental Tools

```text
scripts/detect_table_pages.py
scripts/build_table_aware_chunks.py
scripts/build_mixed_chunks.py
```

Supported table-aware retrieval mode:

```text
bm25_table_boost
```

Supported table-aware chunk types:

```text
table_row_group
generic_residual
generic_page
```

## Key Workflow

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memory_map.jsonl \
  --page-ranges 90-102 \
  --min-score 0.5

.venv/bin/python scripts/build_mixed_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_mixed_memory_map.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_memory_map.jsonl \
  --min-table-score 0.5 \
  --section-title "Memory Maps (MEMMAP)"
```

## Important Limitations

- Table detection is heuristic, not ML-based.
- The detector is validated mainly on the `memory_map` slice.
- Mixed chunking is not wired into `scripts/ingest_document.py`.
- Retrieval mode selection is still manual.
- No parent-child retrieval, reranker, or PDF table parser has been added.
- No production corpus/versioning workflow exists yet.

## Next Step

The next useful slice should test the mixed chunk workflow on a broader page
range that contains both prose and dense tables.

After that, the likely next technical step is automatic retrieval mode selection:

```text
use normal/hybrid retrieval for prose-heavy queries
use bm25_table_boost when table_row_group chunks exist and the query is table-like
```
