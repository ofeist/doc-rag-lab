# P3-9 Task - Mixed Chunk Corpus Experiment

## Context

P3-8 connected automatic table-page detection to the table-aware chunk builder.

Current chain:

```text
detect_table_pages.py
-> table_page_candidates.jsonl
-> build_table_aware_chunks.py --table-candidates
-> table-aware chunks
-> bm25_table_boost retrieval
```

Known `memory_map` result:

```text
bm25:              80 / 80 / 100
bm25_table_boost:  80 / 100 / 100
```

Current limitation:

```text
We still produce either normal chunks OR table-aware chunks.
```

For real technical manuals, we need one mixed corpus:

```text
normal/prose pages      -> generic chunks
detected table pages    -> table-aware row-group chunks + residual chunks
```

P3-9 is an experiment to produce such a combined chunk JSONL.

Do not change the normal ingest pipeline yet.

## Goal

Create an experimental mixed chunk builder that combines:

```text
normal page-aware chunks for non-table pages
table-aware chunks for detected table pages
```

New script:

```text
scripts/build_mixed_chunks.py
```

Output example:

```text
data/chunks_mixed_memory_map.jsonl
```

This is still experimental.

## Target Behavior

Given:

```text
data/raw_pages.jsonl
data/table_page_candidates_memory_map.jsonl
```

produce one combined JSONL file containing:

```text
chunk_type == generic_page
chunk_type == table_row_group
chunk_type == generic_residual
```

Where:

```text
generic_page        = normal token-window chunk from non-table pages
table_row_group     = table-aware table row groups from detected table pages
generic_residual    = non-table text from detected table pages
```

For `memory_map`, most or all pages may be detected as table-heavy, so the output
may look very similar to the current table-aware output. That is acceptable.

The important part is the interface and behavior for future larger documents.

## Desired CLI

```bash
.venv/bin/python scripts/build_mixed_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_mixed_memory_map.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_memory_map.jsonl \
  --min-table-score 0.5 \
  --section-title "Memory Maps (MEMMAP)" \
  --chunk-size 800 \
  --overlap 120 \
  --table-group-size 4 \
  --table-residual-chunk-size 300 \
  --table-residual-overlap 60
```

## Required Inputs

Support:

```text
--input
--output
--doc-id
--source
--table-candidates
--min-table-score
--section-title
--chunk-size
--overlap
--table-group-size
--table-residual-chunk-size
--table-residual-overlap
```

Defaults may mirror existing scripts where reasonable.

## Required Behavior

1. Read raw pages

Read extracted pages from:

```text
data/raw_pages.jsonl
```

Each page record should include at least:

```text
page
text
```

2. Read detector output

Read candidate records from:

```text
data/table_page_candidates_memory_map.jsonl
```

Select table pages where:

```text
recommended_chunker == "table_row_group"
table_likelihood >= --min-table-score
```

3. Split pages into two sets

```text
table_pages     = selected by detector
generic_pages   = all other pages from input
```

Print a summary:

```text
Input pages: 13
Detected table pages: 12
Generic pages: 1
```

4. Build table-aware chunks for table pages

Reuse the same table-row parsing behavior as:

```text
scripts/build_table_aware_chunks.py
```

Do not modify `build_table_aware_chunks.py` heavily unless needed.

5. Build generic chunks for non-table pages

For pages not selected as table pages, create normal token-window chunks similar
to `chunk_pages.py`.

Each generic chunk should include:

```text
chunk_type: generic_page
section_title: ""
table_title: ""
table_context: ""
column_headers: []
row_count: 0
```

Use:

```text
--chunk-size
--overlap
```

6. Preserve required chunk schema

Every chunk must include:

```text
chunk_id
doc_id
source
page_start
page_end
page_chunk_index
chunk_index
token_count
text
```

Also include:

```text
chunk_type
section_title
table_title
table_context
column_headers
row_count
```

7. Stable chunk ordering

Use stable ordering by:

```text
page_start
page_chunk_index
chunk_index
```

The exact chunk_id format is not important, but it should be deterministic.

Example:

```text
mixed-000001
mixed-000002
...
```

## Validation Target

For `memory_map`, the mixed output should preserve the table-aware retrieval result.

Expected:

