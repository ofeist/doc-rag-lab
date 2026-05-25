# RAG Step 4 — First RAG Answer with Sources

## Goal

In Step 3 we proved that semantic search works:

```text
chunks.jsonl → embeddings → ChromaDB → top matching chunks
```

In Step 4 we add the first LLM layer:

```text
user question
  ↓
retrieve top chunks from Chroma
  ↓
build strict prompt
  ↓
send context + question to LLM
  ↓
print answer + sources
```

This is the first real “RAG answer”.

The goal is **not** to make it perfect.

The goal is:

> Ask one question and get a short answer grounded in retrieved document chunks, with source pages.

---

## What this step produces

New script:

```text
scripts/ask_chunks.py
```

It will use the ChromaDB created in Step 3 and call an OpenAI-compatible LLM endpoint.

Example output:

```text
Question:
What does the document say about pin configuration?

Answer:
The document describes pin configuration in the context of ...

Sources:
- source=docs/infineon-manual.pdf page=12 chunk=17
- source=docs/infineon-manual.pdf page=13 chunk=18

Retrieval debug:
1. distance=0.42 page=12 chunk=17
2. distance=0.48 page=13 chunk=18
```

---

## Important principle

The LLM is **not allowed to answer from memory**.

It should answer only from retrieved chunks.

If the retrieved context does not contain the answer, the expected answer is:

```text
Not found in the provided documentation context.
```

This is important because technical RAG must be boring and honest before it becomes clever.

---

## Updated project structure

Expected structure after Step 4:

```text
test-rag/
  docs/
    infineon-manual.pdf

  data/
    raw_pages.jsonl
    chunks.jsonl
    chroma/

  scripts/
    extract_pages.py
    chunk_pages.py
    embed_chunks.py
    search_chunks.py
    ask_chunks.py

  requirements.txt
```

---

## Update `requirements.txt`

Use pinned versions.

```txt
pymupdf==1.24.14
tiktoken==0.8.0
chromadb==0.5.23
sentence-transformers==3.3.1
requests==2.32.3
```

Install/update:

```bash
pip install -r requirements.txt
```

Note: if your existing Step 3 used slightly different package versions and everything works, do not randomly upgrade. For a PoC, stability is more important than newest versions.

---

## LLM endpoint options

This script expects an **OpenAI-compatible chat completion endpoint**.

That can be:

- local Ollama OpenAI-compatible endpoint
- local vLLM OpenAI-compatible endpoint
- LM Studio local server
- OpenAI API
- any compatible internal endpoint

For local PoC, the easiest option is often Ollama or LM Studio.

Example with Ollama:

```bash
export LLM_BASE_URL="http://localhost:11434/v1"
export LLM_MODEL="qwen2.5:7b"
```

On Windows PowerShell:

```powershell
$env:LLM_BASE_URL="http://localhost:11434/v1"
$env:LLM_MODEL="qwen2.5:7b"
```

For OpenAI API style usage:

```bash
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_API_KEY="your-api-key"
export LLM_MODEL="gpt-4o-mini"
```

For local endpoints without authentication, `LLM_API_KEY` can be omitted.

---

## Critical requirement

Use the **same embedding model** as in Step 3.

If Step 3 used:

```text
BAAI/bge-small-en-v1.5
```

then Step 4 must use the same.

If Step 3 used another model, pass it with:

```bash
--embedding-model "your-model-name"
```

Otherwise search quality can degrade.

---

## Script: `scripts/ask_chunks.py`

Create this file:

