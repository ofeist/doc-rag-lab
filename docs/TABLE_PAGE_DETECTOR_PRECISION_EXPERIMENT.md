# Table Page Detector Precision Experiment (P3-11)

## Problem

P3-10 showed that the detector had good recall on the `90-126` mixed smoke
range, but it over-selected some pages for table-aware row-group chunking.

The original finding was:

```text
range: 90-126
detector candidates: 23
selected table pages: 90-111, 121
```

The suspected over-selection pages were:

```text
103-111
121
```

The goal of P3-11 was not to build a perfect classifier. The goal was a small,
explainable precision improvement without losing recall on important memory-map
pages:

```text
93, 94, 96, 97, 100
```

## Before Tuning

Detector output before tuning:

```text
scanned pages: 37
candidates emitted: 23
address_map_table: 20
generic_table: 3
recommended table_row_group pages:
90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,121
```

Inspection showed:

| Pages | Classification | Verdict |
| --- | --- | --- |
| 103-110 | `address_map_table` | Keep selected. They contain real Segment F address-map rows with many split hex address ranges. |
| 111 | `generic_table` | Do not send to row-group parser. It contains revision/history memory capability tables, not address-map row groups. |
| 121 | `generic_table` | Do not send to row-group parser. It contains Boot/ABM tables, but not address-map row groups. |

Representative signals:

```text
page 103: starts=13 ends=13 type=address_map_table
page 104: starts=35 ends=35 type=address_map_table
page 110: starts=14 ends=14 type=address_map_table
page 111: starts=0  ends=0  type=generic_table
page 121: starts=0  ends=0  type=generic_table
```

The issue was not that all suspected pages were false positives. The issue was
that `generic_table` pages were recommended for the address-map row-group
chunker.

## Heuristic Change

The detector now recommends table-aware row-group chunking only for:

```text
page_type == address_map_table
```

Before:

```text
address_map_table -> table_row_group
generic_table     -> table_row_group
```

After:

```text
address_map_table -> table_row_group
generic_table     -> generic
```

This preserves candidate reporting for generic tables while preventing those
pages from being routed into the address-map row parser.

No page-number-specific exclusions were added.

## After Tuning

Detector output after tuning:

```text
scanned pages: 37
candidates emitted: 23
address_map_table -> table_row_group: 20
generic_table -> generic: 3
recommended table_row_group pages:
91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110
```

Important memory-map pages remained selected:

```text
93, 94, 96, 97, 100
```

Reduced row-group over-selection:

```text
90, 111, 121 no longer route to table_row_group
```

Page 90 remains useful, but as a generic page. It contains Table 23 acronyms and
segment prose, not dense address-map rows.

## Mixed Chunk Impact

Before P3-11, P3-10 mixed smoke output was:

| chunk_type | count |
| --- | ---: |
| generic_page | 14 |
| generic_residual | 28 |
| table_row_group | 152 |
| total | 194 |

After P3-11:

| chunk_type | count |
| --- | ---: |
| generic_page | 17 |
| generic_residual | 21 |
| table_row_group | 152 |
| total | 190 |

Interpretation:

```text
row-group rows were preserved for true address-map pages
generic table/prose pages moved out of the table parser
```

## Retrieval Impact

### memory_map

Before P3-11:

```text
bm25_table_boost: 100 / 100 / 100
```

After P3-11:

```text
bm25_table_boost: 100 / 100 / 100
```

Memory-map retrieval stayed strong.

### Boot/BMHD

Before P3-11:

```text
hybrid: 60 / 90 / 90
```

After P3-11:

```text
hybrid: 70 / 90 / 100
```

Boot/BMHD did not materially regress. `boot-005` still failed, but that was
already the known weaker procedural query.

## Verdict

Accept the precision change.

It improves routing precision without losing the important memory-map pages and
without hurting the smoke retrieval checks.

This is still not a final table classifier. It is a conservative rule that keeps
generic tables visible as candidates while preventing them from being parsed as
address-map row groups.

## Next Recommendation

Proceed to a broader full-document or large-section mixed ingest smoke test.

The next validation should measure:

```text
false positives across many sections
false negatives for register/address-map tables
chunk type distribution
retrieval stability across memory_map, boot_bmhd, dma_cache, interrupt_routing
```

Do not wire this into the normal ingest pipeline until broader detector behavior
is measured.
