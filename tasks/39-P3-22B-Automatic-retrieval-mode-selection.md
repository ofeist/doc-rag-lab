# P3-22B Task - Automatic Retrieval Mode Selection

## Context

P3-17 documented the future retrieval direction:

```text
hybrid stays the default for general/prose queries
bm25_table_boost should be used when:
  corpus contains table_row_group chunks
  query looks table-like
```

P3-19 made chunks schema-compatible. P3-22A persisted `chunk_type` and scalar
table metadata to Chroma.

## Goal

Add opt-in retrieval mode:

```text
--mode auto
```

`auto` should select:

- `bm25_table_boost` when the query looks table-like and the corpus contains
  `table_row_group` chunks
- `hybrid` otherwise

Do not change existing default behavior.

## Required Paths

Inspect and update mode handling in:

- `scripts/eval_retrieval.py`
- `scripts/ask_chunks.py`
- `scripts/run_answer_eval.py`

Reuse existing table-like query logic where possible.

## Tests

Add tests for:

- corpus has table row groups
- generic-only corpus does not
- `auto` selects `bm25_table_boost` for table-like query plus table corpus
- `auto` selects `hybrid` for prose query
- `auto` selects `hybrid` for table-like query without table corpus
- manual modes are unchanged

## Documentation

Create:

- `docs/experiments/AUTO_RETRIEVAL_MODE_EXPERIMENT.md`

Update:

- `docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md`

## Verification

Run:

```bash
.venv/bin/python -m pytest tests
.venv/bin/python -m py_compile scripts/retrieval_mode.py scripts/eval_retrieval.py scripts/ask_chunks.py scripts/run_answer_eval.py
git diff --check
git status --short
```

Run retrieval and dry-run answer smokes with `--mode auto`. Do not run model/API
calls.

## Non-goals

Do not:

- change default retrieval mode
- remove manual modes
- tune keyword heuristics heavily
- change detector/chunking/ingest
- run model/API calls
- add reranker
- add parent-child retrieval
- make Chroma metadata mandatory for auto mode

## Commit

```bash
git commit -m "Add automatic retrieval mode selection"
```
