# Table-Aware Row-Group Chunking Plan

## Context

Phase 2 of the RAG lab showed that the current pipeline works reasonably well for prose and semi-structured technical documentation, but struggles with dense technical tables.

The strongest stress case so far is the `memory_map` slice:

```text
slice id: memory_map
page range: 90-102
eval file: eval/memory_map_eval.json
document: docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
```

Current best known settings for this slice:

```text
chunking: 300 tokens / 60 token overlap
retrieval mode: BM25 or bm25_first_hybrid
top_k for answer eval: 5
```

Observed answer grading for the `memory_map` stress eval:

```text
PASS:    6
PARTIAL: 2
FAIL:    2
TOTAL:   10
```

The main conclusion is that the model can often answer correctly when the right table chunk appears in the context. The bigger weakness is retrieval and context construction for dense tables.

---

## 1. Problem

Current chunking treats table-heavy pages mostly like normal text. This is weak for memory maps, register summaries, bit-field tables, and address-map tables.

The main problems are:

1. **Flattened table layout**

   PDF extraction turns rows and columns into plain text streams. The row/header relationship is not explicit anymore.

2. **Headers are not repeated near every row**

   A table row may contain only values such as:

   ```text
   7010 0000H - 7010 FFFFH 64 Kbyte CPU0 PSPR Access Access
   ```

   Without repeated table context, the retriever may not know that this belongs to:

   ```text
   Table 24 — Address Map of Segments 0 to 14
   Columns: Address Range | Size | Description | Read | Write
   ```

3. **Hex addresses are poor semantic signals**

   Values such as `7000 0000H`, `AF40 0000H`, or `A0BF FFFFH` are crucial for the answer, but embedding models do not reliably rank them semantically.

4. **Repeated similar rows confuse retrieval**

   Many pages contain similar repeated terms:

   ```text
   Program Flash 0
   Program Flash 1
   PFLASH
   Reserved
   Access
   BBBBE
   SOTA
   Address Range
   ```

   This causes confusion between standard maps and alternate SOTA maps, or between different device-family tables.

5. **Correct chunks may appear too low**

   In the `memory_map` eval, some answers only succeeded because the correct source appeared at rank 5. This means `top_k=3` is too risky for dense tables.

6. **Multi-row questions need better context packing**

   Questions like “Program Flash 0 through Program Flash 5” require multiple related rows, not just one isolated line.

---

## 2. Proposed Experiment

The next experiment should test table-aware row-group chunking on the `memory_map` slice only.

Scope:

```text
pages: 90-102
slice: memory_map
input document: AURIX TC3xx Part 1 user manual
```

This is not a production parser and not a full corpus migration. It is a focused retrieval experiment.

The goal is to create alternative chunks for table-heavy pages that preserve table context, column headers, and row groups.

Suggested generated output:

```text
data/chunks_table_aware_memory_map.jsonl
```

This file should be treated as a generated experiment artifact and should not be committed.

---

## 3. Target Chunk Shape

A table-aware row-group chunk should include enough metadata and repeated context to make each group independently retrievable.

Target fields:

```json
{
  "doc_id": "memory_map",
  "source": "docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf",
  "page_start": 94,
  "page_end": 94,
  "chunk_type": "table_row_group",
  "section_title": "Memory Maps (MEMMAP)",
  "table_title": "Table 24 Address Map of Segments 0 to 14",
  "table_context": "Segment 8",
  "column_headers": ["Address Range", "Size", "Description", "Read", "Write"],
  "row_count": 3,
  "text": "Table 24 Address Map of Segments 0 to 14\nSegment 8\nColumns: Address Range | Size | Description | Read | Write\n8000 0000H - 802F FFFFH | 3 Mbyte | Program Flash 0 | Access | BBBBE\n8030 0000H - 805F FFFFH | 3 Mbyte | Program Flash 1 | Access | BBBBE\n8060 0000H - 808F FFFFH | 3 Mbyte | Program Flash 2 | Access | BBBBE"
}
```

The most important field is `text`, because the current retrievers operate over text. The metadata fields are useful for debugging, filtering, and later parent-child retrieval.

---

## 4. Chunking Strategy

The experiment should create chunks around small groups of table rows rather than generic token windows.

Recommended row-group size:

```text
1-5 rows per chunk
```

Each chunk should repeat:

```text
section title
table title
table context / segment / device family
column headers
row group
```

Example text chunk:

```text
Memory Maps (MEMMAP)
Table 24 — Address Map of Segments 0 to 14
Context: Segment 8
Columns: Address Range | Size | Description | Read | Write

8000 0000H - 802F FFFFH | 3 Mbyte | Program Flash 0 | Access | BBBBE
8030 0000H - 805F FFFFH | 3 Mbyte | Program Flash 1 | Access | BBBBE
8060 0000H - 808F FFFFH | 3 Mbyte | Program Flash 2 | Access | BBBBE
```

For continuation tables, every chunk should still include the table title and relevant context. Do not rely on previous chunks to provide meaning.

---

## 5. Implementation Options

### Option A — Heuristic from Existing Extracted Text

Use the current PyMuPDF text extraction output, for example `data/raw_pages.jsonl`, and build table-aware chunks heuristically.

Possible approach:

1. Read only pages `90-102`.
2. Detect known table titles such as:

   ```text
   Table 24
   Table 25
   Address Map
   Alternate Address Map
   Segment 8
   Segment 10
   ```

3. Detect rows containing address ranges, for example with regex patterns like:

   ```text
   [0-9A-F]{4} [0-9A-F]{4}H - [0-9A-F]{4} [0-9A-F]{4}H
   ```

