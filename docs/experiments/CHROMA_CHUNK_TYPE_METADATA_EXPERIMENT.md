# Chroma Chunk Type Metadata Experiment

## Context

P3-19 made generic and mixed chunks schema-compatible. P3-22A closes the next
storage gap: Chroma metadata now includes the scalar chunk fields needed by future
retrieval logic.

This is a metadata persistence slice only. It does not change retrieval behavior.

## What changed

`scripts/embed_chunks.py` now persists these metadata fields:

```text
doc_id
source
page_start
page_end
chunk_index
page_chunk_index
token_count
chunk_type
section_title
table_title
table_context
row_count
```

The existing fields are unchanged. The new fields are included only when present
and scalar-safe for Chroma metadata.

## Why column_headers is omitted

`column_headers` is `list[str]`, while Chroma metadata should stay scalar. P3-22A
omits it instead of serializing it, because automatic retrieval mode selection
only needs `chunk_type` as the first corpus-level signal.

## Verification

Unit and syntax checks:

```bash
.venv/bin/python -m pytest tests
.venv/bin/python -m py_compile scripts/embed_chunks.py
```

Generic ingest smoke:

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-91 \
  --doc-id p3_22a_generic_metadata_smoke \
  --collection technical_docs \
  --chunk-mode generic \
  --reset
```

Mixed ingest smoke:

```bash
.venv/bin/python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 90-100 \
  --doc-id p3_22a_mixed_metadata_smoke \
  --collection technical_docs \
  --chunk-mode mixed \
  --section-title "P3-22A Metadata Smoke" \
  --reset
```

Metadata inspection:

```bash
.venv/bin/python - <<'PY'
import chromadb

client = chromadb.PersistentClient(path="vector_db/chroma")
collection = client.get_collection("technical_docs")
result = collection.get(limit=5, include=["metadatas"])

for metadata in result["metadatas"]:
    print(metadata)
PY
```

Expected: metadata records include `chunk_type`. Mixed table-row chunks also
include table scalar fields such as `section_title`, `table_title`,
`table_context`, and `row_count`.

## Non-goals

This does not implement automatic retrieval mode selection, change retrieval
modes, modify `ask_chunks.py`, modify `eval_retrieval.py`, change detector or
chunking behavior, or persist `column_headers` as a list.
