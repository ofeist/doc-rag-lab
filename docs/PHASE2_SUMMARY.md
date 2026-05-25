# Phase 2 Summary

## 1. What Phase 2 Achieved

- Full-document ingest is now the normal workflow via `scripts/ingest_document.py`.
- Focused page-range ingest is available as an eval/debug mode (`--page-ranges`).
- `configs/slices.json` is a curated eval/debug fixture registry, not product config.
- Retrieval eval is repeatable (`scripts/eval_retrieval.py` across modes).
- Answer batch eval is repeatable (`scripts/run_answer_eval.py`) and output handling is
  explicit:
  - default: fail if output JSONL already exists
  - `--overwrite`: replace output file
  - `--append`: intentionally append runs

## 2. Current Eval Slices

| Slice | Content type | Recommended chunking | Recommended retrieval mode | Status |
| --- | --- | --- | --- | --- |
| `boot_bmhd` | startup flow + mixed prose/table | 800 / 120 | `hybrid` | stable baseline |
| `dma_cache` | technical prose + config details | 800 / 120 | `hybrid` | stable baseline |
| `interrupt_routing` | register/procedure mix | 800 / 120 | `hybrid` | stable baseline |
| `memory_map` | table-heavy address/range mappings | 300 / 60 | `bm25_first_hybrid` (or `bm25`) | stress slice |

## 3. Memory Map Findings

- Table-heavy content is harder than prose or semi-structured sections.
- Vector and RRF hybrid underperformed on this slice.
- BM25 performed better than vector and better than RRF hybrid.
- Smaller chunks improved retrieval (`300/60` best tested hit@5).
- Answer quality is mostly good when the correct chunks are present.
- Remaining failures are mostly retrieval/context/table-layout related, not pure extraction
  absence.

Memory map grading summary:

```text
PASS:    6
PARTIAL: 2
FAIL:    2
```

## 4. Known Limitations

- No table-aware chunking yet.
- No parent-child retrieval yet.
- No reranker.
- No hex/address normalization.
- No automated grading.
- Manual eval slices are curated fixtures only.

## 5. Recommended Phase 3 Direction

`P3` should focus on improving table-heavy retrieval.

First likely experiments:

1. Table-aware row-group chunking.
2. Parent-child retrieval.
3. Hex/address normalization.
4. BM25-weighted fusion or reranking.