```text
bm25_table_boost:
hit@1 >= 80%
hit@3 >= 90%
hit@5 >= 100%
```

Ideally:

```text
80 / 100 / 100
```

Also run plain BM25:

```text
bm25:
expected close to 80 / 80 / 100
```

If results differ, document why.

## Commands

1. Generate detector output

```bash
.venv/bin/python scripts/detect_table_pages.py \
  --input data/raw_pages.jsonl \
  --output data/table_page_candidates_memory_map.jsonl \
  --page-ranges 90-102 \
  --min-score 0.5
```

2. Build mixed chunks

```bash
.venv/bin/python scripts/build_mixed_chunks.py \
  --input data/raw_pages.jsonl \
  --output data/chunks_mixed_memory_map.jsonl \
  --doc-id memory_map \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --table-candidates data/table_page_candidates_memory_map.jsonl \
  --min-table-score 0.5 \
  --section-title "Memory Maps (MEMMAP)" \
  --chunk-size 800 \
  --overlap 120 \
  --table-group-size 4 \
  --table-residual-chunk-size 300 \
  --table-residual-overlap 60
```

3. Embed

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_mixed_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

4. Evaluate BM25

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25 \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

5. Evaluate table-aware ranking

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

## Documentation

Create:

```text
docs/MIXED_CHUNK_CORPUS_EXPERIMENT.md
```

Include:

- why mixed chunking is needed
- how detector output splits pages into table/generic sets
- output chunk types
- CLI example
- memory_map validation result
- comparison with previous table-aware-only result
- limitations
- next recommendation

Clearly state:

```text
This is an experimental mixed corpus builder. It does not yet replace the normal ingest pipeline.
```

## Non-goals

Do not:

- modify `scripts/chunk_pages.py`
- modify `scripts/ingest_document.py`
- modify `scripts/ask_chunks.py`
- modify answer generation
- run model/API calls
- run answer eval
- add PyMuPDF `find_tables()`
- add Camelot / Unstructured / Docling
- add parent-child retrieval
- add reranker
- build full production ingest
- commit generated JSONL chunks
- commit vector DB files

## Error Handling

Fail clearly if:

- `--input` does not exist
- `--table-candidates` does not exist
- no pages are read from input
- candidate record is missing `page` / `table_likelihood` / `recommended_chunker`
- `--overlap >= --chunk-size`
- `--table-residual-overlap >= --table-residual-chunk-size`

If no table pages are selected, still produce generic chunks for all pages and
print a warning:

```text
WARNING: no table pages selected; output will contain generic_page chunks only.
```

## Verification

Run syntax checks:

```bash
.venv/bin/python -m py_compile \
  scripts/build_mixed_chunks.py \
  scripts/build_table_aware_chunks.py \
  scripts/detect_table_pages.py \
  scripts/eval_retrieval.py
```

Run detector + mixed builder + embed + retrieval eval.

Expected `memory_map` result:

```text
bm25_table_boost: ideally 80 / 100 / 100
```

Run cleanup checks:

```bash
git diff --check
git status --short
```

Confirm generated artifacts are ignored / not staged:

```bash
git check-ignore -v \
  data/table_page_candidates_memory_map.jsonl \
  data/chunks_mixed_memory_map.jsonl \
  vector_db/chroma
```

## Commit

Stage only source/docs changes:

```bash
git add scripts/build_mixed_chunks.py \
        docs/MIXED_CHUNK_CORPUS_EXPERIMENT.md
```

If small helper reuse required changes to `build_table_aware_chunks.py`, add it too:

```bash
git add scripts/build_table_aware_chunks.py
```

Commit:

```bash
git commit -m "Add mixed chunk corpus experiment"
```

## Done Criteria

Done when:

- `scripts/build_mixed_chunks.py` exists
- it reads raw pages and detector output
- it creates `generic_page` chunks for non-table pages
- it creates `table_row_group` and `generic_residual` chunks for detected table pages
- output is compatible with `embed_chunks.py`
- `memory_map` retrieval result is preserved or explained
- docs explain the mixed corpus workflow and limitations
- generated JSONL/vector DB files are not committed
- normal ingest and answer pipelines remain unchanged

## Scope Note

Do not replace `ingest_document.py`. The goal is only to prove that we can make
one combined chunks JSONL from raw pages + detector output.
