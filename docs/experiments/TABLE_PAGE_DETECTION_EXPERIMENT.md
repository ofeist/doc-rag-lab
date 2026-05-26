# Table Page Detection Experiment (P3-7)

## Purpose

P3-2 through P3-6B proved that table-aware chunks and `bm25_table_boost` improve
dense table retrieval when the relevant pages are known.

The remaining scaling problem is page selection:

```text
manual --page-ranges 90-102 does not scale to large technical manuals
```

This experiment adds a local heuristic detector that identifies candidate
table-heavy pages from extracted page text.

This detects candidate pages only. It does not yet modify ingestion
automatically.

## Script

```text
scripts/detect_table_pages.py
```

Example:

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates.jsonl \
  --min-score 0.5
```

Focused validation:

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memory_map.jsonl \
  --page-ranges 90-102 \
  --min-score 0.5
```

## Output Schema

Each JSONL record is a candidate page:

```text
page
table_likelihood
page_type
recommended_chunker
signals
reasons
```

Example:

```json
{
  "page": 94,
  "table_likelihood": 1.0,
  "page_type": "address_map_table",
  "recommended_chunker": "table_row_group",
  "signals": {
    "table_title_count": 1,
    "address_start_count": 34,
    "address_end_count": 34,
    "hex_token_count": 68,
    "access_keyword_count": 95,
    "column_header_hits": ["Address Range", "Size", "Description", "Access Type", "Read", "Write"]
  },
  "reasons": [
    "contains table title or table-like title terms",
    "contains multiple split hex address ranges",
    "contains dense address-map rows",
    "contains table column header terms",
    "contains repeated access/table values",
    "contains high hex-token density"
  ]
}
```

## Detection Rules

The detector is intentionally simple and local. It uses no ML model and no PDF
table parser.

Signals:

- table title lines such as `Table 24`
- table-like title terms such as `Address Map` and `Register`
- split address ranges such as `8000 0000H` followed by `- 802F FFFFH`
- hex-token density
- column header terms such as `Address Range`, `Size`, `Description`, `Read`,
  and `Write`
- table value terms such as `Access`, `Reserved`, `SRIBE`, `PFLASH`, `DSPR`,
  `PSPR`, `LMURAM`, `DLMU`, and `Boot ROM`

Scoring:

```text
+0.20 table title or table-like title terms
+0.10 multiple table references on the same page
+0.25 at least 3 split address starts and ends
+0.20 at least 10 address starts
+0.15 at least 3 column header terms
+0.10 at least 5 access/table value terms
+0.10 at least 10 hex tokens
cap at 1.0
```

Classification:

```text
address_map_table
generic_table
prose
unknown
```

The only classification currently tuned with evidence is `address_map_table`.
Register-table detection is intentionally left for later.

## Validation Result

The current validation used extracted AURIX `memory_map` pages:

```text
page range: 90-102
min score: 0.5
scanned pages: 13
detected table-heavy pages: 13
detected address-map pages: 12
```

Important target pages were detected:

| Page | Result | Notes |
| --- | --- | --- |
| 90 | detected | `generic_table`, score 0.55 |
| 93 | detected | `address_map_table`, score 1.0 |
| 94 | detected | `address_map_table`, score 1.0 |
| 96 | detected | `address_map_table`, score 1.0 |
| 97 | detected | `address_map_table`, score 1.0 |
| 100 | detected | `address_map_table`, score 1.0 |

Page 90 is emitted as `generic_table`, not `address_map_table`. This is useful
because it contains Table 23 acronym definitions and segment summary context
used by the `memory_map` eval, even though it is not a dense address-map page.

## Observations

False negatives:

- No false negatives were observed for the current `memory_map` eval target
  pages at `--min-score 0.5`.

False positives:

- Within the focused 90-102 validation range, pages 90-102 are all plausible
  table-heavy candidates because they contain address map setup text, table
  headers, dense address rows, or continuation tables.
- Broader-document false positive behavior is not measured yet.

## Next Step

P3-8 should connect detector output to a mixed ingest experiment:

```text
normal prose chunks + table-aware chunks for detected candidate pages
```

Do not wire this detector directly into the normal ingest pipeline until the
mixed ingest experiment has a measured retrieval result.

## Non-Goals

- No changes to `scripts/chunk_pages.py`
- No changes to `scripts/ingest_document.py`
- No changes to `scripts/build_table_aware_chunks.py`
- No answer generation changes
- No ML classifier
- No PyMuPDF `find_tables()`
- No Camelot / Unstructured / Docling
