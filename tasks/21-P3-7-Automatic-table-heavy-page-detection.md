# P3-7 Task - Automatic Table-Heavy Page Detection

## Context

We completed the table-aware retrieval proof chain:

```text
P3-2: table-aware row-group chunks improved memory_map retrieval
P3-3: bm25_table_boost improved table-heavy ranking
P3-5: table-aware chunk builder was generalized
P3-6B: answer path now supports bm25_table_boost
```

Known result on `memory_map`:

```text
generic 300/60 baseline:        60 / 60 / 80
table-aware chunks:             80 / 80 / 100
table-aware chunks + ranking:   80 / 100 / 100
```

Remaining major limitation:

```text
We still manually provide --page-ranges 90-102.
```

That is not acceptable for large technical manuals with hundreds or thousands of pages.

## Goal

Create an automatic page detector that identifies likely table-heavy pages from extracted page text.

New script:

```text
scripts/detect_table_pages.py
```

The detector should read `data/raw_pages.jsonl` and output a JSONL report with per-page table signals.

This is a detection experiment only.

Do not change the normal ingest pipeline.
Do not change chunking or answer generation.

## Target Use Case

Given a large extracted PDF:

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates.jsonl
```

The script should identify pages likely suitable for table-aware chunking.

For the current AURIX manual slice, pages 90-102 should be detected as table-heavy / address-map-like.

## Required Output

Write JSONL records like:

```json
{
  "page": 94,
  "table_likelihood": 0.93,
  "page_type": "address_map_table",
  "recommended_chunker": "table_row_group",
  "signals": {
    "table_title_count": 1,
    "address_start_count": 18,
    "address_end_count": 18,
    "hex_token_count": 52,
    "access_keyword_count": 24,
    "column_header_hits": ["Address Range", "Size", "Description", "Read", "Write"]
  },
  "reasons": [
    "contains table title",
    "contains many split hex address ranges",
    "contains access/read/write column headers"
  ]
}
```

Minimum required fields:

```text
page
table_likelihood
page_type
recommended_chunker
signals
reasons
```

## Detection Rules

Start with simple heuristics. Do not use ML.

Detect signals such as:

1. Table title signal

Lines matching:

```text
^Table\s+\d+
```

or text containing:

```text
Table 24
Table 25
Address Map
Register
```

2. Address-map row signal

The memory-map extraction pattern is multiline:

```text
8000 0000H
- 802F FFFFH
3 Mbyte
Program Flash 0 (PF0)
Access
SRIBE
```

Detect:

```text
^[0-9A-F]{4} [0-9A-F]{4}H$
^- [0-9A-F]{4} [0-9A-F]{4}H$
```

Count both start and end address lines.

3. Hex density signal

Count tokens matching:

```text
[0-9A-F]{2,8}H
```

or address-like tokens.

4. Table header signal

Look for header words:

```text
Address Range
Size
Description
Access Type
Read
Write
Bit
Field
Reset
```

5. Access keyword signal

Look for technical table values:

```text
Access
Reserved
BBBBE
SPBBE
SRIBE
PFLASH
DSPR
PSPR
LMURAM
DLMU
Boot ROM
```

## Page Type Classification

Use simple rule-based classification.

Suggested values:

```text
address_map_table
register_table
generic_table
prose
unknown
```

For now, it is enough to reliably detect:

```text
address_map_table
generic_table
prose
unknown
```

Do not overbuild register-table detection yet.

## Scoring

Create a simple score from `0.0` to `1.0`.

Example heuristic:

```text
score starts at 0.0

+0.20 if table title exists
+0.25 if address_start_count >= 3 and address_end_count >= 3
+0.20 if address_start_count >= 10
+0.15 if at least 3 column header terms exist
+0.10 if access_keyword_count >= 5
+0.10 if hex_token_count >= 10

cap at 1.0
```

This exact scoring can be adjusted, but keep it simple and documented.

## CLI Options

Support:

```text
--input
--output
--min-score
--page-ranges
```

Defaults:

```text
--input data/raw_pages.jsonl
--output data/table_page_candidates.jsonl
--min-score 0.5
```

`--page-ranges` is optional and should support at least:

```text
90-102
```

Nice-to-have:

```text
90-94,96,100-102
```

## Console Summary

Print a readable summary:

```text
Scanned pages: 13
Detected table-heavy pages: 11
Detected address-map pages: 10
Output: data/table_page_candidates.jsonl

Top candidates:
page 94 score=0.93 type=address_map_table reasons=...
page 96 score=0.91 type=address_map_table reasons=...
...
```

## Validation

Run detection on the current `memory_map` raw pages:

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memory_map.jsonl \
  --page-ranges 90-102 \
  --min-score 0.5
```

Expected:

- pages 90-102 should mostly be detected as table-heavy
- pages with address-map tables should be classified as `address_map_table`
- page 90 may be `generic_table` or prose+table depending on detected signals

Important target:

```text
pages 93 and 94 must be detected
pages 96, 97, 100 should be detected
```

These pages are important because they supported prior `memory_map` questions.

## Optional Broader Smoke Test

If `data/raw_pages.jsonl` currently contains a full document, run without `--page-ranges`:

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_full.jsonl \
  --min-score 0.5
```

Do not require this if the current raw pages file only contains a slice.

## Report

Create:

```text
docs/TABLE_PAGE_DETECTION_EXPERIMENT.md
```

Include:

- why automatic page detection is needed
- detection rules
- output schema
- validation result on memory_map pages
- false positive / false negative observations
- how this will feed the next step

The report should clearly say:

```text
This detects candidate pages only. It does not yet modify ingestion automatically.
```

## Non-goals

Do not:

- change `scripts/chunk_pages.py`
- change `scripts/ingest_document.py`
- change `scripts/build_table_aware_chunks.py`
- change answer generation
- add ML classifiers
- add PyMuPDF `find_tables()`
- add Camelot / Unstructured / Docling
- run model/API calls
- run answer eval
- commit generated JSONL outputs
- commit vector DB files

## Verification

Run:

```bash
.venv/bin/python -m py_compile scripts/detect_table_pages.py
```

Run detector:

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memory_map.jsonl \
  --page-ranges 90-102 \
  --min-score 0.5
```

Inspect output:

```bash
head -n 5 data/table_page_candidates_memory_map.jsonl
```

Check important pages:

```bash
grep '"page": 94' data/table_page_candidates_memory_map.jsonl
grep '"page": 96' data/table_page_candidates_memory_map.jsonl
grep '"page": 100' data/table_page_candidates_memory_map.jsonl
```

Run cleanup checks:

```bash
git diff --check
git status --short
```

Confirm generated output is not staged:

```bash
git check-ignore -v data/table_page_candidates_memory_map.jsonl
```

## Commit

Stage only source/docs:

```bash
git add scripts/detect_table_pages.py \
        docs/TABLE_PAGE_DETECTION_EXPERIMENT.md
```

Commit:

```bash
git commit -m "Add automatic table-heavy page detection experiment"
```

## Done Criteria

Done when:

- `scripts/detect_table_pages.py` exists
- it reads raw page JSONL
- it emits per-page table candidate JSONL
- it assigns a table likelihood score
- it classifies likely address-map pages
- memory_map pages 93, 94, 96, 97, and 100 are detected
- docs explain the detection strategy and limitations
- generated JSONL files are not committed
- normal ingest and answer pipelines remain unchanged

## Scope Note

Do not connect this to `scripts/build_table_aware_chunks.py` yet. P3-7 is only
the detector. The next slice should be "detector output -> table-aware chunk
builder input".
