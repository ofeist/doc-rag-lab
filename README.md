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

Focused extraction from multiple page ranges:

```bash
python scripts/extract_pages.py docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf \
  --page-ranges 257-259,307-314,1435-1455,1483-1488 \
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

Compare retrieval modes:

```bash
python scripts/eval_retrieval.py --mode vector --eval eval/boot_bmhd_eval.json
python scripts/eval_retrieval.py --mode bm25 --eval eval/boot_bmhd_eval.json
python scripts/eval_retrieval.py --mode hybrid --eval eval/boot_bmhd_eval.json
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

## Focused DMA/Cache Index

The second focused retrieval slice checks whether the retrieval approach generalizes beyond Boot/BMHD:

```text
PDF pages 257-259: PMA data/code cacheability and coherency notes
PDF pages 307-314: PSPR/DSPR/PMI/PCACHE behavior and invalidation
PDF pages 1435-1455: DMA requests, reset, move operation, address generation
PDF pages 1483-1488: DMA checksum, DMARAM initialization, source/destination errors
```

Build the focused index:

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
```

Run the second mini retrieval eval:

```bash
python scripts/eval_retrieval.py --mode vector --eval eval/dma_cache_eval.json
python scripts/eval_retrieval.py --mode bm25 --eval eval/dma_cache_eval.json
python scripts/eval_retrieval.py --mode hybrid --eval eval/dma_cache_eval.json
```

Current baseline:

```text
vector: hit@1 90%, hit@3 100%, hit@5 100%
bm25:   hit@1 80%, hit@3 100%, hit@5 100%
hybrid: hit@1 90%, hit@3 100%, hit@5 100%
```

Detailed notes are in `eval/dma_cache_hybrid_baseline.md`.

## Focused Interrupt Routing Index

The third focused retrieval slice checks interrupt routing and service request terminology:

```text
PDF pages 1364-1397
topic: Interrupt Router, SRN/SRC registers, TOS routing, ICU arbitration, GPSR/software interrupts
```

Build the focused index:

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
```

Run the third mini retrieval eval:

```bash
python scripts/eval_retrieval.py --mode vector --eval eval/interrupt_routing_eval.json
python scripts/eval_retrieval.py --mode bm25 --eval eval/interrupt_routing_eval.json
python scripts/eval_retrieval.py --mode hybrid --eval eval/interrupt_routing_eval.json
```

Current baseline:

```text
vector: hit@1 80%, hit@3 90%, hit@5 90%
bm25:   hit@1 60%, hit@3 90%, hit@5 90%
hybrid: hit@1 70%, hit@3 100%, hit@5 100%
```

Detailed notes are in `eval/interrupt_routing_hybrid_baseline.md`.

## First Grounded RAG Answer

This slice adds a strict citation-first answer layer on top of retrieval.
Retrieval eval remains the regression gate. If retrieval misses relevant pages, answer quality is not trustworthy.

Dry-run (no model call):

```bash
python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --dry-run
```

OpenAI API example:

```bash
export OPENAI_API_KEY="..."

python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --model gpt-5.5 \
  --base-url https://api.openai.com/v1
```

Another OpenAI-compatible endpoint example:

```bash
python scripts/ask_chunks.py \
  --question "What does the Interrupt Router module schedule?" \
  --mode hybrid \
  --top-k 5 \
  --model local-model \
  --base-url http://localhost:8000/v1 \
  --token-param max_tokens
```

Important:

```text
- Verify citations like [S1], [S2] are present in the answer.
- Treat no-citation answers as ungrounded.
- Keep running retrieval eval slices (boot/dma/interrupt) after retrieval changes.
- Use --token-param max_tokens for endpoints that do not support max_completion_tokens.
```

Batch answer eval:

```bash
python scripts/run_answer_eval.py \
  --eval eval/interrupt_routing_eval.json \
  --mode hybrid \
  --top-k 3 \
  --candidate-k 8 \
  --model gpt-5.4-nano \
  --base-url https://api.openai.com/v1 \
  --output-jsonl eval/rag_answer_interrupt_gpt54nano_batch.jsonl \
  --overwrite
```

JSONL output is protected by default: `run_answer_eval.py` refuses to write to an existing
output file unless the behavior is explicit. Use `--overwrite` for repeatable batch eval
runs, and use `--append` only when intentionally collecting multiple runs in the same
JSONL file.

Dry-run batch smoke test:

```bash
python scripts/run_answer_eval.py \
  --eval eval/interrupt_routing_eval.json \
  --limit 2 \
  --mode hybrid \
  --top-k 3 \
  --candidate-k 8 \
  --dry-run \
  --output-jsonl /tmp/rag_answer_batch_dry_run.jsonl \
  --overwrite
```

Manual grading stays human-reviewed for now. Use `eval/rag_answer_manual_grading_template.md` as the report format.

## Step 4: First RAG Answer

`scripts/ask_chunks.py` expects an OpenAI-compatible chat completion endpoint.

For local Ollama:

```bash
export LLM_BASE_URL="http://localhost:11434/v1"
export LLM_MODEL="qwen2.5:7b"
```

Ask a question:

```bash
python scripts/ask_chunks.py \
  --question "What does the document say about reset behavior?" \
  --db vector_db/chroma \
  --collection technical_docs
```

To debug retrieval context:

```bash
python scripts/ask_chunks.py \
  --question "What does the document say about reset behavior?" \
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
