# Doc RAG Lab

Local RAG lab for technical PDF documentation. The pipeline extracts pages,
chunks them, embeds into a local ChromaDB, evaluates retrieval quality, and can
generate grounded answers via an OpenAI-compatible API.

Phase 3 adds detector-driven mixed chunking for table-heavy manuals:
non-table pages become `generic_page` chunks, while detected table-heavy pages
produce `table_row_group` + `generic_residual` chunks.

## What Currently Works

- Generic ingest: extract -> chunk -> embed
- Mixed ingest: extract -> detect tables -> build mixed chunks -> embed
- Retrieval eval: `scripts/eval_retrieval.py` including opt-in `--mode auto`
- Grounded answers: `scripts/ask_chunks.py` and batch `scripts/run_answer_eval.py`
- Persisted Chroma metadata includes `chunk_type` and table scalar fields
- Mixed ingest artifact cleanup by default (`--keep-intermediate-artifacts` for debugging)
- Pytest coverage (`17` tests passing in current baseline)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-rag.txt
pip install -r requirements-dev.txt
```

Note: `requirements-dev.txt` includes `-r requirements-rag.txt`, so installing
both is redundant. Use `requirements-dev.txt` when you want tests; use
`requirements-rag.txt` when you only want the pipeline dependencies.

## Input Document Location

The current examples use:

`docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf`

Reference documentation landing page:
`https://documentation.infineon.com/aurixtc3xx/docs/qmd1702366622648`

During this PoC, `docs/` contains both project documentation and the local
sample/vendor PDF used for testing. A future cleanup may move source PDFs to a
separate directory such as `source_docs/`.

Eval files under `eval/` are currently tuned for the AURIX manual. You can swap
in another technical PDF, but expect to adjust the eval sets.

## Generic Ingest (Focused Slice)

Generic ingest is the default mode and is a good baseline for prose-heavy
content (page-aware token-window chunking).

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-126 \
  --doc-id aurix_generic_slice \
  --collection technical_docs \
  --chunk-mode generic \
  --reset
```

If you already have a chunks JSONL and only want to embed it into Chroma:

```bash
.venv/bin/python scripts/embed_chunks.py \
  --chunks data/chunks.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

## Mixed Ingest (Shared Corpus)

Mixed ingest runs: extract -> detect table-heavy pages -> build mixed chunks -> embed.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-126,257-259,307-314,1364-1397,1435-1455,1483-1488 \
  --doc-id aurix_mixed_shared \
  --collection technical_docs \
  --chunk-mode mixed \
  --section-title "AURIX Mixed Shared Corpus" \
  --reset
```

Mixed chunk types:

```text
generic_page
table_row_group
generic_residual
```

Artifacts (mixed mode):

- always keeps: `data/chunks_<doc_id>.jsonl`
- by default cleans after successful embed:
  - `data/raw_pages_<doc_id>.jsonl`
  - `data/table_page_candidates_<doc_id>.jsonl`
- `--keep-intermediate-artifacts` keeps intermediates for debugging

## Full-Document Mixed Ingest Smoke

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --doc-id aurix_tc3xx_full_mixed_smoke \
  --collection technical_docs \
  --chunk-mode mixed \
  --section-title "AURIX TC3xx Full Mixed Smoke" \
  --reset
```

Known smoke result (AURIX manual):

- 2080 pages extracted
- 2593 chunks embedded
- hit@5 stayed 100% across the four known eval slices

This is a smoke test only; it does not imply production readiness or tuned
full-document retrieval.

## Retrieval Eval

Canonical auto-mode example:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/eval_retrieval.py \
  --mode auto \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_aurix_mixed_shared.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

Manual modes:

```text
vector
bm25
hybrid
bm25_table_boost
```

Opt-in mode:

```text
auto
```

Auto selection logic:

```text
if query is table-like and chunks JSONL contains table_row_group:
    bm25_table_boost
else:
    hybrid
```

Known eval files:

```text
eval/memory_map_eval.json
eval/boot_bmhd_eval.json
eval/dma_cache_eval.json
eval/interrupt_routing_eval.json
```

## Ask Chunks (Dry-Run Context)

Dry-run does not call any model/API; it prints sources and the constructed prompt.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
.venv/bin/python scripts/ask_chunks.py \
  --question "What address range maps to Program Flash 0?" \
  --chunks data/chunks_aurix_mixed_shared.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --mode auto \
  --dry-run \
  --show-context
```

## Answer Generation (OpenAI-Compatible)

Requires `OPENAI_API_KEY` in the environment. `--base-url` can point to OpenAI or
another OpenAI-compatible API.

```bash
OPENAI_API_KEY=... \
.venv/bin/python scripts/ask_chunks.py \
  --question "What does the SRPN field define in the SRC register?" \
  --chunks data/chunks_aurix_mixed_shared.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --mode auto \
  --model <openai-compatible-model> \
  --base-url https://api.openai.com/v1 \
  --max-tokens 250
```

## Tests

```bash
.venv/bin/python -m pytest tests
```

Known baseline: `17 passed`.

## Generated Artifacts and Cleanup

Generated / gitignored:

```text
data/*.jsonl
vector_db/
```

Notes:

- chunks JSONL is the stable artifact used for BM25/eval/debugging
- raw pages and table candidates are intermediate debug artifacts in mixed mode
- PDFs under `docs/` may be vendor documents; do not redistribute unless allowed

## Offline / Cache Notes

If the embedding model is already cached locally, these env vars avoid slow
network attempts:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
```

This will not work if the model is not cached.

## Known Limitations

- `auto` is heuristic, not a reranker
- full-document retrieval has more competition than focused slices
- hit@1/hit@3 can vary slightly with HNSW rebuilds
- no reranker, no parent-child retrieval
- no PDF layout parser (Camelot/Docling/Unstructured)
- no automatic answer grading

## Useful Docs

```text
docs/PHASE3_INTEGRATION_CHECKPOINT.md
docs/experiments/FULL_DOCUMENT_MIXED_INGEST_SMOKE.md
docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md
```