4. Group nearby rows into chunks.
5. Repeat table title, context, and column headers in every chunk.

Pros:

- Fastest path.
- No new dependencies.
- Uses the current pipeline.
- Good enough for a focused experiment.

Cons:

- Brittle.
- May miss rows if PDF extraction changes formatting.
- Not a general table parser.
- Needs manual validation.

### Option B — PyMuPDF Table Detection

Use PyMuPDF table detection on pages `90-102` and inspect whether it can extract rows/columns better than plain text.

Possible approach:

1. Run PyMuPDF table detection on pages `90-102`.
2. Print or export detected tables.
3. Compare extracted rows against the manual table content needed for `memory_map_eval.json`.
4. If good enough, generate table-aware row-group chunks from detected tables.

Pros:

- May preserve rows and columns better than plain text extraction.
- Still uses an already-present library.
- Could become reusable later.

Cons:

- May fail on complex technical manual tables.
- Needs validation against real pages.
- May not preserve table titles or section context automatically.
- Could take longer than a simple heuristic.

### Recommendation

Start with the smallest useful experiment.

Recommended order:

```text
1. Inspect PyMuPDF table detection quickly on pages 90-102.
2. If table detection is usable, use it.
3. If table detection is poor or slow to adapt, use a focused heuristic for memory_map only.
```

Do not build a general table parser in the first implementation slice.

---

## 6. Evaluation Plan

Use the existing eval file:

```text
eval/memory_map_eval.json
```

Compare current best against the new table-aware chunks.

Current best baseline:

```text
chunks: 300/60 generic chunks
mode: BM25 or bm25_first_hybrid
hit@1: 60%
hit@3: 60%
hit@5: 80%
```

New experiment:

```text
chunks: table-aware row-group chunks
mode: BM25 and/or bm25_first_hybrid
same eval: eval/memory_map_eval.json
```

Metrics:

```text
hit@1
hit@3
hit@5
failed question IDs
which source pages/chunks were retrieved
```

Primary success target:

```text
Improve hit@3 above 60%.
```

Secondary success target:

```text
Preserve or improve hit@5 above 80%.
```

Important questions to improve:

```text
memory-map-004  CPU0 PSPR address range and size
memory-map-006  Boot ROM address range and access types
memory-map-008  Segment 9 vs segment 11 comparison
```

Do not run answer batch eval until retrieval improves or at least changes in an informative way.

---

## 7. Expected Failure Modes

The experiment may fail. Useful failure modes include:

1. **No better retrieval**

   Table-aware chunks may not improve hit@k if rows are still not detected well.

2. **Too many small chunks**

   Row-level chunks may improve exact lookup but hurt multi-row questions.

3. **Lost context**

   If table title, segment, or device-family context is missing, chunks become ambiguous.

4. **Parsing noise**

   Heuristics may accidentally merge unrelated rows or split one logical row into broken pieces.

5. **BM25 overfits exact words**

   BM25 may rank chunks with repeated terms but wrong table context.

All of these are acceptable outcomes as long as the result is measured and documented.

---

## 8. Non-Goals

Do not do these in P3-1/P3-2:

- no answer batch eval
- no live model/API calls
- no full production table parser
- no full-document corpus migration
- no parent-child retrieval yet
- no reranker yet
- no UI work
- no automated grading
- no broad parser benchmark
- no changes to the normal ingest workflow unless the experiment clearly justifies it

---

## 9. Recommended Next Implementation Slice

The next implementation slice should be:

```text
P3-2 — Prototype memory_map table-aware chunks
```

Suggested script:

```text
scripts/build_memory_map_table_chunks.py
```

Scope:

```text
input: pages 90-102 / existing extracted text or PDF pages
output: data/chunks_table_aware_memory_map.jsonl
no changes to normal ingest pipeline
no model calls
```

The script should:

1. Read the focused `memory_map` extracted pages or PDF pages.
2. Produce experimental table-aware row-group chunks.
3. Preserve page metadata.
4. Repeat table title/context/headers in each chunk.
5. Write JSONL chunks compatible with the existing embedding/retrieval path if practical.

Evaluation for P3-2:

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset

.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25 \
  --eval eval/memory_map_eval.json \
  --db vector_db/chroma \
  --collection technical_docs \
  --chunks data/chunks_table_aware_memory_map.jsonl
```

Also test:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_first_hybrid \
  --eval eval/memory_map_eval.json \
  --db vector_db/chroma \
  --collection technical_docs \
  --chunks data/chunks_table_aware_memory_map.jsonl
```

Expected comparison:

```text
current best generic chunks: hit@1 60%, hit@3 60%, hit@5 80%
table-aware chunks: compare honestly against this baseline
```

---

## 10. Decision Rule

After P3-2, decide based on measured results.

If table-aware row-group chunks improve hit@3 or fix key failed questions:

```text
Continue toward a reusable table-aware chunking mode.
```

If they do not improve retrieval:

```text
Do not over-invest in custom heuristics.
Try PyMuPDF table extraction, parent-child retrieval, or reranking next.
```

If PyMuPDF table extraction is clearly superior:

```text
Plan a parser comparison slice before integrating it into the main pipeline.
```

---

## 11. Summary

The goal is not to build a perfect table parser immediately.

The goal is to answer one focused question:

```text
Can table-aware row-group chunks improve retrieval for memory_map compared with generic 300/60 chunks?
```

This keeps P3 small, measurable, and aligned with the existing RAG lab methodology.
