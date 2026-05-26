# Phase 3 Shared-Corpus Checkpoint

Short checkpoint after the detector-driven mixed chunking and shared-corpus smoke
tests (P3-10 .. P3-13). It extends `docs/project/PHASE3_TABLE_RETRIEVAL_SUMMARY.md`, which
covered the table-retrieval foundations up to P3-9.

## Where we are now

- **We can build one shared mixed corpus for multiple technical slices.** A single
  detector-driven mixed corpus (`extract_pages -> detect_table_pages ->
  build_mixed_chunks -> embed`) now spans several disjoint sections of the manual
  at once, mixing `generic_page`, `table_row_group`, and `generic_residual` chunks.
- **Retrieval remains strong across all known evals.** Running every eval slice
  against that one shared corpus (P3-13) gave:

  ```text
  memory_map        bm25_table_boost  100 / 100 / 100
  boot_bmhd         hybrid             70 / 100 / 100
  dma_cache         hybrid            100 / 100 / 100
  interrupt_routing hybrid             80 / 100 / 100   (hit@1 / hit@3 / hit@5)
  ```

  All four slices reach hit@3 = 100% and hit@5 = 100% with no regression versus
  their standalone baselines and no cross-slice interference.
- **Detector precision held** on a 109-page, multi-section selection: only true
  address-map pages became `table_row_group`; `generic_table` pages stayed generic.

## What is still off-limits (unchanged)

- The **normal ingest pipeline is still not replaced.** `scripts/chunk_pages.py`
  and `scripts/ingest_document.py` are unchanged; all table/mixed work is
  experimental and explicit.
- Retrieval mode selection is still manual (per-slice).
- No answer-layer changes in this line of work, no model/API calls in the smoke
  tests, no reranker, no parent-child retrieval, no PDF table parser.
- Generated `data/` and `vector_db/` artifacts are not committed.

## Next step

Two reasonable directions; pick one as the next slice:

1. **Full-document smoke test** — run the mixed pipeline over the whole manual to
   stress detector precision/recall and artifact size at scale.
2. **Ingest integration design** — design how detector-driven mixed chunking and
   automatic retrieval-mode selection (`hybrid` for prose, `bm25_table_boost` when
   `table_row_group` chunks exist and the query is table-like) would move from the
   experimental scripts into the normal ingest/answer path.

Either is a deliberate next slice; this checkpoint does not start it.
