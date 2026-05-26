# P3-6B Task - Integrate Table-Aware Retrieval into Answer Path

## Context

P3-2 / P3-3 / P3-5 proved that table-aware retrieval improves the `memory_map` slice.

Known retrieval results:

```text
generic 300/60 baseline:        60 / 60 / 80
table-aware chunks:             80 / 80 / 100
table-aware chunks + ranking:   80 / 100 / 100
```

The generalized table-aware chunk builder now exists:

```text
scripts/build_table_aware_chunks.py
```

The experimental retrieval mode now exists in retrieval eval:

```text
scripts/eval_retrieval.py --mode bm25_table_boost
```

Current limitation:

```text
retrieval eval supports bm25_table_boost
answer generation path does not yet support it
scripts/ask_chunks.py and/or scripts/run_answer_eval.py still support only the older retrieval modes
```

## Goal

Make the answer path able to use table-aware chunks plus `bm25_table_boost`.

This is still an experimental integration.

Do not change the normal ingest pipeline.
Do not run broad refactors.

## Target Behavior

Support this mode in answer generation:

```text
bm25_table_boost
```

At minimum, add support to:

```text
scripts/ask_chunks.py
```

Preferably also add support to:

```text
scripts/run_answer_eval.py
```

only if it is small and consistent with existing mode handling.

## Desired Commands

Single-question answer:

```bash
.venv/bin/python scripts/ask_chunks.py \
  --question "What address range and size are listed for CPU0 PSPR in the segment 0 to 14 address map?" \
  --mode bm25_table_boost \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --model gpt-5.4-nano \
  --base-url https://api.openai.com/v1 \
  --max-tokens 500
```

Batch answer eval, if implemented:

```bash
.venv/bin/python scripts/run_answer_eval.py \
  --eval eval/memory_map_eval.json \
  --mode bm25_table_boost \
  --top-k 5 \
  --candidate-k 10 \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --model gpt-5.4-nano \
  --base-url https://api.openai.com/v1 \
  --max-tokens 900 \
  --output-jsonl eval/rag_answer_memory_map_table_boost_gpt54nano_batch.jsonl
```

## Implementation Guidance

Reuse the same logic from `scripts/eval_retrieval.py` as much as possible.

Do not duplicate large blocks blindly if a small helper extraction is cleaner.
However, do not do a large architecture refactor.

Acceptable approaches:

Option A - Minimal duplication:

Copy the small `TABLE_LIKE_TERMS`, `is_table_like_query()`, and BM25 score adjustment into `ask_chunks.py`.
This is acceptable for now if it keeps the task small.

Option B - Small shared helper:

Create a small helper module, for example:

```text
scripts/retrieval_modes.py
```

or:

```text
scripts/retrieval_utils.py
```

Move only small reusable retrieval helpers there:

```text
tokenize
is_table_like_query
bm25_table_boost scoring helper
```

Only choose this if it stays small and does not force many unrelated changes.

## Required Behavior

For `bm25_table_boost`:

- Load chunks from `--chunks`.
- Build BM25 index from chunk text.
- Detect whether the query is table-like.
- If table-like, multiply scores for `chunk_type == table_row_group` by default boost `1.15`.
- Leave `generic_residual` unchanged.
- For non-table-like queries, ranking should be equivalent to plain BM25.
- Return selected chunks to the answer prompt exactly like other modes.

Add optional CLI flag if simple:

```text
--table-boost 1.15
```

## Important Compatibility Requirement

The new mode must work with normal chunks too.

If chunks do not have `chunk_type`, the mode must behave like normal BM25.

This makes it safe to leave the mode available even outside table-aware experiments.

## Validation Without Model Calls

Before any model call, verify retrieval context with dry-run/show-context.

Use whichever flags already exist in `ask_chunks.py`, for example:

```bash
.venv/bin/python scripts/ask_chunks.py \
  --question "What address range and size are listed for CPU0 PSPR in the segment 0 to 14 address map?" \
  --mode bm25_table_boost \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --dry-run \
  --show-context
```

The expected retrieved context should include the CPU0 PSPR table chunk from page 94 in the selected sources.

Also test:

```bash
.venv/bin/python scripts/ask_chunks.py \
  --question "What do the acronyms BBBBE, SPBBE, SRIBE, and Access mean in the MEMMAP address map tables?" \
  --mode bm25_table_boost \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --dry-run \
  --show-context
```

This should not regress the acronym/prose question.

## Optional Model Validation

Only after dry-run context looks correct, run one or two model calls.

Recommended questions:

```text
memory-map-004:
What address range and size are listed for CPU0 PSPR in the segment 0 to 14 address map?

memory-map-006:
Which address range maps to Boot ROM in segment 8 and what are its read and write access types?
```

Expected outcome:

- model should answer from table-aware context
- citations should point to the correct source chunks/pages
- no hallucination if context is present

Do not run a full answer batch unless the implementation is stable and cheap enough.

## Documentation

Create:

```text
docs/TABLE_AWARE_ANSWER_PATH_EXPERIMENT.md
```

Include:

- what changed
- supported mode
- example commands
- dry-run validation result
- optional model validation result if run
- limitations
- next recommendation

Mention clearly:

```text
This enables table-aware retrieval in the answer path, but the normal ingest pipeline is still unchanged.
```

## Non-goals

Do not:

- change `scripts/chunk_pages.py`
- change `scripts/ingest_document.py`
- change embedding model
- add PyMuPDF `find_tables()`
- add parent-child retrieval
- add reranker
- generalize to all tables
- run broad model comparisons
- commit generated JSONL outputs
- commit vector DB files

## Verification

Run syntax checks:

```bash
.venv/bin/python -m py_compile \
  scripts/ask_chunks.py \
  scripts/run_answer_eval.py \
  scripts/eval_retrieval.py
```

Adjust the list if `run_answer_eval.py` was not changed.

Run retrieval eval sanity:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

Expected:

```text
hit@1: 80%
hit@3: 100%
hit@5: 100%
```

Run dry-run answer context test for at least `memory-map-004`.

Run:

```bash
git diff --check
git status --short
```

Confirm generated artifacts are ignored / not staged:

```bash
git check-ignore -v data/chunks_table_aware_memory_map.jsonl vector_db/chroma
```

## Commit

Stage only source/docs changes.

Examples:

```bash
git add scripts/ask_chunks.py \
        docs/TABLE_AWARE_ANSWER_PATH_EXPERIMENT.md
```

If `run_answer_eval.py` was changed:

```bash
git add scripts/run_answer_eval.py
```

If a small shared helper was added:

```bash
git add scripts/retrieval_utils.py
```

Commit message:

```bash
git commit -m "Add table-aware retrieval mode to answer path"
```

## Done Criteria

Done when:

- `ask_chunks.py` supports `bm25_table_boost`
- dry-run/show-context confirms correct table chunks are selected
- normal BM25 behavior is not broken
- optional `run_answer_eval.py` support is added only if small
- docs explain how to use the mode
- generated JSONL/vector DB files are not committed
- normal ingest pipeline remains unchanged

## Scope Note

First implement `ask_chunks.py` only. Touch `run_answer_eval.py` only if it is trivial; batch eval integration can be a separate mini-slice if it becomes messy.
