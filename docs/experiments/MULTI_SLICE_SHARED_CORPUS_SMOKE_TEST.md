# Multi-Slice Shared Corpus Smoke Test (P3-13)

This is a multi-slice shared-corpus smoke test. It does not replace the normal
ingest pipeline. All table-specific work remains experimental and explicit.

## Goal

Earlier mixed smoke tests (P3-10, P3-12) each covered one contiguous section. This
test builds ONE mixed chunk corpus containing all four known eval slice ranges at
once, then runs all four retrieval evals against that single shared corpus, to
check whether combining table and prose slices causes cross-slice interference.

## Setup

Slice ranges and the union used for extraction:

```text
memory_map:        90-126
boot_bmhd:         115-126
dma_cache:         257-259,307-314,1435-1455,1483-1488
interrupt_routing: 1364-1397

union (extracted): 90-126,257-259,307-314,1364-1397,1435-1455,1483-1488
```

Pipeline (detector-driven mixed chunking, unchanged tools):

```text
extract_pages -> detect_table_pages -> build_mixed_chunks -> embed -> eval_retrieval
```

Generated artifacts (gitignored, not committed):

```text
data/raw_pages_multi_slice.jsonl
data/table_page_candidates_multi_slice.jsonl
data/chunks_mixed_multi_slice.jsonl
vector_db/chroma
```

Build parameters: `--chunk-size 800 --overlap 120 --table-group-size 4
--table-residual-chunk-size 300 --table-residual-overlap 60 --min-table-score 0.5`,
`--section-title "Multi-Slice Shared Corpus Smoke Test"`.

## Detector behavior

```text
pages scanned        : 109
table candidates      : 24
  address_map_table  : 20   -> table_row_group
  generic_table      : 4    -> generic
```

- `address_map_table -> table_row_group`: pages 91-110 (the memory_map address-map
  region).
- `generic_table -> generic`: pages 90, 111, 121, 1393. These are detected as
  table-like but lack address-pair rows, so the P3-11 precision rule keeps them on
  the generic path. This is the intended behavior, not a miss.
- The dma_cache (257-259, 307-314, 1435-1455, 1483-1488) and interrupt_routing
  (1364-1397) sections were not selected as address-map tables and are chunked
  generically, which matches how those slices are evaluated (hybrid).

No obvious prose page was routed into the row-group parser, and no obvious
address-map page was missed within the memory_map region.

## Chunk type distribution

```text
total chunks      : 269
generic_page      : 96
table_row_group   : 152   (527 rows)
generic_residual  : 21
segment markers   : accepted=31, skipped=0
```

`generic_page > 0`, `table_row_group > 0`, `generic_residual > 0` — all satisfied.

All four expected page sets are present in the shared corpus:

```text
memory_map        present
boot_bmhd         present
dma_cache         present
interrupt_routing present
```

## Retrieval results (single shared corpus)

| Slice | Mode | hit@1 | hit@3 | hit@5 | Standalone ref (hit@3/@5) |
| --- | --- | ---: | ---: | ---: | --- |
| memory_map | bm25_table_boost | 100% | 100% | 100% | 100 / 100 |
| boot_bmhd | hybrid | 70% | 100% | 100% | 80-90 / 90-100 |
| dma_cache | hybrid | 100% | 100% | 100% | 100 / 100 |
| interrupt_routing | hybrid | 80% | 100% | 100% | 100 / 100 |

Every slice reaches hit@3 = 100% and hit@5 = 100% from the shared corpus.

## Analysis

- **Did any slice regress vs. its standalone baseline?** No. Each slice is at or
  above its known standalone hit@3 / hit@5. boot_bmhd is actually stronger here
  (hit@3 100%).
- **Cross-slice interference?** No evidence. The slices occupy disjoint page
  ranges and distinct vocabularies (address maps vs. boot flow vs. DMA/cache vs.
  interrupt routing), so retrieval for one slice is not pulled toward another. The
  `bm25_table_boost` mode only lifts `table_row_group` chunks, which exist only in
  the memory_map region, so it does not distort the prose slices.
- **Detector over/under-selection?** Precision held: only true address-map pages
  became `table_row_group`; `generic_table` pages stayed generic.
- **Ready for a full-document smoke test?** Yes for retrieval mechanics. The mixed
  pipeline handled a sparse, multi-section page set (109 pages spread across
  90-1488) and kept all four slices strong. A full-document run would mainly stress
  detector precision/recall and artifact size, not the retrieval path tested here.

## Conclusion

One shared mixed corpus serves all four eval slices without regression or
cross-slice interference. The detector-driven mixed chunking pipeline is stable
across very different document sections.

This remains a smoke test. The normal ingest and answer pipelines are still not
replaced, retrieval mode selection is still manual, and no generated artifacts are
committed.
