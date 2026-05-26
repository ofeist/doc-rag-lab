# P3-21 Task - Add --keep-intermediate-artifacts and Default Cleanup for Mixed Ingest

## Context

P3-19 implemented `ingest_document.py --chunk-mode mixed` end-to-end.

Mixed mode currently writes generated intermediate files under `data/`:

```text
data/raw_pages_<doc_id>.jsonl
data/table_page_candidates_<doc_id>.jsonl
data/chunks_<doc_id>.jsonl
```

P3-20 added reporting and guardrail warnings. P3-20B added pytest invariant tests.

P3-17 design recommends:

- default: keep stable chunk JSONL only
- `--keep-intermediate-artifacts`: keep raw pages + table candidates + chunks

## Goal

Add `--keep-intermediate-artifacts` to `scripts/ingest_document.py`.

Default mixed behavior should clean up temporary intermediate files after successful embed.

## Required Behavior

Mixed mode default:

- delete `data/raw_pages_<doc_id>.jsonl`
- delete `data/table_page_candidates_<doc_id>.jsonl`
- keep `data/chunks_<doc_id>.jsonl`

Mixed mode with `--keep-intermediate-artifacts`:

- keep all three files

Generic mode:

- do not change existing `--raw-pages` and `--chunks` behavior

Cleanup must happen only after successful embed. If detection, mixed chunking, or embedding fails, keep intermediates for debugging.

## Tests

Add or update tests for:

- cleanup removes raw/candidate files and keeps chunks
- cleanup keeps files when requested
- CLI help exposes `--keep-intermediate-artifacts`

Do not run full PDF ingest in tests.

## Documentation

Update:

- `docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md`

Create:

- `docs/experiments/MIXED_INGEST_ARTIFACT_CLEANUP_EXPERIMENT.md`

## Verification

Run:

```bash
.venv/bin/python -m pytest tests
.venv/bin/python -m py_compile scripts/ingest_document.py
git diff --check
git status --short
```

Generated `data/` and `vector_db/` artifacts must not be committed.

## Commit

```bash
git commit -m "Add mixed ingest artifact cleanup"
```
