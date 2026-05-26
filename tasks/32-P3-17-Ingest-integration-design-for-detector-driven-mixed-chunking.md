# P3-17 Task - Ingest Integration Design for Detector-Driven Mixed Chunking

## Context

Phase 3 proved the experimental detector-driven mixed chunking path:

```text
extract_pages -> detect_table_pages -> build_mixed_chunks -> embed_chunks
              -> eval_retrieval -> run_answer_eval
```

Key results.

P3-13 retrieval on one shared mixed corpus (hit@1 / @3 / @5):

```text
memory_map        100 / 100 / 100
boot_bmhd          70 / 100 / 100
dma_cache         100 / 100 / 100
interrupt_routing  80 / 100 / 100
```

P3-16 answer quality on the shared corpus: 39 PASS / 1 PARTIAL / 0 FAIL.

The mixed corpus contains `generic_page`, `table_row_group`, `generic_residual`
chunks. The normal ingest pipeline (`extract_pages.py`, `chunk_pages.py`,
`embed_chunks.py`, `ingest_document.py`) is still unchanged. All detector / mixed
chunking work is still experimental and explicit.

## Goal

Design how detector-driven mixed chunking should be integrated into the normal
ingest path. **Design-only.** Do not implement the integration yet. Do not add
`--chunk-mode` to `ingest_document.py` in this slice.

Create `docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md`.

## Required sections

1. Current state (scripts and responsibilities; mixed path is proven but manual).
2. Desired ingest modes (`generic`, `table-aware`, `mixed`); `generic` stays default.
3. Proposed `ingest_document.py` CLI with examples (generic, mixed over ranges,
   full-document mixed).
4. Intermediate artifacts policy.
5. Output chunk schema (common schema across all modes).
6. Retrieval mode implications (design only; no auto-selection yet).
7. Failure modes and guardrails.
8. Migration plan (thin slices P3-18..P3-22).
9. Non-goals.

## Non-goals

No reranker, parent-child retrieval, ML table classifier, Camelot / Unstructured /
Docling, PDF layout parser, automatic answer grading, or production full-document
indexing. No pipeline behavior changes in this slice.

## Validation

- No model / API calls; no retrieval eval.
- No code changes except creating `docs/design/` if missing.
- `git diff --check`, `git status --short`.

## Commit

Stage only the design doc and this task file:

```text
git add docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md
git add tasks/32-P3-17-Ingest-integration-design-for-detector-driven-mixed-chunking.md
git commit -m "Design detector-driven mixed ingest integration"
```

## Done Criteria

- design doc exists under `docs/design/`
- current experimental workflow described
- desired ingest modes defined, with default stated
- proposed `ingest_document.py` CLI documented
- artifact policy documented
- common chunk schema documented
- retrieval implications documented
- migration plan documented
- no pipeline behavior changed
