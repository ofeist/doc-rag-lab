# Large-Section Mixed Ingest Smoke Test (P3-12)

## Scope

This is a large-section smoke test. It does not replace the normal ingest
pipeline.

Range tested:

```text
90-200
```

Input document:

```text
docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
```

## Commands Used

```bash
.venv/bin/python scripts/extract_pages.py \
  docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-200 \
  --out data/raw_pages_large_section.jsonl
```

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages_large_section.jsonl \
  --output data/table_page_candidates_large_section.jsonl \
  --page-ranges 90-200 \
  --min-score 0.5
```

```bash
.venv/bin/python scripts/build_mixed_chunks.py \
  --input data/raw_pages_large_section.jsonl \
  --output data/chunks_mixed_large_section.jsonl \
  --doc-id large_section_90_200 \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_large_section.jsonl \
  --min-table-score 0.5 \
  --section-title "Large Section Mixed Smoke Test" \
  --chunk-size 800 \
  --overlap 120 \
  --table-group-size 4 \
  --table-residual-chunk-size 300 \
  --table-residual-overlap 60
```

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_mixed_large_section.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_large_section.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode hybrid \
  --eval eval/boot_bmhd_eval.json \
  --chunks data/chunks_mixed_large_section.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8
```

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode hybrid \
  --eval eval/dma_cache_eval.json \
  --chunks data/chunks_mixed_large_section.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8
```

## Detector Summary

```text
pages scanned: 111
candidates emitted: 25
address_map_table: 20
generic_table: 5
recommended table_row_group pages:
91-110
```

Selected table pages:

```text
91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110
```

Generic pages:

```text
90,111-200
```

## Mixed Chunk Distribution

```text
total chunks: 273
generic_page: 100
generic_residual: 21
table_row_group: 152
pages covered: 90-200
```

Acceptance condition passed:

```text
generic_page > 0
generic_residual > 0
table_row_group > 0
```

## Retrieval Results

### memory_map (`bm25_table_boost`)

```text
hit@1: 100%
hit@3: 100%
hit@5: 100%
```

This is above the smoke target (`hit@3 >= 90%`, `hit@5 >= 100%`).

### boot_bmhd (`hybrid`)

```text
hit@1: 60%
hit@3: 80%
hit@5: 90%
```

This meets the smoke thresholds (`hit@3 >= 80%`, `hit@5 >= 90%`), but is weaker
than the tighter small-range result from P3-11 (`70/90/100`).

`boot-005` remains the known weaker procedural query.

### dma_cache (`hybrid`)

```text
hit@1: 0%
hit@3: 0%
hit@5: 0%
```

This eval is not valid for this smoke range: `dma_cache_eval.json` expects pages
outside `90-200` (for example 257+, 300+, 1400+), so failure is expected and not
actionable for this slice.

## Observations

1. Detector behavior is conservative for table routing: only `address_map_table`
   pages are routed to `table_row_group`.
2. Over-selection still exists: pages `103-110` are selected as table pages, but
   this appears content-driven (Segment F address map tables), not arbitrary prose.
3. Mixed corpus behavior works at larger scale: all three chunk types are present
   and embedding/retrieval pipeline runs end-to-end.
4. Boot/BMHD stability is acceptable for smoke, but weaker than smaller focused
   runs.

## Artifact Size Notes

```text
data/raw_pages_large_section.jsonl:            272K (111 lines)
data/table_page_candidates_large_section.jsonl: 16K (25 lines)
data/chunks_mixed_large_section.jsonl:         396K (273 lines)
```

## Verdict

Accept this smoke test.

The large-section mixed ingest path works and remains stable for the key
`memory_map` target. Boot/BMHD remains usable at smoke level. `dma_cache` should
not be evaluated on this range.

## Next Recommendation

Run a dedicated larger-range smoke that includes the expected pages for all
target eval slices (memory_map + boot_bmhd + dma_cache) to compare retrieval
stability on one shared corpus.

Do not wire this into the normal ingest pipeline yet.
