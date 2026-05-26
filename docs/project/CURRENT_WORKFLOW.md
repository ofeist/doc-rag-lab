# Current RAG Lab Workflow

This repository is a small technical-documentation RAG lab. The current workflow is
CLI-first and intentionally explicit:

```text
PDF -> raw pages -> chunks -> ChromaDB -> retrieval eval -> answer eval -> manual grading
```

## 1. Full-Document Ingest

Full-document ingest is the default/normal mode.

```bash
python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --doc-id aurix_tc3xx_part1 \
  --collection technical_docs \
  --reset
```

When `--page-ranges` is omitted, the full PDF is extracted, chunked, and embedded.

Default generated outputs:

```text
data/raw_pages.jsonl
data/chunks.jsonl
vector_db/chroma
```

Use `--reset` when the Chroma DB should be rebuilt from the current chunks.

## 2. Focused Eval Ingest

Focused ingest is for controlled eval/debug slices. It uses the same pipeline, but limits
the extracted pages:

```bash
python scripts/ingest_document.py \
  --pdf docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 115-126 \
  --doc-id boot_bmhd \
  --collection technical_docs \
  --reset
```

Focused slices are useful when testing retrieval quality because the expected context is
small and inspectable. They are not the main production ingest model.

## 3. Retrieval Eval

Retrieval eval checks whether the correct pages appear in the top retrieved candidates.

```bash
python scripts/eval_retrieval.py \
  --mode hybrid \
  --eval eval/boot_bmhd_eval.json
```

Supported modes:

```text
vector
bm25
hybrid
bm25_first_hybrid
```

Hybrid retrieval is the current default baseline because it combines semantic search with
keyword matching through Reciprocal Rank Fusion.

`bm25_first_hybrid` is experimental and currently exists to test table-heavy slices where
RRF hybrid performs worse than BM25.

## 4. Answer Batch Eval

Answer batch eval runs grounded answer generation over an eval file and writes JSONL
records.

```bash
python scripts/run_answer_eval.py \
  --eval eval/boot_bmhd_eval.json \
  --mode hybrid \
  --top-k 3 \
  --candidate-k 8 \
  --model gpt-5.4-nano \
  --base-url https://api.openai.com/v1 \
  --max-tokens 900 \
  --output-jsonl eval/rag_answer_boot_bmhd_gpt54nano_batch.jsonl \
  --overwrite
```

JSONL output is protected by default. Use:

```text
--overwrite   repeatable batch runs
--append      intentional multi-run logs
```

Do not use answer batch eval until retrieval eval shows that the right context is being
retrieved.

## 5. Manual Grading

Manual grading is still human-reviewed.

Use:

```text
eval/rag_answer_manual_grading_template.md
```

Write slice-specific grading reports next to the batch JSONL output, for example:

```text
eval/rag_answer_boot_bmhd_gpt54nano_batch_grading.md
```

Grade for groundedness, citation quality, correctness, and whether the answer refuses
when context is insufficient.

## 6. Known Eval Slices

Known focused eval/debug slices are recorded in:

```text
configs/slices.json
```

Current slices:

| Slice | Page ranges | Eval file | Notes |
| --- | --- | --- | --- |
| `boot_bmhd` | `115-126` | `eval/boot_bmhd_eval.json` | Boot Mode Header and startup firmware flow. Uses `default_max_tokens: 900`. |
| `dma_cache` | `257-259,307-314,1435-1455,1483-1488` | `eval/dma_cache_eval.json` | DMA/cache coherency, cacheability, and LMU-related questions. |
| `interrupt_routing` | `1364-1397` | `eval/interrupt_routing_eval.json` | Interrupt Router, SRC, TOS routing, service request terminology. |
| `memory_map` | `90-102` | `eval/memory_map_eval.json` | Table-heavy MEMMAP address ranges, segment mappings, and SOTA alternate PFLASH mappings. |

The slice manifest is a curated fixture registry for eval/debug work. It is not yet an
orchestrator.

Per-slice recommended settings are recorded in the manifest because one global retrieval
default is not ideal for every content type:

| Slice | Chunk tokens | Overlap tokens | Retrieval mode |
| --- | ---: | ---: | --- |
| `boot_bmhd` | 800 | 120 | `hybrid` |
| `dma_cache` | 800 | 120 | `hybrid` |
| `interrupt_routing` | 800 | 120 | `hybrid` |
| `memory_map` | 300 | 60 | `bm25_first_hybrid` |

Validate it with:

```bash
python scripts/validate_slices_config.py
```

### Table-Heavy Eval Slice

The `memory_map` slice was added as a harder retrieval stress test. It covers pages
`90-102` of the AURIX manual and contains 10 retrieval eval questions.

It was chosen because the section is dense with address-map tables, repeated numeric
address ranges, repeated Program Flash bank names, and alternate SOTA mappings. This is
harder than prose-heavy sections and exposes table/chunking weaknesses.

Initial retrieval results:

```text
vector: hit@1 20%, hit@3 40%, hit@5 40%
bm25:   hit@1 40%, hit@3 60%, hit@5 70%
hybrid: hit@1 40%, hit@3 40%, hit@5 40%
bm25_first_hybrid: hit@1 40%, hit@3 60%, hit@5 70%
```

The low hybrid result is intentional signal, not a hidden failure. It suggests that the
current page-local fixed chunking and RRF settings are weak for dense table lookups.
The `bm25_first_hybrid` experiment avoids the RRF regression but does not beat BM25.
The current recommended `memory_map` settings are 300 token chunks, 60 token overlap, and
`bm25_first_hybrid` retrieval.

## 7. Known Limitations

- Ingest is still PyMuPDF text extraction only; tables and diagrams are not handled as
  first-class structured objects.
- Chunking is page-local fixed token chunking; there is no parent-child retrieval yet.
- Dense table-heavy address maps can retrieve poorly even when the target text was
  extracted; `memory_map` is the current stress fixture for this.
- The slice manifest is not yet wired into a runner.
- Retrieval eval is focused on expected pages, not complete answer correctness.
- Answer eval requires a live OpenAI-compatible model endpoint and manual grading.
- Full-document ingest can be larger and slower; focused slices remain better for quick
  retrieval debugging.
- Chroma is local and rebuilt manually with `--reset`; there is no multi-document lifecycle
  management yet.
