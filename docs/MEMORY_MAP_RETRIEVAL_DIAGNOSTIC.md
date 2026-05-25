# Memory Map Retrieval Diagnostic

## Slice Metadata

```text
slice id: memory_map
pdf: docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
page range: 90-102
eval file: eval/memory_map_eval.json
collection: technical_docs
questions: 10
```

This slice was chosen because it is dense with MEMMAP tables: segment descriptions,
address ranges, read/write access types, repeated Program Flash bank names, and alternate
SOTA mappings.

No answer-generation/model calls were made for this diagnostic.

## Retrieval Results

Commands rerun:

```bash
.venv/bin/python scripts/eval_retrieval.py --mode vector --eval eval/memory_map_eval.json --db vector_db/chroma --collection technical_docs
.venv/bin/python scripts/eval_retrieval.py --mode bm25 --eval eval/memory_map_eval.json --db vector_db/chroma --collection technical_docs
.venv/bin/python scripts/eval_retrieval.py --mode hybrid --eval eval/memory_map_eval.json --db vector_db/chroma --collection technical_docs --debug-failures
```

Results:

| Mode | hit@1 | hit@3 | hit@5 |
| --- | ---: | ---: | ---: |
| vector | 20% | 40% | 40% |
| BM25 | 40% | 60% | 70% |
| hybrid | 40% | 40% | 40% |

BM25 is the best current mode for this slice. Hybrid is worse than BM25 at hit@3/hit@5,
so the current RRF fusion is not helping table-heavy address-map retrieval.

## Chunk Inspection

Focused ingest produced:

```text
pages: 13
chunks: 23
chunking: page-local, 800 token size, 120 token overlap
```

Chunk distribution:

```text
90: 1 chunk
91: 1 chunk
92-101: mostly 2 chunks per page
102: 1 chunk
```

Important target text is present in extracted chunks:

- CPU0 DSPR is present on page 93, chunk 5.
- CPU0 PSPR and segment 8 PFLASH mapping are present on page 94, chunk 6.
- Data Flash 0 EEPROM/UCB/CFS and Data Flash 1 EEPROM are present on page 96, chunk 10.
- TC39x alternate SOTA segment 8 mapping is split across page 97 chunks, with the table
  header and first row separated from later rows.

This means the main failure is not simply "text missing from extraction." The harder
problem is retrieval ranking over flattened, repetitive table text.

## Failed Question Summary

Hybrid failed these questions at hit@3:

| Question | Expected | Hybrid top pages | Likely issue |
| --- | --- | --- | --- |
| `memory-map-003` CPU0 DSPR range/size | 93 | 102, 91, 90, 101, 100 | Generic table words dominate; CPU0 DSPR exact row is buried in a continuation chunk. |
| `memory-map-004` CPU0 PSPR range/size | 94 | 90, 102, 91, 101, 100 | Query asks for a precise row, but vector/BM25 favor section intro and similar table headings. |
| `memory-map-005` segment 8 PF0-PF5 ranges | 94 | 97, 90, 101, 100, 102 | Repeated PF0-PF5 rows across standard and alternate SOTA tables confuse the retriever. |
| `memory-map-006` Boot ROM range/access | 94 | 90, 91, 101, 102, 100 | Boot ROM is a single row inside a large table; query terms also occur in prose/introduction pages. |
| `memory-map-007` Data Flash/UCB/CFS ranges | 96 | 97, 91, 100, 101, 101 | BM25 finds this at rank 1, but vector ranking pulls unrelated alternate PFLASH pages upward in hybrid. |
| `memory-map-009` TC39x alternate SOTA segment 8 | 97 | 99, 98, 101, 100, 101 | Many device-family alternate maps have nearly identical text; TC39x segment 8 competes with TC3Ex/TC38x/TC37x pages. |

## Failure Categories

### 1. Numeric Address Lookup Is Weak For Vector Search

Hex address ranges such as `7000 0000H`, `7010 0000H`, `A000 0000H`, and `AF40 0000H`
carry the actual answer, but semantic embeddings do not rank them reliably. The vector
retriever often prefers nearby conceptual pages or similar table sections.

### 2. Repeated Similar Rows Confuse Ranking

The same terms repeat across many pages:

```text
Program Flash 0
Program Flash 1
PFLASH
Access
SRIBE
Reserved
Address Range
SOTA
```

For PFLASH/SOTA questions, pages 97-101 contain near-duplicate tables for different
device families and segments. Retrieval often lands on the right family of tables but the
wrong page.

### 3. Flattened Tables Lose Row/Header Structure

PyMuPDF text extraction keeps useful text, but table structure is flattened into long
streams. A row like:

```text
7010 0000H - 7010 FFFFH 64 Kbyte CPU0 PSPR Access Access
```

is retrievable textually, but the row/header relationship is not explicit. The retriever
cannot tell that `Address Range`, `Size`, `Description`, `Read`, and `Write` bind to the
same row.

### 4. Chunk Boundaries Split Important Table Context

Some pages split into two chunks. On page 97, the TC39x alternate SOTA table begins after
the standard segment table and is split so that the table title/header context is not
always adjacent to all rows. This hurts queries that depend on both the device family
name and the address rows.

### 5. Current Hybrid Fusion Can Degrade BM25

BM25 has better hit@3/hit@5 than hybrid on this slice:

```text
BM25:   hit@3 60%, hit@5 70%
hybrid: hit@3 40%, hit@5 40%
```

RRF gives vector-ranked near-duplicate table chunks enough influence to displace BM25
hits. The clearest example is `memory-map-007`: BM25 ranks page 96 first, but hybrid does
not place page 96 in the top 5.

### 6. Some Eval Questions Are Intentionally Broad

Questions like `memory-map-005` ask for all PF0-PF5 ranges in segment 8. The answer is a
multi-row table segment, not a single sentence. This is a good stress test, but it is also
harder than a narrow exact-address query.

## Recommended Next Experiments

Do these one at a time and rerun the same eval after each change.

1. BM25-first hybrid mode for table-heavy slices

   Add a mode or option that preserves BM25 top results before adding vector results. This
   is the highest-ROI next experiment because BM25 is already better for `memory_map`.

2. Smaller chunk-size experiment

   Try 300-500 token chunks with overlap and compare `memory_map` hit@k. The goal is to
   avoid huge table chunks where many unrelated rows compete inside one embedding.

3. Table-aware chunking by row groups

   Preserve table title/header and chunk rows into smaller groups. Each chunk should keep
   the table name, device family, segment number, and column labels.

4. Query normalization for hex addresses and table terms

   Normalize address forms like `A000 0000H`, `A000_0000H`, and `A0000000H`; preserve or
   expand terms like `PF0`, `Program Flash 0`, `PFLASH`, `UCB`, and `CFS`.

5. Reranker experiment

   Retrieve top 20-50 with BM25/vector/hybrid, then rerank with a cross-encoder. This may
   help when the right page appears in candidate sets but not near the top.

6. Parent-child retrieval

   Search smaller child chunks but return the parent page or table context. This is likely
   useful for answers that need surrounding table headers and multiple rows.

## Current Conclusion

`memory_map` is doing its job as a stress fixture. It shows that the current pipeline can
extract the relevant table text, but retrieval ranking is not robust for dense numeric
tables. The next retrieval work should start with BM25-first or BM25-weighted hybrid
before changing multiple parts of the pipeline.
