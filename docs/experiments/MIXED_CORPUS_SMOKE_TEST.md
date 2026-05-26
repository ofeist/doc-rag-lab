# Mixed Corpus Smoke Test (P3-10)

## Purpose

This smoke test checks whether the mixed chunk builder behaves correctly on a
range that contains both dense table pages and prose/semi-structured pages.

This is a smoke test for mixed chunk behavior. It does not replace the normal
ingest pipeline yet.

## Tested Range

```text
PDF: docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
pages: 90-126
```

The range combines:

```text
90-102   MEMMAP / dense address-map pages
115-126  Boot/BMHD startup pages
```

Raw pages were re-extracted for this smoke test because `data/raw_pages.jsonl`
is a generated working file and may contain whichever slice was used last.

## Detector Result

Command:

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memmap_boot_smoke.jsonl \
  --page-ranges 90-126 \
  --min-score 0.5
```

Summary:

```text
scanned pages: 37
detected table-heavy pages: 23
detected address-map pages: 20
```

Detected page types:

| page_type | count |
| --- | ---: |
| address_map_table | 20 |
| generic_table | 3 |

Selected table pages:

```text
90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,121
```

Generic pages:

```text
112,113,114,115,116,117,118,119,120,122,123,124,125,126
```

Observation: the detector over-selected some pages after MEMMAP (`103-111`) and
one Boot/BMHD page (`121`) as table-heavy. This was not tuned in this slice; it
is a useful finding for the detector.

## Mixed Chunk Output

Command:

```bash
.venv/bin/python scripts/build_mixed_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_mixed_memmap_boot_smoke.jsonl \
  --doc-id memmap_boot_smoke \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_memmap_boot_smoke.jsonl \
  --min-table-score 0.5 \
  --section-title "Mixed MEMMAP / Boot Smoke Test" \
  --chunk-size 800 \
  --overlap 120 \
  --table-group-size 4 \
  --table-residual-chunk-size 300 \
  --table-residual-overlap 60
```

Chunk counts:

| chunk_type | count |
| --- | ---: |
| generic_page | 14 |
| generic_residual | 28 |
| table_row_group | 152 |

Total chunks:

```text
194
```

Pages covered:

```text
90-126
```

Acceptance condition was met:

```text
generic_page > 0
table_row_group > 0
generic_residual > 0
```

## Retrieval Results

### memory_map

Command:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_memmap_boot_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

Result:

```text
hit@1: 100%
hit@3: 100%
hit@5: 100%
```

The target was `hit@3 >= 80%` and `hit@5 >= 90%`, so the smoke corpus preserved
strong `memory_map` retrieval.

### Boot/BMHD

Command:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode hybrid \
  --eval eval/boot_bmhd_eval.json \
  --chunks data/chunks_mixed_memmap_boot_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8
```

Result:

```text
hit@1: 60%
hit@3: 90%
hit@5: 90%
```

Most Boot/BMHD questions retrieved expected pages in the 115-126 range. The one
failure was `boot-005`, the known weaker procedural question about SSW Boot Mode
Header processing.

## Analysis

Did the mixed builder produce all three chunk types?

```text
Yes: generic_page, table_row_group, generic_residual.
```

Which pages were selected as table pages?

```text
90-111 and 121.
```

Which pages became generic pages?

```text
112-120 and 122-126.
```

Did memory_map retrieval remain strong?

```text
Yes. bm25_table_boost improved to 100 / 100 / 100 on this smoke corpus.
```

Did Boot/BMHD retrieval still work on prose/semi-structured pages?

```text
Mostly yes. Hybrid retrieval reached 60 / 90 / 90, with one known procedural miss.
```

Did table detection over-select Boot/BMHD pages as tables?

```text
Yes, page 121 was selected as table-heavy. Pages 115-120 and 122-126 stayed generic.
```

Does the mixed approach look safe enough for a larger full-document smoke test?

```text
Yes as a lab workflow. The mixed builder behavior is correct. The detector needs
broader-range evaluation and over-selection analysis before production ingest.
```

## Limitations

- This smoke test does not tune detector precision.
- `data/raw_pages.jsonl`, candidate output, mixed chunks, and Chroma DB are
  generated artifacts and are not committed.
- The normal ingest pipeline remains unchanged.
- No model/API calls or answer evals were run.
- No parser migration, parent-child retrieval, or reranker was added.

## Recommendation

Next useful slice:

```text
Run a broader full-document or large-section mixed-corpus smoke test.
```

Focus on detector behavior:

```text
false positives
false negatives
chunk type distribution
retrieval stability across multiple eval slices
```

Do not wire mixed chunking into `ingest_document.py` until the broader detector
behavior is measured.
