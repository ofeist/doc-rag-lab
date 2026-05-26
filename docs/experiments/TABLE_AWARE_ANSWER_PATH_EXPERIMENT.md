# Table-Aware Answer Path Experiment (P3-6B)

## What changed

The answer path now supports the experimental retrieval mode:

```text
bm25_table_boost
```

This mode is available in:

```text
scripts/ask_chunks.py
scripts/run_answer_eval.py
```

It uses BM25 over the provided `--chunks` file. When the query looks table-like,
it multiplies BM25 scores for chunks with:

```text
chunk_type == table_row_group
```

The default multiplier is:

```text
--table-boost 1.15
```

If chunks do not contain `chunk_type`, the mode behaves like normal BM25.

This enables table-aware retrieval in the answer path, but the normal ingest
pipeline is still unchanged.

## Single-question usage

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

To call an OpenAI-compatible model, remove `--dry-run` and pass the model
settings, for example:

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

## Batch dry-run usage

```bash
.venv/bin/python scripts/run_answer_eval.py \
  --eval eval/memory_map_eval.json \
  --limit 1 \
  --mode bm25_table_boost \
  --top-k 5 \
  --candidate-k 10 \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --dry-run \
  --output-jsonl /tmp/rag_answer_table_boost_smoke.jsonl \
  --overwrite
```

## Validation

Retrieval eval sanity was preserved:

```text
memory_map + table-aware chunks + bm25_table_boost
hit@1: 80%
hit@3: 100%
hit@5: 100%
```

Dry-run answer context checks:

| Question | Result |
| --- | --- |
| CPU0 PSPR address range and size | retrieved page 94 table chunk in selected sources (`S3`) |
| BBBBE / SPBBE / SRIBE / Access acronyms | `table_like_query: False`; retrieved page 90 acronym definitions |

Compatibility smoke:

```text
bm25_table_boost also runs against normal chunks without chunk_type metadata.
In that case no table-row boost is applied, so behavior degrades to plain BM25.
```

No model/API calls were made during this integration validation.

## Limitations

- `bm25_table_boost` is still experimental.
- Table-like query detection is a small keyword heuristic.
- The mode improves ranking only when table-aware chunks exist in the selected
  `--chunks` file.
- It does not change `scripts/chunk_pages.py` or `scripts/ingest_document.py`.
- It does not add parent-child retrieval, a reranker, or a PDF table parser.

## Recommendation

Use `bm25_table_boost` for answer-path stress tests on `memory_map` and future
table-heavy slices that have table-aware chunks. Keep normal `hybrid` retrieval
as the default for prose and semi-structured slices until another eval slice
proves a different setting is better.
