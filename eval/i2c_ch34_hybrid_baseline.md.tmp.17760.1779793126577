# I2C Ch34 Hybrid Retrieval Baseline

Run metadata:
```
eval file:          eval/i2c_ch34_eval.json
chunks file:        data/chunks_i2c_ch34.jsonl
embedding model:    BAAI/bge-small-en-v1.5
collection:         technical_docs
questions:          10
date:               2026-05-26
```

## BM25

```
mode: bm25, top-k: 5
hit@1: 3/10 = 30.00%
hit@3: 7/10 = 70.00%
hit@5: 10/10 = 100.00%

FAIL (hit@3 miss): i2c-005 (SDA/SCL), i2c-007 (interrupts), i2c-008 (clock/bitrate)
```

## Hybrid (RRF)

```
mode: hybrid, top-k: 5, candidate-k: 12, rrf-k: 60
hit@1: 9/10 = 90.00%
hit@3: 10/10 = 100.00%
hit@5: 10/10 = 100.00%
```

## Cross-Slice Comparison

| Slice           | Mode    | hit@1 | hit@3 | hit@5 |
|-----------------|---------|-------|-------|-------|
| Boot/BMHD       | hybrid  | 70%   | 100%  | 100%  |
| DMA/cache       | hybrid  | --    | --    | --    |
| Interrupt       | hybrid  | --    | --    | --    |
| Memory Map      | bm25_tb | 80%   | 100%  | 100%  |
| I2C Ch34        | bm25    | 30%   | 70%   | 100%  |
| I2C Ch34        | hybrid  | 90%   | 100%  | 100%  |

## Notes

- BM25 alone struggles with SDA/SCL (i2c-005), interrupts (i2c-007), clock/bitrate (i2c-008)
- Hybrid resolves all three — vector component bridges the keyword gap
- hit@1 = 90% (only i2c-007 misses at rank-1, hits at rank-2)
- 89 chunks, 84 pages, 800/120 chunking — solid baseline
