## Active TODO (Post-P2 / Current P3 Cleanup)

1. Align docs with current canonical table-aware path:
   - ensure all "how-to" examples point to `scripts/build_table_aware_chunks.py`
   - status: done in P3-6A

2. Finalize roadmap/document tails:
   - update `planning/RAG_ROADMAP_TO_SPACESHIP.md` "Recommended Next Concrete Step"
   - keep phase status consistent with implemented experiments
   - status: done for P3-6A

3. Resolve old memory-map builder status:
   - status: removed in P3-6A after generalized builder equivalence was verified

4. Hygiene cleanup after merge:
   - normalize endlines/whitespace in imported eval artifacts (done for current CRLF set)
   - keep future eval outputs LF-only

5. Keep regression gate strict for retrieval changes:
   - evaluate against `boot_bmhd`, `dma_cache`, `interrupt_routing`, `memory_map`
   - compare at least `hit@1`, `hit@3`, `hit@5` before/after each change

6. Next implementation slice after P3-6A:
   - select the next failing table-heavy slice before adding parser/reranker complexity
