# Memory Map Table-Aware Chunking Experiment (P3-2)

## Goal

Answer one focused question from the Phase 3 plan:

```text
Can table-aware row-group chunks improve retrieval for the memory_map slice
compared with generic 300/60 chunks?
```

This is a `memory_map`-only retrieval experiment. It does **not** change the
normal ingest pipeline (`scripts/chunk_pages.py`), does not call any model, and
does not run answer batch eval.

## Setup

| Item | Value |
| --- | --- |
| Slice | `memory_map` |
| Pages | 90-102 |
| Document | `docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf` |
| Eval file | `eval/memory_map_eval.json` (10 questions, page-level hit@k) |
| Embedding model | `BAAI/bge-small-en-v1.5` |
| Builder | `scripts/build_table_aware_chunks.py` |

Both chunk files are generated experiment artifacts under `data/` (gitignored,
not committed):

```text
baseline:    data/chunks_memory_map_baseline_300_60.jsonl   (generic 300/60)
table-aware: data/chunks_table_aware_memory_map.jsonl
```

The retrieval eval is page-level, so a fair comparison needs every expected page
represented. The builder therefore emits table-aware row-group chunks for the
address-map tables **and** generic token-window chunks (300/60) for non-table
text (prose, the Table 23 acronym list, footnotes).

```text
table_row_group chunks : 91  (298 parsed rows)
generic_residual chunks: 11
pages covered          : 90-102
segment markers        : accepted=31, skipped=0  (segment detection reliable)
```

### Reproduce

```bash
.venv/bin/python scripts/build_table_aware_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_table_aware_memory_map.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-102 \
  --section-title "Memory Maps (MEMMAP)" \
  --group-size 4 \
  --residual-chunk-size 300 \
  --residual-overlap 60

.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma --collection technical_docs --reset

for M in vector bm25 bm25_first_hybrid; do
  .venv/bin/python scripts/eval_retrieval.py --mode $M \
    --eval eval/memory_map_eval.json \
    --db vector_db/chroma --collection technical_docs \
    --chunks data/chunks_table_aware_memory_map.jsonl
done
```

Note: BM25 (`--chunks`) and the Chroma vector index must come from the same
chunk file, so always `embed_chunks.py --reset` the file you are about to
evaluate before running `bm25_first_hybrid`.

## Results

Baseline reproduced in-session and matched the documented Phase 2 numbers.

| Mode | hit@1 | hit@3 | hit@5 | | hit@1 | hit@3 | hit@5 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| | **baseline 300/60** | | | | **table-aware** | | |
| vector | 30% | 40% | 40% | | 40% | 70% | 80% |
| bm25 | 60% | 60% | 80% | | **80%** | **80%** | **100%** |
| bm25_first_hybrid | 60% | 60% | 80% | | **80%** | **80%** | **100%** |

Per-question (bm25), hit@3 PASS/FAIL:

| Question | Topic | Baseline | Table-aware |
| --- | --- | --- | --- |
| memory-map-001 | Table 23 acronyms | PASS | PASS |
| memory-map-002 | segment summary | PASS | PASS |
| memory-map-003 | CPU0 DSPR (p93) | FAIL | FAIL (now rank 4) |
| memory-map-004 | CPU0 PSPR (p94) | FAIL | FAIL (now rank 4) |
| memory-map-005 | PFLASH PF0-PF5 (p94) | FAIL | **PASS** |
| memory-map-006 | Boot ROM (p94) | FAIL | **PASS** |
| memory-map-007 | Data Flash / UCB / CFS | PASS | PASS |
| memory-map-008 | seg9 vs seg11 | PASS | PASS |
| memory-map-009 | TC39x alt SOTA seg8 | PASS | PASS |
| memory-map-010 | TC38x alt SOTA seg10 | PASS | PASS |

## Verdict

Table-aware row-group chunking **clearly improves** `memory_map` retrieval. Both
acceptance signals from the plan are met:

```text
target: hit@3 > 60%   -> achieved 80%
target: hit@5 >= 80%  -> achieved 100%
```

Of the three flagged hard questions:

- `memory-map-006` (Boot ROM): fixed (FAIL -> PASS).
- `memory-map-008` (seg9 vs seg11): still PASS.
- `memory-map-004` (CPU0 PSPR): still misses hit@3, but improved from "not in
  top-5" to rank 4 (now within hit@5).

## Remaining failures are not a table-parsing problem

`memory-map-003` and `memory-map-004` still miss hit@3, but the **correct table
chunk is retrieved at rank 4** in both cases. The top-3 slots are taken by
keyword-dense *prose residual* chunks that mention "address map", "segment", and
"PSPR/DSPR":

```text
rank 1: p90  "2.3 Functional Description ... address maps ... bus master ..."
rank 2: p102 "Segment 15 ... address map of segment F ..."
rank 3: p91  segment summary prose
rank 4: p93/p94  the actual CPU0 DSPR / CPU0 PSPR table row group   <-- correct
```

So the bottleneck for these two questions is **prose vs. table competition in
BM25 ranking**, not table extraction. The table content is parsed correctly and
is retrievable; it is just outranked by concept-dense prose.

## Notes / caveats

- This builder is a `memory_map`-specific heuristic, not a general table parser.
  Its assumptions (running boilerplate, `Table NN` title lines, the
  `Segm`/`ent`/... header block, multiline address rows) are tuned to the AURIX
  TC3xx MEMMAP pages and should not be assumed to hold on other documents.
- Row field separation is best-effort. Multiline cells (e.g. `Access2) /` +
  `SRIBE`, or a description split across two lines) are joined with `|`, so a few
  rows have slightly noisy column alignment. All tokens are preserved, which is
  what matters for retrieval.
- `current_segment` intentionally carries across pages so continuation tables
  (`... (cont’d)`) inherit the correct segment context. A new alternate-map table
  resets it via its own segment marker.
- Segment detection was reliable on this slice (31 accepted, 0 skipped) because
  every segment marker is immediately followed by an address range. The builder
  prints a warning if any marker is skipped, so this stays visible on other data.
- Vector mode also improved (hit@3 40% -> 70%) from the repeated table context,
  but it regressed `memory-map-001` (acronyms). BM25 / bm25_first_hybrid remain
  the recommended modes for this slice.

## Recommended next steps (not part of P3-2)

Based on the measured failure mode, the next experiments should target ranking,
not more table parsing:

1. Separate or down-weight prose residual chunks vs. table chunks (e.g. filter
   by `chunk_type`, or weighted fusion).
2. Parent-child retrieval: search the small table row group, return the page /
   table context.
3. Only after the above, consider PyMuPDF `find_tables()` or a reranker.

If integrating table-aware chunking more broadly, that belongs in a separate
slice (P3-3) focused on doing it without changing the normal ingest workflow.
