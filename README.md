# Aurix RAG PoC

Minimal pragmatic RAG proof-of-concept for technical PDF documentation.

The first iteration is intentionally CLI-first:

```text
PDF -> raw_pages.jsonl -> chunks.jsonl -> ChromaDB -> search -> first RAG answer
```

No UI, Docker, OCR, hybrid search, reranker, or production platform yet.

## Structure

```text
docs/        original PDF files, ignored by git
data/        generated JSONL outputs, ignored by git
scripts/     CLI scripts
eval/        future evaluation questions
vector_db/   future local vector database, ignored by git
```

## Setup

Recommended on Linux/macOS/Git Bash:

```bash
./scripts/setup.sh
source .venv/bin/activate
```

Install the heavier Chroma/embedding dependencies later when you need search/RAG:

```bash
./scripts/setup.sh --rag
```

Recommended on Windows PowerShell:

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\Activate.ps1
```

PowerShell with RAG dependencies:

```powershell
.\scripts\setup.ps1 -Rag
```

Manual setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Git Bash for Windows, activation may be:

```bash
source .venv/Scripts/activate
```

## Step 1: PDF extraction

Put a PDF in `docs/`, for example:

```text
docs/sample.pdf
```

Run:

```bash
python scripts/extract_pages.py docs/sample.pdf
```

Optional smoke test with only the first 10 pages:

```bash
python scripts/extract_pages.py docs/sample.pdf --max-pages 10
```

Focused extraction from a specific page range:

```bash
python scripts/extract_pages.py docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-start 115 \
  --page-end 126 \
  --out data/raw_pages.jsonl
```

Output:

```text
data/raw_pages.jsonl
```

Each line is one PDF page with source, page metadata, character count, and text.

## Step 2: Chunking

Run:

```bash
python scripts/chunk_pages.py \
  --input data/raw_pages.jsonl \
  --output data/chunks.jsonl \
  --source docs/sample.pdf
```

Output:

```text
data/chunks.jsonl
```

This first chunker works page-by-page so every chunk has stable page metadata:

```json
{
  "chunk_id": "chunk-000000",
  "source": "docs/sample.pdf",
  "page_start": 1,
  "page_end": 1,
  "page_chunk_index": 0,
  "chunk_index": 0,
  "token_count": 800,
  "text": "..."
}
```

## Step 3: Embeddings and Semantic Search

Build the local Chroma database:

```bash
python scripts/embed_chunks.py \
  --chunks data/chunks.jsonl \
  --db vector_db/chroma \
  --collection technical_docs \
  --reset
```

Run a retrieval-only search:

```bash
python scripts/search_chunks.py "reset behavior" \
  --db vector_db/chroma \
  --collection technical_docs
```

This step is intentionally before the LLM. If search returns bad chunks, the LLM will only make the bad retrieval look nicer.

## Focused Boot/BMHD Index

For the first meaningful retrieval test, do not index the whole 2080-page PDF.
Use a small real-content slice from the AURIX startup chapter:

```text
PDF pages 115-126
topic: startup, Boot Mode Header (BMHD), Alternate Boot Mode (ABM), no-valid-BMHD handling
```

This range is small, fast to re-index, and includes prose, procedures, and Table 45.

Build the focused index:

```bash
python scripts/extract_pages.py docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-start 115 \
  --page-end 126 \
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
```

Quick metadata check:

```bash
rg '"page_start": null|"page_end": null' data/chunks.jsonl
```

The command should print nothing.

Retrieval quality checks:

```bash
python scripts/search_chunks.py "Boot Mode Header BMI HWCFG" --db vector_db/chroma --collection technical_docs
python scripts/search_chunks.py "PINDIS bit 0 mode selection by configuration pins" --db vector_db/chroma --collection technical_docs
python scripts/search_chunks.py "Alternate Boot Mode Header STADABM" --db vector_db/chroma --collection technical_docs
python scripts/search_chunks.py "what happens if no valid Boot Mode Header is found" --db vector_db/chroma --collection technical_docs
python scripts/search_chunks.py "RAM overwrite during startup CPU0 DSPR PSPR" --db vector_db/chroma --collection technical_docs
python scripts/search_chunks.py "CRC calculation ABMHD CHKSTART CHKEND" --db vector_db/chroma --collection technical_docs
```

Run the mini retrieval eval:

```bash
python scripts/eval_retrieval.py \
  --eval eval/boot_bmhd_eval.json \
  --db vector_db/chroma \
  --collection technical_docs
```

Inspect failing questions with snippets:

```bash
python scripts/eval_retrieval.py \
  --eval eval/boot_bmhd_eval.json \
  --db vector_db/chroma \
  --collection technical_docs \
  --debug-failures
```

Expected retrieval targets:

```text
BMHD / BMI / HWCFG / PINDIS: pages 117-119
ABM / STADABM / CHKSTART / CHKEND: pages 121-123
no valid BMHD handling: pages 123-126
RAM overwrite during startup: page 115
```

Table extraction check:

```bash
python scripts/search_chunks.py "PINDIS bit 0 mode selection by configuration pins" \
  --db vector_db/chroma \
  --collection technical_docs
```

For the current PyMuPDF baseline, a good result means page 117 appears in the top 3.
If it does not, plain text extraction is probably too weak for register/table lookup and we should benchmark PyMuPDF4LLM or Docling next.

## Step 4: First RAG Answer

`scripts/ask_chunks.py` expects an OpenAI-compatible chat completion endpoint.

For local Ollama:

```bash
export LLM_BASE_URL="http://localhost:11434/v1"
export LLM_MODEL="qwen2.5:7b"
```

Ask a question:

```bash
python scripts/ask_chunks.py "What does the document say about reset behavior?" \
  --db vector_db/chroma \
  --collection technical_docs
```

To debug retrieval context:

```bash
python scripts/ask_chunks.py "What does the document say about reset behavior?" \
  --db vector_db/chroma \
  --collection technical_docs \
  --show-context
```

## Definition of Done for Iteration 1

- `data/raw_pages.jsonl` exists after extraction.
- Extracted text is readable enough for a PoC.
- `data/chunks.jsonl` exists after chunking.
- Chunks have non-empty text.
- `page_start` and `page_end` are never `null`.
- `vector_db/chroma/` exists after embedding.
- `search_chunks.py` returns relevant chunks with source/page metadata.
- `ask_chunks.py` can produce a grounded answer with sources when a local LLM endpoint is available.

Next iteration starts with retrieval evaluation and parser benchmarking.
