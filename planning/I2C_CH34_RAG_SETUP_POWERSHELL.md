# AURIX TC3xx Part 2 — Chapter 34 I2C RAG Setup Notes

PowerShell-style notes for preparing a normal RAG slice for **AURIX TC3xx User Manual Part 2, Chapter 34 — I2C**.

For now:

```text
no table-aware builder
no table-specific chunking
no answer generation yet
no model/API env needed for extraction/chunking/embedding
```

---

## 1. Goal

Prepare a focused RAG slice for:

```text
AURIX TC3xx User Manual Part 2
Chapter 34 — I2C
```

Expected local PDF path:

```text
docs/infineon-aurix-tc3xx-part2-usermanual-en.pdf
```

You can manually inspect the PDF and find the actual page range for Chapter 34.

Use placeholders below:

```text
START-END
```

Replace with the real PDF/document page range for Chapter 34.

---

## 2. Do We Need to Extract the Whole PDF?

No.

You do **not** need to extract all pages from Part 2.

You can skip the full-document extraction step.

But you cannot completely skip `extract_pages.py`, because the current pipeline expects raw extracted page JSONL before chunking.

The minimal required extraction is only the Chapter 34 page range.

Pipeline:

```text
PDF chapter range
  -> extract_pages.py
  -> raw_pages_i2c_ch34.jsonl
  -> chunk_pages.py
  -> chunks_i2c_ch34.jsonl
  -> embed_chunks.py
  -> Chroma vector DB
```

---

## 3. Activate Virtual Environment in PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

If activation is blocked, run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 4. Extract Only Chapter 34

Replace `START-END` with the actual Chapter 34 page range.

```powershell
python scripts/extract_pages.py `
  --pdf docs/infineon-aurix-tc3xx-part2-usermanual-en.pdf `
  --page-ranges START-END `
  --output data/raw_pages_i2c_ch34.jsonl
```

This creates:

```text
data/raw_pages_i2c_ch34.jsonl
```

---

## 5. Chunk Chapter 34

Use normal page-aware chunking.

Recommended first settings:

```text
chunk_tokens: 800
overlap_tokens: 120
```

PowerShell:

```powershell
python scripts/chunk_pages.py `
  --input data/raw_pages_i2c_ch34.jsonl `
  --output data/chunks_i2c_ch34.jsonl `
  --chunk-tokens 800 `
  --overlap-tokens 120 `
  --doc-id aurix_tc3xx_part2_i2c_ch34
```

This creates:

```text
data/chunks_i2c_ch34.jsonl
```

---

## 6. Embed Chapter 34 Chunks

Embedding does **not** require an OpenAI API key.

It uses the local embedding model configured by the script, usually something like:

```text
BAAI/bge-small-en-v1.5
```

PowerShell:

```powershell
python scripts/embed_chunks.py `
  --chunks data/chunks_i2c_ch34.jsonl `
  --db vector_db/chroma `
  --collection technical_docs `
  --reset
```

Expected output should include a collection count.

---

## 7. Alternative: One-Step Ingest

If `scripts/ingest_document.py` is working in your repo, you can use the shorter command.

```powershell
python scripts/ingest_document.py `
  --pdf docs/infineon-aurix-tc3xx-part2-usermanual-en.pdf `
  --page-ranges START-END `
  --doc-id aurix_tc3xx_part2_i2c_ch34 `
  --collection technical_docs `
  --db vector_db/chroma `
  --reset `
  --chunk-tokens 800 `
  --overlap-tokens 120
```

This should internally run:

```text
extract -> chunk -> embed
```

If there is any CLI mismatch, use the manual three-step workflow above.

---

## 8. Add Slice Config

Add an entry to:

```text
configs/slices.json
```

Example:

```json
{
  "id": "i2c_ch34",
  "doc_id": "aurix_tc3xx_part2_i2c_ch34",
  "description": "AURIX TC3xx User Manual Part 2, Chapter 34 I2C",
  "source": "docs/infineon-aurix-tc3xx-part2-usermanual-en.pdf",
  "page_ranges": "START-END",
  "recommended": {
    "chunk_tokens": 800,
    "overlap_tokens": 120,
    "retrieval_mode": "hybrid",
    "top_k": 5,
    "candidate_k": 12
  },
  "notes": [
    "Normal prose/semi-structured peripheral chapter slice.",
    "Start with generic page-aware chunking.",
    "Do not use table-aware builder initially."
  ]
}
```

Validate config if the validator exists:

```powershell
python scripts/validate_slices_config.py
```

---

## 9. Minimal I2C Eval Draft

Create:

```text
eval/i2c_ch34_eval.json
```

Initial question draft:

