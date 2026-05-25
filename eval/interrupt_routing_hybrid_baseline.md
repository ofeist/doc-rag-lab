# Interrupt Routing Hybrid Retrieval Baseline

Focused index:

```text
PDF: docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
pages: 1364-1397
topic: Interrupt Router, Service Request Nodes, SRC registers, TOS routing, ICU arbitration
chunks: 36
embedding model: BAAI/bge-small-en-v1.5
vector store: Chroma
BM25 source: data/chunks.jsonl
fusion: Reciprocal Rank Fusion, k=60
```

Commands:

```bash
python scripts/extract_pages.py docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 1364-1397 \
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

python scripts/eval_retrieval.py --mode vector --eval eval/interrupt_routing_eval.json
python scripts/eval_retrieval.py --mode bm25 --eval eval/interrupt_routing_eval.json
python scripts/eval_retrieval.py --mode hybrid --eval eval/interrupt_routing_eval.json
```

Results:

```text
vector:
hit@1: 8/10 = 80.00%
hit@3: 9/10 = 90.00%
hit@5: 9/10 = 90.00%

bm25:
hit@1: 6/10 = 60.00%
hit@3: 9/10 = 90.00%
hit@5: 9/10 = 90.00%

hybrid:
hit@1: 7/10 = 70.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%
```

Comparison with previous slices:

```text
Boot/BMHD hybrid:          hit@1 70%, hit@3 100%, hit@5 100%
DMA/cache hybrid:          hit@1 90%, hit@3 100%, hit@5 100%
Interrupt routing hybrid:  hit@1 70%, hit@3 100%, hit@5 100%
```

Interpretation:

```text
Hybrid retrieval generalizes to a third focused technical slice and preserves perfect hit@3.
Vector retrieval is stronger than BM25 on hit@1 for this slice because several interrupt-routing pages repeat the same generic terms.
BM25 still helps recover exact register/address-space lookups, especially for INT/SRC register address space questions.
This is enough retrieval stability to start testing grounded answer generation, while keeping eval as the regression gate.
```
