# DMA/Cache Hybrid Retrieval Baseline

Focused index:

```text
PDF: docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
pages: 257-259, 307-314, 1435-1455, 1483-1488
topic: PMA cacheability, PMI/PCACHE coherency, DMA requests, DMA address generation
chunks: 43
embedding model: BAAI/bge-small-en-v1.5
vector store: Chroma
BM25 source: data/chunks.jsonl
fusion: Reciprocal Rank Fusion, k=60
```

Commands:

```bash
python scripts/extract_pages.py docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 257-259,307-314,1435-1455,1483-1488 \
  --out data/raw_pages.jsonl \
  --no-preview

python scripts/chunk_pages.py \
  --input data/raw_pages.jsonl \
  --output data/chunks.jsonl \
  --source docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf

python scripts/embed_chunks.py \
  --chunks data/chunks.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset

python scripts/eval_retrieval.py --mode vector --eval eval/dma_cache_eval.json
python scripts/eval_retrieval.py --mode bm25 --eval eval/dma_cache_eval.json
python scripts/eval_retrieval.py --mode hybrid --eval eval/dma_cache_eval.json
```

Results:

```text
vector:
hit@1: 9/10 = 90.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%

bm25:
hit@1: 8/10 = 80.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%

hybrid:
hit@1: 9/10 = 90.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%
```

Comparison with Boot/BMHD:

```text
Boot/BMHD vector: hit@1 60%, hit@3 70%, hit@5 90%
Boot/BMHD bm25:   hit@1 60%, hit@3 100%, hit@5 100%
Boot/BMHD hybrid: hit@1 70%, hit@3 100%, hit@5 100%

DMA/cache vector: hit@1 90%, hit@3 100%, hit@5 100%
DMA/cache bm25:   hit@1 80%, hit@3 100%, hit@5 100%
DMA/cache hybrid: hit@1 90%, hit@3 100%, hit@5 100%
```

Interpretation:

```text
Hybrid retrieval generalizes to a second focused technical slice.
The DMA/cache slice is easier for vector retrieval than Boot/BMHD, likely because key terms are repeated in prose and register descriptions.
BM25 still provides useful exact-token coverage for register and bit names.
The next eval slice should be interrupt routing before moving to LLM answer generation.
```
