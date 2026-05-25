# Boot/BMHD Retrieval Baseline

Focused index:

```text
PDF: docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf
pages: 115-126
chunks: 12
embedding model: BAAI/bge-small-en-v1.5
vector store: Chroma
collection: technical_docs
```

Command:

```bash
python scripts/eval_retrieval.py \
  --eval eval/boot_bmhd_eval.json \
  --db vector_db/chroma \
  --collection technical_docs
```

Initial result:

```text
hit@1: 6/10 = 60.00%
hit@3: 7/10 = 70.00%
hit@5: 9/10 = 90.00%
```

Passes at hit@3:

```text
boot-001 RAM overwrite during startup CPU0 DSPR PSPR
boot-003 PINDIS bit 0 mode selection by configuration pins
boot-004 HWCFG values for startup mode selection
boot-006 HWCFG pins vs BMI boot mode selection
boot-007 Alternate Boot Mode Headers and STADABM
boot-008 ABMHD CRC over CHKSTART/CHKEND
boot-010 Startup firmware main flow
```

Failures at hit@3:

```text
boot-002 Boot Mode Header BMHD structure
boot-005 SSW processing of Boot Mode Headers and copies
boot-009 No valid Boot Mode Header handling
```

Interpretation:

```text
The focused PyMuPDF baseline is good enough to continue, especially for exact table-field queries.
It is not yet robust enough for broader procedural questions where flow diagrams and neighboring pages compete.
Before tuning the LLM, improve or compare retrieval using query wording, section-aware chunking, and parser alternatives.
```
