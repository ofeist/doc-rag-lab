# Table Retrieval — Design Decision (P3-4)

## Status

Decided. This records *how* table-heavy retrieval should be integrated after the
P3-2 / P3-3 experiments, without committing to a heavier parser yet.

## Background

Measured on the `memory_map` slice (`eval/memory_map_eval.json`, page-level hit@k):

```text
generic 300/60 BM25 ........... hit@1 60  hit@3 60   hit@5 80
+ table-aware chunks (P3-2) ... hit@1 80  hit@3 80   hit@5 100
+ table_boost ranking (P3-3) .. hit@1 80  hit@3 100  hit@5 100
```

Prose and semi-structured slices (`boot_bmhd`, `dma_cache`, `interrupt_routing`)
already work well with normal chunking and `hybrid` retrieval. The gains above
are specific to dense tables, and both gains are additive and low-cost.

## Decision

1. **Keep normal prose chunking as the default.** `scripts/chunk_pages.py` and the
   standard ingest path are unchanged. The default behavior for any document is
   still generic token-window chunking + `hybrid` retrieval.

2. **Add optional table-aware chunk production** for pages that are detected or
   manually selected as table-heavy. This runs *in addition to* normal chunking,
   not instead of it, and stays opt-in.

3. **Preserve `chunk_type` metadata** on every chunk (`generic` /
   `generic_residual` / `table_row_group`). It is cheap, already produced by the
   experimental builder, and is what makes ranking and debugging possible.

4. **Use table-aware ranking only when it can help** — i.e. only when
   `table_row_group` chunks exist in the corpus *and* the query looks table-like.
   The `bm25_table_boost` behavior is a no-op otherwise, so it is safe to leave
   enabled by default.

5. **Do not introduce Camelot, PyMuPDF `find_tables()`, a reranker, or
   parent-child retrieval yet.** The current heuristic + ranking combination
   already reaches `80/100/100` on the hardest slice. Heavier machinery is only
   justified if a future slice fails this approach.

## Rationale

- The biggest measured win came from cheap, inspectable steps (regular text
  parsing + a 1.15 score boost), not from a new parser. Spend complexity only
  where a measured failure demands it (guiding principle: do not overbuild before
  measuring).
- Keeping prose chunking as default protects the slices that already work. The
  table path is opt-in, so it cannot silently regress them.
- `chunk_type` is the single piece of metadata that lets retrieval stay
  content-aware without hard-coding document assumptions into the retriever.
- Both table features degrade to plain behavior when their preconditions are
  absent, so they are safe to ship before the table builder is generalized.

## Scope of the optional table path

```text
input:  pages detected/selected as table-heavy
output: table_row_group chunks (with table title, segment/context, headers
        repeated per chunk) PLUS generic_residual chunks for non-table text
        on the same pages, so page coverage stays complete
rank:   table_boost applied to table_row_group chunks on table-like queries
```

The current builder (`scripts/build_table_aware_chunks.py`) exposes the
table-aware row-group behavior through a generalized CLI. Its heuristics are
still tuned to AURIX-style address-map tables, so applying it to other dense
slices remains an explicit experiment rather than part of normal ingest.

## Non-goals (for now)

- No change to the normal ingest pipeline or its defaults.
- No Camelot / PyMuPDF `find_tables()` / Docling / Marker migration.
- No reranker (cross-encoder or local).
- No parent-child retrieval.
- No answer-layer or model changes.
- No automatic, document-agnostic table detection yet.

## What would change this decision

Revisit if a future table-heavy slice fails the
`table-aware chunks + table_boost` approach (e.g. hit@3 stays low, or the
text-based row parser cannot recover rows). At that point the first escalation is
PyMuPDF `find_tables()` on the failing pages, evaluated as its own slice before
any pipeline integration.
