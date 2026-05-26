# P3-10 Task - Mixed Corpus Smoke Test on Prose + Table Pages

## Context

Phase 3 table retrieval work is summarized in:

```text
docs/PHASE3_TABLE_RETRIEVAL_SUMMARY.md
```

Current completed chain:

```text
P3-2  table-aware chunks
P3-3  table-aware ranking
P3-5  generalized table-aware builder
P3-6B answer path integration
P3-7  automatic table-heavy page detection
P3-8  detector-driven table chunking
P3-9  mixed chunk corpus builder
```

Known `memory_map` result:

```text
bm25:              80 / 80 / 100
bm25_table_boost:  80 / 100 / 100
```

P3-9 validated the mixed builder on `memory_map`, but that slice is almost
entirely table-heavy:

```text
mixed output for memory_map:
- table_row_group: 91
- generic_residual: 11
- generic_page: 0
```

This is acceptable for `memory_map`, but it does not yet prove mixed behavior on
a corpus that contains both prose pages and table pages.

## Goal

Run a smoke test on a mixed page range that contains both prose-like technical
documentation and table-heavy pages.

The goal is to prove that:

```text
detected table pages -> table_row_group + generic_residual chunks
non-table pages      -> generic_page chunks
```

This is a smoke test only.

Do not change the normal ingest pipeline.

## Suggested Mixed Page Range

Use a range that includes both:

```text
memory_map pages: 90-102
boot/BMHD-ish pages: 115-126
```

Suggested range:

```text
90-126
```

This should contain table-heavy MEMMAP pages and more prose/semi-structured
Boot/BMHD pages.

If this range is too broad or not available in current raw pages, use another
nearby mixed range and document why.

## Target Output

Create mixed chunks:

```text
data/chunks_mixed_memmap_boot_smoke.jsonl
```

Expected chunk types:

```text
table_row_group
generic_residual
generic_page
```

Key acceptance condition:

```text
generic_page count > 0
table_row_group count > 0
generic_residual count > 0
```

## Required Workflow

1. Ensure raw pages cover the mixed range

If current `data/raw_pages.jsonl` does not include pages 90-126, re-extract the needed range:

```bash
.venv/bin/python scripts/extract_pages.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-126 \
  --output data/raw_pages.jsonl
```

If the actual extract script uses different flags, inspect `scripts/extract_pages.py --help` and use the correct existing CLI.

2. Detect table-heavy pages

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memmap_boot_smoke.jsonl \
  --page-ranges 90-126 \
  --min-score 0.5
```

Record pages scanned, selected table pages, non-table pages, and detected page types.

3. Build mixed chunks

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

Record chunk counts: total chunks, generic_page, table_row_group, generic_residual, pages covered.

4. Embed mixed chunks

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_mixed_memmap_boot_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

5. Run retrieval evals

Run `memory_map` eval:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_memmap_boot_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

Run Boot/BMHD eval:

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

If `eval/boot_bmhd_eval.json` uses expected pages outside 115-126 or does not
match the selected range, document the mismatch and run only the subset that is
valid, or create a temporary smoke eval with 2-3 known questions. Do not
overbuild.

## Expected Results

For `memory_map`, result may differ slightly because the corpus now includes
more pages and more generic chunks.

Target:

```text
memory_map bm25_table_boost:
hit@3 >= 80%
hit@5 >= 90%
```

Ideal:

```text
80 / 100 / 100
```

For Boot/BMHD, target is not strict yet. This is a smoke test.

Expected signal:

```text
Boot/BMHD questions retrieve pages in the 115-126 range
generic_page chunks participate in retrieval
no obvious failure caused by table-aware chunking
```

## Important Analysis

In the report, answer these questions:

- Did the mixed builder produce all three chunk types?
- Which pages were selected as table pages?
- Which pages became generic pages?
- Did `memory_map` retrieval remain strong?
- Did Boot/BMHD retrieval still work on prose/semi-structured pages?
- Did table detection over-select Boot/BMHD pages as tables?
- Does the mixed approach look safe enough for a larger full-document smoke test?

## Documentation

Create:

```text
docs/MIXED_CORPUS_SMOKE_TEST.md
```

Include:

- tested page range
- detector result summary
- chunk type counts
- retrieval eval results
- observations
- limitations
- recommendation for next step

Clearly state:

```text
This is a smoke test for mixed chunk behavior. It does not replace the normal ingest pipeline yet.
```

## Non-goals

Do not:

- modify `scripts/chunk_pages.py`
- modify `scripts/ingest_document.py`
- modify `scripts/ask_chunks.py`
- change answer generation
- run model/API calls
- run answer eval
- add PyMuPDF `find_tables()`
- add Camelot / Unstructured / Docling
- add parent-child retrieval
- add reranker
- build production ingest
- commit generated JSONL chunks
- commit vector DB files

## Practical Constraints

- If pages 90-126 are not all available in `data/raw_pages.jsonl`, re-extract them.
- If the detector selects too many pages as table-heavy, do not tune endlessly. Document it.
- If Boot/BMHD eval is not valid for the selected mixed corpus, do not force it.
  Document the mismatch and run a small smoke query/eval instead.

## Verification

Run syntax checks:

```bash
.venv/bin/python -m py_compile \
  scripts/detect_table_pages.py \
  scripts/build_mixed_chunks.py \
  scripts/eval_retrieval.py
```

Run detector + mixed builder + embed + retrieval evals.

Check generated artifacts are ignored / not staged:

```bash
git check-ignore -v \
  data/table_page_candidates_memmap_boot_smoke.jsonl \
  data/chunks_mixed_memmap_boot_smoke.jsonl \
  vector_db/chroma
```

Run cleanup checks:

```bash
git diff --check
git status --short
```

## Commit

Stage only docs if no source changes are needed:

```bash
git add docs/MIXED_CORPUS_SMOKE_TEST.md
```

If a small bug fix is required in scripts, add only the relevant changed script:

```bash
git add scripts/build_mixed_chunks.py
git add scripts/detect_table_pages.py
```

Commit:

```bash
git commit -m "Run mixed corpus smoke test"
```

## Done Criteria

Done when:

- mixed smoke corpus was generated
- output contains `generic_page`, `table_row_group`, and `generic_residual`
- `memory_map` retrieval was checked
- prose/Boot-style retrieval was checked or a documented reason is given
- results are documented in `docs/MIXED_CORPUS_SMOKE_TEST.md`
- generated JSONL/vector DB files are not committed
- normal ingest and answer pipelines remain unchanged

## Scope Note

Do not tune the detector for a long time in this slice. If it over-selects pages,
that is a finding for the report. P3-10 is a smoke test, not final optimization.
