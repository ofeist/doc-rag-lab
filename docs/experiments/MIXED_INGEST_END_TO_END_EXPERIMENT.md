# Mixed Ingest End-to-End (P3-19)

This records the first end-to-end run of detector-driven mixed chunking through
the normal ingest command, `scripts/ingest_document.py --chunk-mode mixed`. It
closes integration gap 1 from P3-17 (generic chunks are now schema-compatible) and
wires the proven experimental scripts into one user-facing command. The retrieval
and answer layers are unchanged.

## What changed

- `scripts/chunk_pages.py`: generic chunks now carry `chunk_type="generic_page"`
  plus empty table fields (`section_title`, `table_title`, `table_context`,
  `column_headers`, `row_count`), so every ingest mode emits one common schema.
  `doc_id` is still added by ingest. Retrieval behavior is unchanged (the extra
  fields are ignored by BM25/vector ranking).
- `scripts/ingest_document.py`: `--chunk-mode mixed` now runs
  `extract_pages -> detect_table_pages -> build_mixed_chunks -> embed_chunks` over
  doc_id-scoped intermediate files under `data/`. Mixed mode reuses the proven
  experimental scripts directly (subprocess orchestration), so its output matches
  the manual P3-13/P3-16 path. New mixed-mode flags: `--section-title`,
  `--min-table-score`, `--table-group-size`, `--table-residual-chunk-size`,
  `--table-residual-overlap`. `generic` remains the default.

## Commands

Generic (default unchanged):

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-91 --doc-id p3_19_generic_smoke \
  --collection technical_docs --chunk-mode generic --reset
```

Mixed over the shared eval ranges:

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-126,257-259,307-314,1364-1397,1435-1455,1483-1488 \
  --doc-id p3_19_mixed_shared --collection technical_docs \
  --chunk-mode mixed --section-title "P3-19 Mixed Shared Corpus" --reset
```

## Generic schema compatibility

The generic chunk JSONL now contains all 15 schema fields. First chunk of the
generic smoke:

```text
keys: chunk_id, chunk_index, chunk_type, column_headers, doc_id,
      page_chunk_index, page_end, page_start, row_count, section_title,
      source, table_context, table_title, text, token_count
chunk_type = generic_page; table fields empty; doc_id set
```

## Chunk distribution (mixed)

Identical structure to the manual P3-13 / P3-16 shared corpus:

```text
total chunks      : 269
generic_page      : 96
table_row_group   : 152  (527 rows)
generic_residual  : 21
detected table pages (address_map_table -> row_group): 20  (p91-110)
input pages       : 109
```

Generated `data/` and `vector_db/` artifacts are not committed.

## Retrieval eval (mixed corpus)

Primary run, mixed ingest with `--section-title "P3-19 Mixed Shared Corpus"`:

| slice | mode | hit@1 | hit@3 | hit@5 | P3-13 | P3-16 |
| --- | --- | ---: | ---: | ---: | --- | --- |
| memory_map | bm25_table_boost | 100% | 100% | 100% | 100/100/100 | 100/100/100 |
| boot_bmhd | hybrid | 60% | 90% | 100% | 70/100/100 | 70/100/100 |
| dma_cache | hybrid | 90% | 100% | 100% | 100/100/100 | 80/100/100 |
| interrupt_routing | hybrid | 80% | 90% | 100% | 80/100/100 | 80/100/100 |

`hit@5` is 100% for all four slices: every question's expected page lands in the
top-5 answer context.

### On the hit@1 / hit@3 differences

These are not an integration regression. Two effects, both in the retrieval layer,
not in chunking:

1. **BM25 global-stat sensitivity to section title** (already seen in P3-16): the
   table-chunk text repeats `--section-title`, so a different title shifts avg
   doc length / IDF and can move a borderline question by one rank.
2. **HNSW vector-index nondeterminism on rebuild.** A parity rebuild with the
   exact P3-16 title (`"Multi-Slice Shared Corpus"`) produced a byte-identical
   chunk distribution (269 / 96 / 152 / 21, 527 rows) yet still returned hybrid
   hit@1/hit@3 of boot 60/90 and dma 90/100 — different from P3-16's 70/100 and
   80/100. Re-running an eval against a fixed (already-built) index is
   deterministic (boot_bmhd returned 70/100/100 on two back-to-back runs), so the
   variance comes from the index build during `--reset`, not from query time.

`memory_map` uses `bm25_table_boost` (pure BM25, deterministic) and is 100/100/100
on every run. The hybrid slices vary by at most one question at hit@1/hit@3 between
rebuilds; hit@5 is stable at 100% throughout. Per the task, this is documented, not
tuned.

## Known remaining gap

`embed_chunks.safe_metadata()` still persists only `doc_id, source, page_start,
page_end, chunk_index, page_chunk_index, token_count` to Chroma. It does **not**
persist `chunk_type` or the table fields. BM25/`bm25_table_boost` read `chunk_type`
directly from the chunks JSONL, so mixed retrieval works today; but any future
filtering or boosting by `chunk_type` from the vector store needs this field
persisted. This is P3-17 gap 2, deferred to **P3-22** (automatic retrieval-mode
selection).

## Verdict

Mixed ingest works end-to-end through `ingest_document.py` and produces a corpus
structurally identical to the proven manual path. Generic ingest is now
schema-compatible without any change to its retrieval behavior. Retrieval quality
is preserved (hit@5 100% on all four slices); the small hit@1/hit@3 variance is a
documented retrieval-layer property (BM25 title sensitivity + HNSW rebuild
nondeterminism), not an ingest defect.

## Next step

- **P3-20**: surface the detector summary + chunk-type counts + guardrail warnings
  through `ingest_document.py` output (currently only the subprocess steps print
  them).
- **P3-21**: `--keep-intermediate-artifacts` and default cleanup of intermediate
  JSONL.
- **P3-22**: persist `chunk_type` to Chroma and design automatic retrieval-mode
  selection; that slice could also pin/seed the vector index if reproducible
  hit@1/hit@3 is wanted.

This remains experimental opt-in. `generic` is still the default ingest mode.
