- interrupt routing: PASS
- DMA/cache: PASS
- Boot/BMHD: PASS after higher max-tokens rerun
- model: gpt-5.4-nano
- retrieval mode: hybrid
- common settings: top_k=3, candidate_k=8, rrf_k=60
- known issue: run_answer_eval.py appends JSONL; should add overwrite/fail-if-exists behavior
- known issue: long procedural answers may need higher max-tokens