```json
[
  {
    "id": "i2c-001",
    "question": "Which I2C operating modes are supported by the AURIX TC3xx I2C module?",
    "expected_pages": []
  },
  {
    "id": "i2c-002",
    "question": "Which I2C speed ranges are supported and what are their maximum data rates?",
    "expected_pages": []
  },
  {
    "id": "i2c-003",
    "question": "What address formats are supported by the I2C module?",
    "expected_pages": []
  },
  {
    "id": "i2c-004",
    "question": "What low-level I2C bus tasks can the module execute automatically?",
    "expected_pages": []
  },
  {
    "id": "i2c-005",
    "question": "How are SDA and SCL used and what is their idle state?",
    "expected_pages": []
  },
  {
    "id": "i2c-006",
    "question": "What role does the FIFO play in I2C transmit and receive data transfer?",
    "expected_pages": []
  },
  {
    "id": "i2c-007",
    "question": "Which interrupt categories or sources are described for the I2C module?",
    "expected_pages": []
  },
  {
    "id": "i2c-008",
    "question": "How is the I2C kernel clock and bit rate generated?",
    "expected_pages": []
  },
  {
    "id": "i2c-009",
    "question": "What does the documentation say about multi-master operation and arbitration?",
    "expected_pages": []
  },
  {
    "id": "i2c-010",
    "question": "What are the main CPU offload benefits of the I2C module?",
    "expected_pages": []
  }
]
```

Important:

```text
expected_pages must eventually be filled with real page numbers
```

If `eval_retrieval.py` requires expected pages, first use the questions for manual discovery, then update the file.

---

## 10. Retrieval Eval Commands

After `expected_pages` are filled, run vector/BM25/hybrid.

### Vector

```powershell
python scripts/eval_retrieval.py `
  --mode vector `
  --eval eval/i2c_ch34_eval.json `
  --db vector_db/chroma `
  --collection technical_docs `
  --chunks data/chunks_i2c_ch34.jsonl
```

### BM25

```powershell
python scripts/eval_retrieval.py `
  --mode bm25 `
  --eval eval/i2c_ch34_eval.json `
  --db vector_db/chroma `
  --collection technical_docs `
  --chunks data/chunks_i2c_ch34.jsonl
```

### Hybrid

```powershell
python scripts/eval_retrieval.py `
  --mode hybrid `
  --eval eval/i2c_ch34_eval.json `
  --db vector_db/chroma `
  --collection technical_docs `
  --chunks data/chunks_i2c_ch34.jsonl `
  --top-k 5 `
  --candidate-k 12
```

Initial target:

```text
hit@3 >= 80%
hit@5 >= 90%
```

If results are weak, try:

```text
chunk_tokens: 500
overlap_tokens: 80
candidate_k: 16
mode: bm25_first_hybrid
```

Do not start table-aware chunking unless this normal baseline fails clearly.

---

## 11. Do We Need Model or Env for This?

For this workflow:

```text
extract -> chunk -> embed -> retrieval eval
```

you do **not** need:

```text
OPENAI_API_KEY
OpenAI model
answer model
base-url
```

Embedding is local.

Model/env is needed only for:

```text
ask_chunks.py
run_answer_eval.py
```

That is the answer-generation stage.

---

## 12. What Is the Model Name?

Do not use:

```text
code
```

as a model name unless your endpoint explicitly lists a model with that exact name.

The model name must match what the OpenAI-compatible endpoint supports.

Examples from previous runs:

```text
gpt-5.4-nano
gpt-5.4-mini
gpt-5.5
```

For a local OpenAI-compatible server, check:

```powershell
curl http://localhost:8000/v1/models
```

or whatever base URL your local server uses.

Use the returned model ID in:

```text
--model ...
```

---

## 13. PowerShell Env for Answer Generation

Only needed later for answer generation.

Temporary env var for the current PowerShell window:

```powershell
$env:OPENAI_API_KEY = "sk-..."
```

Check it:

```powershell
$env:OPENAI_API_KEY
```

Permanent user-level env var:

```powershell
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-...", "User")
```

Then close and reopen PowerShell.

Check again:

```powershell
$env:OPENAI_API_KEY
```

---

## 14. PowerShell Answer Eval Example

Only run this after retrieval is good and `expected_pages` are set.

```powershell
python scripts/run_answer_eval.py `
  --eval eval/i2c_ch34_eval.json `
  --mode hybrid `
  --top-k 5 `
  --candidate-k 12 `
  --model gpt-5.4-nano `
  --base-url https://api.openai.com/v1 `
  --max-tokens 700 `
  --output-jsonl eval/rag_answer_i2c_ch34_gpt54nano_batch.jsonl
```

PowerShell multiline uses a backtick:

```text
`
```

not a Linux backslash:

```text
\\
```

---

## 15. Suggested Current Plan

Use this sequence:

```text
1. Manually find Chapter 34 page range in the PDF.
2. Extract only that page range.
3. Chunk with 800/120.
4. Embed chunks.
5. Create i2c_ch34 eval file.
6. Fill expected_pages.
7. Run vector/BM25/hybrid retrieval eval.
8. Only then decide whether chunk tuning is needed.
9. Do not worry about table-aware commits for this slice yet.
```

---

## 16. Git Notes

Generated files should usually not be committed:

```text
data/raw_pages_i2c_ch34.jsonl
data/chunks_i2c_ch34.jsonl
vector_db/
```

Commit source/config/eval/docs only, for example:

```text
configs/slices.json
eval/i2c_ch34_eval.json
docs/... if you create a report
```

Before commit:

```powershell
git status --short
git diff --check
```
