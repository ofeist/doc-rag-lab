# Minimal Technical PDF RAG PoC

This project is a minimal, pragmatic RAG PoC for technical PDF documents.

The goal of the first version is not to build a “perfect AI assistant”, but to get this working loop:

> PDF → text → chunks → embeddings → semantic search → first RAG answer with source/page references

For now, this is CLI-first. No UI, no FastAPI, no Docker.

---

## 1. Project structure

Recommended root structure:

```text
test-rag/
  docs/
    infineon-manual.pdf

  data/
    raw_pages.jsonl
    chunks.jsonl

  vector_db/

  scripts/
    extract_pages.py
    chunk_pages.py
    embed_chunks.py
    search_chunks.py
    ask.py

  requirements.txt
  README.md
```

`docs/` contains the original PDF documents.  
`data/` contains intermediate outputs.  
`vector_db/` contains the local Chroma database.  
`scripts/` contains the CLI scripts.

---

## 2. Setup

From the project root folder:

```bash
python -m venv .venv
```

Activate in Git Bash / Linux / macOS:

```bash
source .venv/Scripts/activate
```

If you are on Linux/macOS and the venv uses the standard layout:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Important: `requirements.txt` should use pinned versions, for example `package==x.y.z`.

---

## 3. Add a PDF document

Put the technical PDF into `docs/`.

Example:

```text
docs/infineon-manual.pdf
```

The file name can be your own, but keep it stable and meaningful because it is later used as source metadata.

---

## 4. Step 1 — PDF extraction

Goal: extract text from the PDF into page-by-page JSONL format.

Run:

```bash
python scripts/extract_pages.py --pdf docs/infineon-manual.pdf --output data/raw_pages.jsonl
```

Expected output:

```text
data/raw_pages.jsonl
```

Each line represents one PDF page, roughly like this:

```json
{"page": 1, "text": "..."}
```

Quick check:

```bash
head -n 3 data/raw_pages.jsonl
```

On Windows without `head`, open the file in an editor or use PowerShell:

```powershell
Get-Content data/raw_pages.jsonl -TotalCount 3
```

Step 1 is OK if:

- `data/raw_pages.jsonl` exists;
- you can see text extracted from the PDF;
- pages have page numbers;
- the text is at least partially readable.

Note: tables in technical PDFs may look messy. For this PoC, that is acceptable.

---

## 5. Step 2 — Chunking

Goal: convert large page texts into smaller chunks suitable for embeddings/retrieval.

Run:

```bash
python scripts/chunk_pages.py \
  --input data/raw_pages.jsonl \
  --output data/chunks.jsonl \
  --source docs/infineon-manual.pdf
```

Expected output:

```text
data/chunks.jsonl
```

Each chunk should include metadata, for example:

```json
{
  "source": "docs/infineon-manual.pdf",
  "page_start": 10,
  "page_end": 10,
  "page_chunk_index": 0,
  "chunk_index": 13,
  "token_count": 800,
  "text": "..."
}
```

Quick check:

```bash
head -n 5 data/chunks.jsonl
```

Most important checks:

- `page_start` must not be `null`;
- `page_end` must not be `null`;
- `text` must not be empty;
- `token_count` should usually stay below the chunk limit;
- one page can have multiple chunks — that is normal.

Step 2 is OK if you can open `chunks.jsonl` and see that every chunk has source metadata, page metadata, and text.

---

## 6. Step 3 — Embeddings + ChromaDB search

Goal: convert chunks into embeddings and store them in a local vector database.

Build embeddings / vector DB:

```bash
python scripts/embed_chunks.py \
  --input data/chunks.jsonl \
  --persist-dir vector_db \
  --collection infineon_manual
```

Expected output:

```text
vector_db/
```

Semantic search test:

```bash
python scripts/search_chunks.py \
  --persist-dir vector_db \
  --collection infineon_manual \
  --query "pin configuration analog input"
```

Other useful test queries:

```bash
python scripts/search_chunks.py --persist-dir vector_db --collection infineon_manual --query "reset behavior"
```

```bash
python scripts/search_chunks.py --persist-dir vector_db --collection infineon_manual --query "interrupt priority"
```

```bash
python scripts/search_chunks.py --persist-dir vector_db --collection infineon_manual --query "memory protection"
```

Step 3 is OK if search returns:

- relevant chunks;
- page/source metadata;
- a short text preview;
- results that at least partially make sense for the query.

If search returns nonsense, the problem is retrieval, not the LLM.

---

## 7. Step 4 — First RAG answer

Goal: connect retrieval and the LLM.

Flow:

```text
question
  ↓
search top chunks from Chroma
  ↓
build context
  ↓
LLM answers only from context
  ↓
answer + sources
```

Before running this step, you need LLM configuration.

If you use an API-based LLM:

```bash
export OPENAI_API_KEY="your-key-here"
```

Do not commit `.env`, API keys, or secrets.

Example run:

```bash
python scripts/ask.py \
  --persist-dir vector_db \
  --collection infineon_manual \
  --query "What does the document say about interrupt priority?"
```

Expected output should include at least:

```text
Answer:
...

Sources:
- docs/infineon-manual.pdf, page X
- docs/infineon-manual.pdf, page Y

Confidence:
...

Missing / limitations:
...
```

Step 4 is OK if:

- the answer uses the retrieved context;
- it lists source/page references;
- it does not invent information when there is not enough context;
- it clearly says when something was not found.

---

## 8. Full rebuild flow

When you change the PDF or want to rebuild from scratch:

```bash
rm -rf data/raw_pages.jsonl data/chunks.jsonl vector_db
```

Then run again:

```bash
python scripts/extract_pages.py --pdf docs/infineon-manual.pdf --output data/raw_pages.jsonl
```

```bash
python scripts/chunk_pages.py \
  --input data/raw_pages.jsonl \
  --output data/chunks.jsonl \
  --source docs/infineon-manual.pdf
```

```bash
python scripts/embed_chunks.py \
  --input data/chunks.jsonl \
  --persist-dir vector_db \
  --collection infineon_manual
```

```bash
python scripts/search_chunks.py \
  --persist-dir vector_db \
  --collection infineon_manual \
  --query "your test question"
```

```bash
python scripts/ask.py \
  --persist-dir vector_db \
  --collection infineon_manual \
  --query "your RAG question"
```

---

## 9. Current limitations

This PoC does not yet properly solve:

- tables;
- register bitfields;
- figures/captions;
- section-aware chunking;
- hybrid search;
- reranking;
- eval set;
- multi-document reasoning;
- internal debug notes.

This is intentional. First, we build the working loop.

---

## 10. Next planned step

The next major step after Step 4:

> Step 5 — evaluation set

Minimum version:

- 20–30 questions;
- expected source/page/section;
- actual retrieval result;
- pass/fail;
- short note on what failed.

Without evaluation, we have a demo.  
With evaluation, we have a tool that we can improve.
