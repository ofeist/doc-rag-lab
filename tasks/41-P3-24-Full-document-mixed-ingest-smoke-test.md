# P3-24 Task - Full-Document Mixed Ingest Smoke Test

## Context

We have:

- `scripts/ingest_document.py --chunk-mode mixed`
- `--keep-intermediate-artifacts`
- schema-compatible chunks
- `chunk_type` metadata persisted to Chroma
- retrieval `--mode auto`
- pytest coverage

The shared eval-slice corpus works, but full-document mixed ingest had not been
validated yet.

## Goal

Run a conservative full-document mixed ingest smoke test.

Smoke test only, not production tuning.

## Constraints

Do not:

- change detector logic
- change chunking
- tune retrieval
- run answer generation / model API calls
- commit generated `data/` or `vector_db/` artifacts

## Command

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --doc-id aurix_tc3xx_full_mixed_smoke \
  --collection technical_docs \
  --chunk-mode mixed \
  --section-title "AURIX TC3xx Full Mixed Smoke" \
  --reset
```

Default behavior should keep only:

```text
data/chunks_aurix_tc3xx_full_mixed_smoke.jsonl
```

Use `--keep-intermediate-artifacts` only if debugging is needed.

## After Ingest

Record:

- pages extracted
- candidate pages emitted
- `address_map_table` count
- `generic_table` count
- `table_row_group` routed pages count
- chunk distribution: `generic_page`, `table_row_group`, `generic_residual`
- cleanup behavior correctness (only after successful embed)
- Chroma metadata includes `chunk_type`
- rough runtime observation
- any warnings

## Retrieval Smoke (Auto)

Run these evals:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode auto \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_aurix_tc3xx_full_mixed_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs

.venv/bin/python scripts/eval_retrieval.py \
  --mode auto \
  --eval eval/boot_bmhd_eval.json \
  --chunks data/chunks_aurix_tc3xx_full_mixed_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8

.venv/bin/python scripts/eval_retrieval.py \
  --mode auto \
  --eval eval/dma_cache_eval.json \
  --chunks data/chunks_aurix_tc3xx_full_mixed_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8

.venv/bin/python scripts/eval_retrieval.py \
  --mode auto \
  --eval eval/interrupt_routing_eval.json \
  --chunks data/chunks_aurix_tc3xx_full_mixed_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8
```

Expectation: full-doc retrieval may be weaker than shared-slice corpora due to
more competition. Do not tune in this slice; record honestly.

## Optional ask_chunks Dry-Run

No API calls:

```bash
.venv/bin/python scripts/ask_chunks.py \
  --question "What address range maps to Program Flash 0?" \
  --chunks data/chunks_aurix_tc3xx_full_mixed_smoke.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --mode auto \
  --dry-run \
  --show-context
```

Expected: auto selects `bm25_table_boost`.

## Documentation

Create:

`docs/experiments/FULL_DOCUMENT_MIXED_INGEST_SMOKE.md`

Include:

- command used
- ingest summary
- chunk distribution
- artifact cleanup result
- metadata inspection result
- retrieval eval results
- dry-run result (if performed)
- limitations, verdict, next step

## Verification

```bash
git diff --check
git status --short
```

Only the experiment doc should be staged (for the result commit).

## Commit

```bash
git commit -m "Run full-document mixed ingest smoke"
```

