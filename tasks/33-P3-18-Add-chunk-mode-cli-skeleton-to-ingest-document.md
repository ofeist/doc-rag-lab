# P3-18 Task - Add Chunk-Mode CLI Skeleton to ingest_document.py

## Context

P3-17 designed detector-driven mixed ingest integration in
`docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md`. Key decisions: `generic`
stays default, `mixed` is opt-in, schema work is P3-19, auto retrieval-mode
selection is P3-22. Two integration gaps were documented (generic chunk schema
not yet mixed-compatible; `embed_chunks.safe_metadata()` does not persist
`chunk_type`). P3-18 is therefore intentionally small: CLI/API preparation only.

## Goal

Add a user-facing `--chunk-mode {generic,mixed}` skeleton to
`scripts/ingest_document.py` without changing default behavior.

- `--chunk-mode generic` (default): behaves exactly like current ingest.
- omitting the flag: same as `generic`.
- `--chunk-mode mixed`: exits clearly with a not-implemented message.

## Non-goals

Do not implement mixed ingest; do not call `detect_table_pages.py` or
`build_mixed_chunks.py`; do not modify `chunk_pages.py` or `embed_chunks.py`; do
not change the chunk schema or persist `chunk_type` to Chroma; do not change
default behavior; no model/API calls, no answer eval, no retrieval tuning.

## Verification

1. `.venv/bin/python -m py_compile scripts/ingest_document.py`
2. `--help` shows `--chunk-mode`.
3. Tiny generic smoke (`--page-ranges 90-91`, `--chunk-mode generic`) succeeds.
4. Same smoke without `--chunk-mode` behaves identically.
5. `--chunk-mode mixed` exits non-zero with a clear message, no misleading ingest.
6. `git diff --check`, `git status --short`; no `data/` or `vector_db/` committed.

## Commit

```text
git add scripts/ingest_document.py
git add docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md
git add tasks/33-P3-18-Add-chunk-mode-cli-skeleton-to-ingest-document.md
git commit -m "Add ingest chunk-mode CLI skeleton"
```

## Done Criteria

- `ingest_document.py --help` shows `--chunk-mode`
- default behavior remains current/generic
- `--chunk-mode generic` works; omitting it works
- `--chunk-mode mixed` exits clearly as not implemented
- no mixed ingest implemented; generated artifacts not committed