```python
#!/usr/bin/env python3

import argparse
import os
import sys
from typing import Any

import chromadb
import requests
from chromadb.utils import embedding_functions


DEFAULT_CHROMA_DIR = "data/chroma"
DEFAULT_COLLECTION = "manual_chunks"
DEFAULT_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

DEFAULT_LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
DEFAULT_LLM_API_KEY = os.getenv("LLM_API_KEY", "")


SYSTEM_PROMPT = """You are a technical documentation assistant.

Rules:
- Use ONLY the provided documentation context.
- Do NOT answer from general knowledge.
- If the answer is not present in the context, say: "Not found in the provided documentation context."
- Keep the answer concise and technical.
- Always mention which sources support the answer.
- If the context is weak or incomplete, say so.
"""


def build_context(results: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    context_blocks = []
    source_debug = []

    for idx, (doc, meta, distance) in enumerate(zip(documents, metadatas, distances), start=1):
        source = meta.get("source", "unknown")
        page_start = meta.get("page_start", "unknown")
        page_end = meta.get("page_end", page_start)
        chunk_index = meta.get("chunk_index", "unknown")

        source_label = (
            f"S{idx}: source={source}, "
            f"page_start={page_start}, page_end={page_end}, chunk_index={chunk_index}"
        )

        context_blocks.append(
            f"[{source_label}]\n"
            f"{doc}\n"
        )

        source_debug.append(
            {
                "rank": idx,
                "source": source,
                "page_start": page_start,
                "page_end": page_end,
                "chunk_index": chunk_index,
                "distance": distance,
            }
        )

    return "\n---\n".join(context_blocks), source_debug


def call_llm(
    *,
    base_url: str,
    model: str,
    api_key: str,
    question: str,
    context: str,
    timeout_seconds: int,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"

    headers = {
        "Content-Type": "application/json",
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    user_prompt = f"""Documentation context:

{context}

Question:
{question}

Answer format:

Answer:
...

Sources:
- ...

Limitations:
...
"""

    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=timeout_seconds,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"LLM request failed: HTTP {response.status_code}\n{response.text}"
        )

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected LLM response format:\n{data}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ask a question using retrieved ChromaDB chunks and an OpenAI-compatible LLM."
    )

    parser.add_argument(
        "question",
        help="Question to ask against the indexed documentation.",
    )

    parser.add_argument(
        "--chroma-dir",
        default=DEFAULT_CHROMA_DIR,
        help=f"Path to Chroma persistent DB. Default: {DEFAULT_CHROMA_DIR}",
    )

    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help=f"Chroma collection name. Default: {DEFAULT_COLLECTION}",
    )

    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help=f"SentenceTransformers embedding model. Default: {DEFAULT_EMBEDDING_MODEL}",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve. Default: 5",
    )

    parser.add_argument(
        "--llm-base-url",
        default=DEFAULT_LLM_BASE_URL,
        help=f"OpenAI-compatible base URL. Default: {DEFAULT_LLM_BASE_URL}",
    )

    parser.add_argument(
        "--llm-model",
        default=DEFAULT_LLM_MODEL,
        help=f"LLM model name. Default: {DEFAULT_LLM_MODEL}",
    )

    parser.add_argument(
        "--llm-api-key",
        default=DEFAULT_LLM_API_KEY,
        help="LLM API key. Can also be set via LLM_API_KEY.",
    )

    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="LLM request timeout. Default: 120",
    )

    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Print retrieved context before asking the LLM.",
    )

    args = parser.parse_args()

    if not os.path.isdir(args.chroma_dir):
        print(f"ERROR: Chroma directory not found: {args.chroma_dir}", file=sys.stderr)
        print("Run Step 3 embed script first.", file=sys.stderr)
        return 1

    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=args.embedding_model
    )

    client = chromadb.PersistentClient(path=args.chroma_dir)

    try:
        collection = client.get_collection(
            name=args.collection,
            embedding_function=embedding_fn,
        )
    except Exception as exc:
        print(f"ERROR: Could not open Chroma collection '{args.collection}'.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    results = collection.query(
        query_texts=[args.question],
        n_results=args.top_k,
        include=["documents", "metadatas", "distances"],
    )

    context, source_debug = build_context(results)

    print("\nQuestion:")
    print(args.question)

    print("\nRetrieved sources:")
    for item in source_debug:
        print(
            f"{item['rank']}. distance={item['distance']:.4f} "
            f"source={item['source']} "
            f"page={item['page_start']}-{item['page_end']} "
            f"chunk={item['chunk_index']}"
        )

    if args.show_context:
        print("\nRetrieved context:")
        print(context)

    try:
        answer = call_llm(
            base_url=args.llm_base_url,
            model=args.llm_model,
            api_key=args.llm_api_key,
            question=args.question,
            context=context,
            timeout_seconds=args.timeout_seconds,
        )
    except Exception as exc:
        print("\nERROR while calling LLM:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    print("\nAnswer:")
    print(answer)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Run Step 4

Basic run:

```bash
python scripts/ask_chunks.py "What does the document say about pin configuration?"
```

With explicit settings:

```bash
python scripts/ask_chunks.py "What does the document say about pin configuration?" \
  --chroma-dir data/chroma \
  --collection manual_chunks \
  --embedding-model BAAI/bge-small-en-v1.5 \
  --top-k 5
