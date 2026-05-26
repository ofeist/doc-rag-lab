# P3-15 Task - Organize Project Documentation

## Goal

The `docs/` directory has grown to ~19 Markdown reports in a flat layout. Group
them into three subdirectories by purpose, without changing any content meaning.

```text
docs/project/      project-level status: workflow, phase summaries, checkpoints
docs/experiments/  experiment reports, smoke tests, diagnostics
docs/design/       design decisions and interface specs
```

## Scope

- Move the Markdown reports with `git mv` (preserve history).
- Leave vendor/source PDFs in `docs/` untouched.
- Update living links/references where needed (intra-docs references, README).
- Do not change scripts.
- Do not rerun evals.
- Leave historical `tasks/` and `planning/` files as-is (they are a log of what
  was done at the time, not live links).

## Planned mapping

```text
docs/project/
  CURRENT_WORKFLOW.md
  PHASE2_SUMMARY.md
  PHASE3_TABLE_RETRIEVAL_SUMMARY.md
  PHASE3_TABLE_RETRIEVAL_CHECKPOINT.md
  PHASE3_SHARED_CORPUS_CHECKPOINT.md

docs/design/
  TABLE_RETRIEVAL_DESIGN_DECISION.md
  TABLE_AWARE_BUILDER_INTERFACE.md

docs/experiments/
  MEMORY_MAP_RETRIEVAL_DIAGNOSTIC.md
  MEMORY_MAP_CHUNK_SIZE_EXPERIMENT.md
  MEMORY_MAP_TABLE_AWARE_EXPERIMENT.md
  MEMORY_MAP_TABLE_RANKING_EXPERIMENT.md
  TABLE_PAGE_DETECTION_EXPERIMENT.md
  TABLE_PAGE_DETECTOR_PRECISION_EXPERIMENT.md
  DETECTOR_DRIVEN_TABLE_CHUNKING_EXPERIMENT.md
  MIXED_CHUNK_CORPUS_EXPERIMENT.md
  MIXED_CORPUS_SMOKE_TEST.md
  LARGE_SECTION_MIXED_INGEST_SMOKE_TEST.md
  MULTI_SLICE_SHARED_CORPUS_SMOKE_TEST.md
  TABLE_AWARE_ANSWER_PATH_EXPERIMENT.md
```

## References to update

- `docs/experiments/MEMORY_MAP_RETRIEVAL_DIAGNOSTIC.md` -> link to
  `MEMORY_MAP_CHUNK_SIZE_EXPERIMENT.md` (now in `docs/experiments/`).
- `docs/project/PHASE3_SHARED_CORPUS_CHECKPOINT.md` -> link to
  `PHASE3_TABLE_RETRIEVAL_SUMMARY.md` (now in `docs/project/`).
- `README.md` structure section -> describe the new `docs/` subfolders.

## Done Criteria

- All 19 reports live under `docs/project|experiments|design`.
- Vendor PDF still in `docs/` (untouched).
- Intra-docs references and README still resolve.
- No script changes, no eval reruns.
