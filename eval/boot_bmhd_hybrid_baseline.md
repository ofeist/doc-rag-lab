# Boot/BMHD Hybrid Retrieval Baseline

Focused index:

```text
PDF: docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
pages: 115-126
chunks: 12
embedding model: BAAI/bge-small-en-v1.5
vector store: Chroma
BM25 source: data/chunks.jsonl
fusion: Reciprocal Rank Fusion, k=60
```

Commands:

```bash
python scripts/eval_retrieval.py --mode vector --eval eval/boot_bmhd_eval.json
python scripts/eval_retrieval.py --mode bm25 --eval eval/boot_bmhd_eval.json
python scripts/eval_retrieval.py --mode hybrid --eval eval/boot_bmhd_eval.json
```

Results:

```text
vector:
hit@1: 6/10 = 60.00%
hit@3: 7/10 = 70.00%
hit@5: 9/10 = 90.00%

bm25:
hit@1: 6/10 = 60.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%

hybrid:
hit@1: 7/10 = 70.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%
```

Interpretation:

```text
BM25 fixes the current hit@3 failures for this focused technical slice.
Hybrid retrieval improves hit@1 while preserving the BM25 hit@3 gain.
The failures were primarily ranking problems, not missing extraction problems.
Next retrieval work should keep hybrid as the default eval mode and test it on a second focused slice.
```
