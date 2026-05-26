# Phase 3 Integration Checkpoint

This checkpoint records the current integrated state of the Phase 3
detector-driven mixed ingest work. The previously experimental path is now
available through the normal CLI entry points for ingest, retrieval eval, and
answer generation.

## Summary

What is integrated now:

- `scripts/ingest_document.py --chunk-mode mixed` orchestrates extract -> detect
  -> mixed chunking -> embed using doc-id-scoped intermediate files.
- Chunks are schema-compatible across modes (`generic_page`, `table_row_group`,
  `generic_residual`).
- Mixed ingest prints a final report and guardrail warnings (detector summary,
  chunk-type counts, over-selection warnings).
- Mixed ingest supports artifact cleanup by default, and keeps intermediates only
  when requested.
- `embed_chunks.safe_metadata()` persists `chunk_type` and table scalar fields to
  Chroma metadata.
- Retrieval/answer paths support an opt-in `--mode auto` that selects a retrieval
  mode conservatively based on query + corpus signals.
- Lightweight pytest coverage exists for the integration invariants (currently
  `17 passed`).

## What Now Works

Conceptual pipeline flow:

```text
extract_pages
-> detect_table_pages
-> build_mixed_chunks
-> embed_chunks
-> eval_retrieval / ask_chunks / run_answer_eval (with --mode auto)
```

User-facing mixed ingest example:

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-126,257-259,307-314,1364-1397,1435-1455,1483-1488 \
  --doc-id mixed_shared \
  --collection technical_docs \
  --chunk-mode mixed \
  --section-title "Mixed Shared Corpus" \
  --reset
```

Retrieval eval with auto mode:

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode auto \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_mixed_shared.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

## Retrieval Mode Behavior

Manual modes remain unchanged:

```text
vector
bm25
hybrid
bm25_table_boost
```

New opt-in mode:

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

Important: `auto` is opt-in. Default behavior is unchanged.

## Artifact Behavior (Mixed Ingest)

Mixed ingest generates these artifacts under `data/`:

```text
data/raw_pages_<doc_id>.jsonl
data/table_page_candidates_<doc_id>.jsonl
data/chunks_<doc_id>.jsonl
```

Default policy (after successful embed):

```text
keep   data/chunks_<doc_id>.jsonl
delete data/raw_pages_<doc_id>.jsonl
delete data/table_page_candidates_<doc_id>.jsonl
```

With `--keep-intermediate-artifacts`:

```text
keep all three files
```

Cleanup runs only after a successful embed. If extraction/detection/chunking/embed
fails, intermediates are kept for debugging.

## Metadata / Schema State

All chunks share a compatible JSONL schema, including:

```text
chunk_type
section_title
table_title
table_context
row_count
```

Chroma metadata now persists these scalar fields as well:

```text
chunk_type
section_title
table_title
table_context
row_count
```

`column_headers` is not persisted to Chroma metadata because it is list-valued.

## Test Coverage

Lightweight pytest coverage exists for:

- generic chunk schema compatibility
- mixed ingest report summaries and guardrail warnings
- mixed artifact cleanup helper behavior and CLI flag exposure
- `embed_chunks.safe_metadata()` scalar metadata persistence
- `--mode auto` resolver (query + corpus signals)

Current status: `17 passed`.

## Known Limitations

- `auto` mode is heuristic; it is not a reranker.
- Query table-likeness depends on keyword logic.
- Vector/HNSW and hybrid hit@1/hit@3 can vary slightly across rebuilds; hit@5 has
  been stable in known shared-corpus checks.
- Full-document mixed ingest has not yet been validated as a tuned deliverable.
- No parent-child retrieval, no reranker.
- No PDF layout parser (Camelot/Docling/Unstructured) integrated.
- No automatic answer grading.

## Recommended Next Steps

- P3-24: full-document mixed ingest smoke test (runtime/artifact size/detector precision at scale).
- P3-25: README/CLI polish (canonical commands, flags, and guardrail expectations).
- Later: retrieval robustness improvements (reranking, parent-child retrieval,
  table parser experiments) based on failure-driven eval slices.
