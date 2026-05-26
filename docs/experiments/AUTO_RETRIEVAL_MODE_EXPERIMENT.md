# Auto Retrieval Mode Experiment

## Context

P3-22A made `chunk_type` and scalar table metadata available in Chroma. P3-22B
adds an opt-in retrieval mode selector across retrieval eval and answer paths.

This is intentionally conservative: existing manual modes and defaults are
unchanged.

## What auto mode does

`--mode auto` resolves to:

```text
bm25_table_boost  when query is table-like and chunks JSONL contains table_row_group
hybrid            otherwise
```

Manual modes still force the requested behavior:

```text
vector
bm25
hybrid
bm25_table_boost
```

## Decision signals

The query signal reuses the same table-like term list already used by
`bm25_table_boost`.

The corpus signal reads the chunks JSONL and checks for:

```text
chunk_type == "table_row_group"
```

Chroma metadata is now ready for this signal, but P3-22B deliberately keeps the
resolver JSONL-based to avoid adding Chroma coupling to the selector.

## Reporting

When `--mode auto` is used, CLIs print the selected effective mode and reason:

```text
mode: auto
effective_mode: bm25_table_boost
auto_reason: table-like query and table_row_group chunks present
```

Batch answer eval records include:

```text
requested_mode
effective_mode
```

## Verification

Unit and syntax checks:

```bash
.venv/bin/python -m pytest tests
.venv/bin/python -m py_compile scripts/retrieval_mode.py scripts/eval_retrieval.py scripts/ask_chunks.py scripts/run_answer_eval.py
```

The shared mixed corpus was embedded locally:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

Retrieval eval smoke:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/eval_retrieval.py \
  --mode auto \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

Result:

```text
memory_map: hit@1 100%, hit@3 100%, hit@5 100%
```

Boot/BMHD smoke:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/eval_retrieval.py \
  --mode auto \
  --eval eval/boot_bmhd_eval.json \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --top-k 5 \
  --candidate-k 8
```

Result:

```text
boot_bmhd: hit@1 70%, hit@3 100%, hit@5 100%
```

Most Boot/BMHD questions selected `hybrid`. One query mentioning `DSPR/PSPR`
selected `bm25_table_boost` because those terms are part of the existing
table-like heuristic. This is acceptable for this slice because the result did
not regress and the heuristic was intentionally not retuned.

Answer dry-run smoke:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/ask_chunks.py \
  --question "What address range maps to Program Flash 0?" \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --mode auto \
  --dry-run \
  --show-context
```

Selected `bm25_table_boost` and retrieved memory-map table chunks.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/ask_chunks.py \
  --question "What does the startup software do after reset?" \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --mode auto \
  --dry-run \
  --show-context
```

Selected `hybrid` and retrieved prose-oriented startup firmware context.

Batch answer dry-run smoke:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/run_answer_eval.py \
  --eval eval/memory_map_eval.json \
  --limit 2 \
  --mode auto \
  --chunks data/chunks_mixed_multi_slice.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --dry-run \
  --output-jsonl /tmp/p3_22b_auto_answer_eval.jsonl \
  --overwrite
```

The JSONL output includes `requested_mode: auto` and per-question
`effective_mode`.

## Known limitations

The table-like query heuristic is still keyword-based. It can route a prose query
that mentions table-ish memory terms to `bm25_table_boost`; P3-22B records that
behavior but does not tune it.

The selector reads the chunks JSONL instead of Chroma metadata. That keeps this
slice simple and matches current retrieval commands, but future production
selection may use Chroma metadata directly.

## Non-goals

This does not change default retrieval mode, remove manual modes, tune detector
or chunking behavior, add reranking, add parent-child retrieval, or run model/API
calls.
