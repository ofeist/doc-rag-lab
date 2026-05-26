# Mixed Ingest Artifact Cleanup Experiment

## Context

P3-19 added end-to-end `ingest_document.py --chunk-mode mixed`. That path creates
three doc-id-scoped JSONL artifacts under `data/`:

```text
data/raw_pages_<doc_id>.jsonl
data/table_page_candidates_<doc_id>.jsonl
data/chunks_<doc_id>.jsonl
```

P3-21 implements the artifact policy from the P3-17 design.

## What changed

Mixed ingest now removes raw-page and table-candidate intermediates after a
successful embed by default:

```text
delete data/raw_pages_<doc_id>.jsonl
delete data/table_page_candidates_<doc_id>.jsonl
keep   data/chunks_<doc_id>.jsonl
```

The chunks JSONL stays because it is the stable artifact used by BM25, retrieval
eval, and debugging.

## Keeping intermediates

Use `--keep-intermediate-artifacts` when debugging extraction or table detection:

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-91 \
  --doc-id p3_21_keep_smoke \
  --collection technical_docs \
  --chunk-mode mixed \
  --section-title "P3-21 Keep Smoke" \
  --keep-intermediate-artifacts \
  --reset
```

With the flag, all three JSONL files are kept.

## Failure behavior

Cleanup runs only after `embed_chunks()` succeeds. If extraction, table detection,
mixed chunking, or embedding fails, intermediate files are left in place for
debugging.

## Verification

Unit tests cover the cleanup helper and CLI exposure:

```bash
.venv/bin/python -m pytest tests
.venv/bin/python -m py_compile scripts/ingest_document.py
```

Manual default cleanup smoke:

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-91 \
  --doc-id p3_21_cleanup_smoke \
  --collection technical_docs \
  --chunk-mode mixed \
  --section-title "P3-21 Cleanup Smoke" \
  --reset
```

Expected after success:

```text
data/raw_pages_p3_21_cleanup_smoke.jsonl does not exist
data/table_page_candidates_p3_21_cleanup_smoke.jsonl does not exist
data/chunks_p3_21_cleanup_smoke.jsonl exists
```

## Non-goals

This does not change generic ingest behavior, detector heuristics, chunking,
retrieval, Chroma metadata, or answer generation. It also does not delete the
stable chunks JSONL by default.
