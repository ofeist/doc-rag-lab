# Phase 3 Table Retrieval Checkpoint

## Verdict

P3-6B is accepted and closed.

We can now improve dense table retrieval when table-aware chunks are available.
The remaining unsolved problem is automatic detection of table-heavy pages in
large documents.

In practical terms: we have reached the real scaling problem. The current
approach works when the table-heavy pages are known, but we still do not have a
repeatable way to find those pages automatically in a 3000-page document.

## What We Proved

- Generic prose chunking remains the normal ingest path.
- Dense table-heavy slices need different treatment than prose slices.
- For `memory_map`, table-aware row-group chunks improved retrieval over generic
  300/60 chunks.
- `bm25_table_boost` preserved the best measured retrieval result:

```text
memory_map + table-aware chunks + bm25_table_boost
hit@1: 80%
hit@3: 100%
hit@5: 100%
```

- The answer path now supports `bm25_table_boost` through:

```text
scripts/ask_chunks.py
scripts/run_answer_eval.py
```

- Dry-run answer context validation confirmed that table-aware chunks can reach
  the grounded answer prompt.

## What Is Still Missing

The main missing piece is not another answer model or another manual eval.

The missing piece is:

```text
automatic table-heavy page detection
```

Without that, table-aware chunking is useful but still manual. For large
technical manuals, we need a cheap local detector that can identify candidate
pages before table-aware chunking runs.

## Recommended Next Steps

1. P3 checkpoint doc
2. P3-7 automatic table-heavy page detection
3. P3-8 mixed ingest: prose chunks + table chunks
4. P3-9 automatic retrieval mode selection

## Guardrails

- Do not change the normal ingest pipeline until detection is measured.
- Do not add a heavier parser before a local page detector baseline exists.
- Keep `memory_map` as the table-heavy regression slice.
- Keep prose/semi-structured slices in regression checks:

```text
boot_bmhd
dma_cache
interrupt_routing
```

## Current Decision

Proceed to P3-7:

```text
Automatic table-heavy page detection
```

The goal is to identify likely table-heavy pages from extracted PDF text so
table-aware chunking can become repeatable across large documents without
manually searching for tables.
