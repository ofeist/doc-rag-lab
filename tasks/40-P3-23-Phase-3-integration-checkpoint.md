# P3-23 Task - Phase 3 Integration Checkpoint

## Context

We completed the Phase 3 detector-driven mixed ingest integration work.

Completed slices:

```text
P3-17   Design detector-driven mixed ingest integration
P3-18   Add chunk-mode CLI skeleton
P3-19   Implement schema-compatible mixed ingest end-to-end
P3-20   Add mixed ingest reporting guardrails
P3-20B  Add mixed ingest invariant tests
P3-21   Add mixed ingest artifact cleanup
P3-22A  Persist chunk_type metadata in Chroma
P3-22B  Add automatic retrieval mode selection
```

Recent commits (reference list):

```text
6617c51 Design detector-driven mixed ingest integration
947d61a Add ingest chunk-mode CLI skeleton
504f7ca Implement schema-compatible mixed ingest
739fcf9 Add mixed ingest reporting guardrails
99f76aa Add mixed ingest invariant tests
d7f5c93 Add P3-21 mixed ingest artifact cleanup task
ec28a63 Add mixed ingest artifact cleanup
4f10cb8 Add P3-22A Chroma metadata task
86185d5 Persist chunk type metadata in Chroma
0a69fb6 Add P3-22B automatic retrieval mode task
f9f3c48 Add automatic retrieval mode selection
```

Current verified state:

```text
pytest: 17 passed
generic ingest smoke: OK
mixed ingest smoke: OK
Chroma metadata inspection: chunk_type and table scalar fields present
memory_map --mode auto: 100 / 100 / 100
boot_bmhd --mode auto: 70 / 100 / 100
ask_chunks.py --mode auto dry-run:
  table-like query -> bm25_table_boost
  prose query      -> hybrid
run_answer_eval.py --mode auto --dry-run --limit 2: OK, writes effective_mode
```

## Goal

Create a concise checkpoint document summarizing the completed Phase 3 integration state.

Docs-only task.

## Create

`docs/PHASE3_INTEGRATION_CHECKPOINT.md`

## The document should include

1. Short summary of what is integrated now.
2. What now works (flow + user-facing command examples).
3. Retrieval mode behavior (manual modes unchanged, `auto` opt-in, selection logic).
4. Artifact behavior (mixed ingest cleanup + keep flag, cleanup only after successful embed).
5. Metadata/schema state (schema-compatible chunks; Chroma metadata fields; why `column_headers` omitted).
6. Test coverage (what is covered; current `17 passed`).
7. Known limitations (heuristics, HNSW variance, no reranker/parent-child/parser/grading, full-doc not tuned).
8. Recommended next steps (P3-24 full-doc smoke, P3-25 README/CLI polish, later retrieval work).

## Optional update

Optionally update `docs/design/DETECTOR_DRIVEN_MIXED_INGEST_DESIGN.md` with a single pointer line to the checkpoint doc.

## Verification

```bash
git diff --check
git status --short
```

No code changes.

## Commit

```bash
git commit -m "Add Phase 3 integration checkpoint"
```

