# Memory Map Table-vs-Prose Ranking Experiment (P3-3)

## Goal

P3-2 showed that table-aware row-group chunking improves `memory_map` retrieval,
but two questions still missed hit@3: the correct table chunk was retrieved at
rank 4 and pushed below top-3 by keyword-heavy `generic_residual` prose chunks.

P3-3 tests one minimal ranking idea:

```text
For table-like queries, prefer table_row_group chunks over generic_residual chunks.
```

Experiment only. No change to the normal ingest pipeline, no model/API calls, no
answer batch eval, no reranker, no parent-child retrieval.

## Implementation

New experimental retrieval mode in `scripts/eval_retrieval.py`:

```text
--mode bm25_table_boost
```

- Starts from the existing BM25 ranking.
- A query is treated as **table-like** if it contains any of a small local
  keyword list (`address range`, `size`, `segment`, `cpu0..cpu3`, `dspr`, `pspr`,
  `dlmu`, `lmuram`, `boot rom`, `program flash`, `data flash`, `pflash`, `eeprom`,
  `ucb`, `cfs`, `sota`).
- For table-like queries, the BM25 score of `chunk_type == table_row_group`
  chunks is multiplied by a conservative boost (default `1.15`, via
  `--table-boost`). `generic_residual` chunks are left unchanged.
- For non-table-like queries the ranking is identical to plain BM25.
- The boost is a no-op on chunk files without `chunk_type` (e.g. the normal
  pipeline chunks), so the mode is safe to leave in place.

The mode prints the boost factor and a per-question `table_like_query: True/False`
flag so the behavior is visible.

### Reproduce

```bash
.venv/bin/python scripts/eval_retrieval.py \
  --mode bm25_table_boost \
  --eval eval/memory_map_eval.json \
  --chunks data/chunks_table_aware_memory_map.jsonl \
  --db vector_db/chroma \
  --collection technical_docs
```

(`bm25_table_boost` is pure BM25 and does not query the vector DB; `--db` /
`--collection` are accepted but unused.)

## Results

| Mode | hit@1 | hit@3 | hit@5 |
| --- | ---: | ---: | ---: |
| table-aware BM25 (P3-2) | 80% | 80% | 100% |
| table-aware bm25_table_boost (1.15) | 80% | **100%** | 100% |

Per-question hit@3 PASS/FAIL:

| Question | Topic | table-like? | BM25 (P3-2) | bm25_table_boost |
| --- | --- | :---: | :---: | :---: |
| memory-map-001 | Table 23 acronyms | no | PASS | PASS |
| memory-map-002 | segment summary (p90) | yes | PASS | PASS |
| memory-map-003 | CPU0 DSPR (p93) | yes | FAIL | **PASS** |
| memory-map-004 | CPU0 PSPR (p94) | yes | FAIL | **PASS** |
| memory-map-005 | PFLASH PF0-PF5 | yes | PASS | PASS |
| memory-map-006 | Boot ROM | yes | PASS | PASS |
| memory-map-007 | Data Flash / UCB / CFS | yes | PASS | PASS |
| memory-map-008 | seg9 vs seg11 | yes | PASS | PASS |
| memory-map-009 | TC39x alt SOTA seg8 | yes | PASS | PASS |
| memory-map-010 | TC38x alt SOTA seg10 | yes | PASS | PASS |

## Verdict

The experiment **succeeds and beats the better target**:

```text
success target: hit@3 >= 90%, hit@5 stays 100%, 003 OR 004 into top-3
result:         hit@3 = 100%, hit@5 = 100%, BOTH 003 AND 004 into top-3
```

- `memory-map-003` and `memory-map-004` both moved from rank 4 into top-3. This
  matches the P3-2 score analysis: their correct table chunks scored ~16.1-16.2
  vs. a rank-3 prose chunk at ~17.8; `16.2 * 1.15 = 18.6` clears it.
- **No regression.** Every previously passing question still passes. In
  particular `memory-map-002` (answered by a page-90 prose chunk) is table-like
  and still passes — its prose chunk stays in top-3 because the boost lifts table
  chunks rather than penalizing prose.
- `memory-map-001` is correctly detected as not table-like, so it keeps plain
  BM25 ranking.
- hit@1 is unchanged at 80%: the two fixed questions reached rank 3, not rank 1,
  which is expected and sufficient for hit@3.

The conservative default boost (`1.15`, the value suggested in the task) was
enough; no further tuning was done.

## Notes / caveats

- The table-like keyword list is intentionally local to this experiment and
  tuned to the `memory_map` vocabulary. It is not a general query classifier.
- The boost only takes effect when chunks carry `chunk_type == table_row_group`,
  which today only the experimental `memory_map` table-aware file does.
- Plain `bm25` was re-checked in the same session and remained 80% / 80% / 100%,
  confirming the new mode did not alter existing modes.

## Recommended next step

The combination of **table-aware row-group chunking (P3-2) + bm25_table_boost
(P3-3)** takes `memory_map` from `60/60/80` (generic baseline) to `80/100/100`.

The next slice (P3-4) should decide how to make this reusable without changing
the normal ingest workflow, e.g.:

1. Generalize the table-aware chunk builder beyond `memory_map` (table detection
   on other dense slices) and keep `chunk_type` in chunk metadata.
2. Promote `bm25_table_boost` from an eval-only mode into the answer/retrieval
   path once the chunk format is stable.
3. Only then consider heavier options (PyMuPDF `find_tables()`, parent-child
   retrieval, or a reranker) if dense tables still fail.
