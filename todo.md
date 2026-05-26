## Active TODO (Post-P2 / Current P3 Cleanup)

1. Align docs with current canonical table-aware path:
   - ensure all "how-to" examples point to `scripts/build_table_aware_chunks.py`
   - keep memory-map-specific builder only as historical note, not active instruction

2. Finalize roadmap/document tails:
   - update `planning/RAG_ROADMAP_TO_SPACESHIP.md` "Recommended Next Concrete Step"
   - keep phase status consistent with implemented experiments

3. Resolve old memory-map builder status:
   - option A: mark `scripts/build_memory_map_table_chunks.py` as superseded
   - option B: remove it in a dedicated cleanup commit once reproducibility baseline is confirmed

4. Hygiene cleanup after merge:
   - normalize endlines/whitespace in imported eval artifacts (done for current CRLF set)
   - keep future eval outputs LF-only

5. Keep regression gate strict for retrieval changes:
   - evaluate against `boot_bmhd`, `dma_cache`, `interrupt_routing`, `memory_map`
   - compare at least `hit@1`, `hit@3`, `hit@5` before/after each change

6. Next implementation slice after cleanup:
   - small generalization pass for table-aware flow (without changing default ingest path)