```

Show retrieved context too:

```bash
python scripts/ask_chunks.py "What does the document say about pin configuration?" --show-context
```

---

## First good test questions

Use questions where you already roughly know the document contains the answer.

Examples:

```bash
python scripts/ask_chunks.py "What is the purpose of the pin configuration table?"
```

```bash
python scripts/ask_chunks.py "Which information is provided for electrical characteristics?"
```

```bash
python scripts/ask_chunks.py "What does the document say about package pin assignment?"
```

Use your actual document terms. If the document is about an Infineon chip datasheet, start with terms you see in the first 30 pages:

- package
- pin assignment
- electrical characteristics
- absolute maximum ratings
- ADC
- reset
- clock
- memory
- peripheral

---

## How to judge the result

Good result:

```text
Retrieved sources:
1. page=24-24
2. page=25-25
3. page=26-26

Answer:
The document describes package pin assignment as...
Sources:
- S1, page 24
- S2, page 25
```

Bad result:

```text
Retrieved sources:
1. unrelated page
2. unrelated page

Answer:
Generic explanation without matching document evidence.
```

If retrieval is bad, do not tune the LLM yet.

Fix retrieval first.

---

## Important distinction

Step 4 has two separate parts:

1. **retrieval quality**
2. **LLM answer quality**

If retrieved chunks are wrong, the LLM cannot save the answer.

Debug order:

```text
wrong answer
  ↓
check retrieved sources
  ↓
if sources are wrong: Step 3/retrieval issue
  ↓
if sources are right but answer is bad: prompt/model issue
```

---

## Common problems

### Problem 1 — LLM endpoint not running

Symptom:

```text
Connection refused
```

Fix:

Start your local model server, for example Ollama/LM Studio/vLLM.

---

### Problem 2 — wrong model name

Symptom:

```text
model not found
```

Fix:

Set the model name to whatever your local server exposes.

Example:

```bash
export LLM_MODEL="qwen2.5:7b"
```

---

### Problem 3 — answer is generic

Usually retrieval or prompt issue.

Run:

```bash
python scripts/ask_chunks.py "your question" --show-context
```

If the context does not contain the answer, the problem is retrieval.

---

### Problem 4 — sources are not useful

Try:

```bash
--top-k 8
```

If that helps, keep it.

If it does not help, we need better retrieval in a later step:

- better chunking
- keyword search
- hybrid search
- reranker

Not now.

---

## Definition of Done

Step 4 is done when:

- `scripts/ask_chunks.py` runs without error
- it retrieves top chunks from Chroma
- it calls the LLM
- answer contains source references
- at least 3 manually tested questions produce useful answers
- for at least 1 question with weak context, the answer admits uncertainty or says not found

---

## What we are not solving yet

Not yet:

- perfect citations
- section-aware chunking
- table-aware extraction
- hybrid BM25 + vector search
- reranking
- automated eval
- UI
- FastAPI
- multi-document RAG

Those come later.

For now the target is simple:

> Ask a question and get a grounded answer with source pages.

---

## Next step after this

Step 5 should be:

> Create a small manual evaluation set.

That means 10–20 questions where we record:

- question
- expected page/section
- retrieved pages
- answer quality
- pass/fail

That is how we stop guessing and start measuring.
