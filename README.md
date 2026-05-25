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
