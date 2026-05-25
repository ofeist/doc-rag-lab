# RAG Step 2 — Chunking: `raw_pages.jsonl` → `chunks.jsonl`

## 0. Where we are now

You already completed Step 1:

```text
PDF
  ↓
scripts/extract_pages.py
  ↓
data/raw_pages.jsonl
```

That means we can extract page-level text from the technical PDF.

Now we do Step 2:

```text
data/raw_pages.jsonl
  ↓
scripts/chunk_pages.py
  ↓
data/chunks.jsonl
```

This is the first truly RAG-critical step.

---

## 1. Goal of Step 2

The goal is to transform large page-level text into smaller searchable chunks.

A vector database does not work well with entire PDFs or large pages. It works better with compact text blocks that contain enough context, but not too much noise.

For the first PoC, our target is:

```text
one chunk ≈ 600–900 tokens
chunk overlap ≈ 100–150 tokens
metadata included
output as JSONL
```

The output file should look like this:

```json
{
  "chunk_id": "chunk-000001",
  "source": "infineon_manual.pdf",
  "page_start": 12,
  "page_end": 13,
  "chunk_index": 1,
  "token_count": 785,
  "text": "..."
}
```

---

## 2. Why chunking matters

Bad chunking creates bad retrieval.

If chunks are too large:

- retrieval becomes noisy;
- the model receives too much irrelevant context;
- answers become generic;
- important details are buried.

If chunks are too small:

- context is missing;
- technical meaning gets cut apart;
- tables/register descriptions lose surrounding explanation.

For technical documentation, chunking is especially sensitive because documents contain:

- tables;
- registers;
- bitfields;
- warnings;
- notes;
- long descriptions;
- section headers;
- repeated page headers/footers.

For this PoC we accept imperfect extraction and imperfect chunking, but we keep the structure clean so that we can improve later.

---

## 3. Important pragmatic decision

We will **not** solve perfect table extraction now.

Your Infineon technical document has many tables. That is normal.

For now:

- we keep the extracted table text as-is;
- we preserve page metadata;
- we create reasonably sized chunks;
- later we can add table-aware extraction if needed.

This is the correct PoC attitude:

> Get a working retrieval loop first. Improve extraction/chunking only where evaluation shows problems.

---

## 4. Step 2 output

After this step, project structure should look like this:

```text
aurix-rag/
  docs/
    your_manual.pdf

  data/
    raw_pages.jsonl
    chunks.jsonl

  scripts/
    extract_pages.py
    chunk_pages.py

  requirements.txt
  README.md
```

---

## 5. Update `requirements.txt`

Add `tiktoken`:

```txt
pymupdf
tiktoken
```

Then install/update:

```bash
pip install -r requirements.txt
```

`tiktoken` is used only to estimate token size. This keeps chunks closer to what an LLM/embedding model will actually see.

---

## 6. Create `scripts/chunk_pages.py`

Create this file:

```text
scripts/chunk_pages.py
```

Paste the following script:

```python
#!/usr/bin/env python3
"""
Chunk extracted PDF pages into RAG-ready JSONL chunks.

Input:
  data/raw_pages.jsonl

Output:
  data/chunks.jsonl

Expected input line format:
  {"page": 1, "text": "..."}

Expected output line format:
  {
    "chunk_id": "chunk-000001",
    "source": "manual.pdf",
    "page_start": 1,
    "page_end": 2,
    "chunk_index": 1,
    "token_count": 800,
    "text": "..."
  }
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import tiktoken


DEFAULT_INPUT = "data/raw_pages.jsonl"
DEFAULT_OUTPUT = "data/chunks.jsonl"
DEFAULT_SOURCE = "unknown_source.pdf"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 120
DEFAULT_MIN_CHARS = 200


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read a JSONL file into a list of dicts."""
    rows: List[Dict[str, Any]] = []

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write rows as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_text(text: str) -> str:
    """
    Light text cleanup.

    This intentionally stays conservative.
    We do not want to destroy technical formatting too early.
    """
    if not text:
        return ""

    # Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive empty lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize repeated spaces/tabs, but keep newlines.
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def token_count(text: str, encoding: tiktoken.Encoding) -> int:
    return len(encoding.encode(text))


def build_page_blocks(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert raw pages into normalized page blocks.
    """
    blocks: List[Dict[str, Any]] = []

    for row in pages:
        page = row.get("page")
        text = normalize_text(row.get("text", ""))

        if page is None:
            continue

        if not text:
            continue

        blocks.append({"page": int(page), "text": text})

    return blocks


def chunk_pages(
    page_blocks: List[Dict[str, Any]],
    source: str,
    chunk_size: int,
    overlap: int,
    min_chars: int,
    encoding: tiktoken.Encoding,
) -> List[Dict[str, Any]]:
    """
    Create chunks from page blocks.

    Strategy:
    - concatenate page text progressively;
    - track page_start and page_end;
    - split by token size;
    - keep overlap between chunks.

    This is simple, robust, and good enough for the first PoC.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    # Build one large token stream, but keep page markers in text.
    # Page markers are useful later for citation/debugging.
    combined_parts: List[str] = []

    for block in page_blocks:
        combined_parts.append(f"\n\n[PAGE {block['page']}]\n{block['text']}")

    combined_text = "".join(combined_parts).strip()
    tokens = encoding.encode(combined_text)

    chunks: List[Dict[str, Any]] = []
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens).strip()

        if len(chunk_text) < min_chars:
            break

        page_numbers = extract_page_markers(chunk_text)
        page_start = min(page_numbers) if page_numbers else None
        page_end = max(page_numbers) if page_numbers else None

        chunk_index += 1
        chunks.append({
            "chunk_id": f"chunk-{chunk_index:06d}",
            "source": source,
            "page_start": page_start,
            "page_end": page_end,
            "chunk_index": chunk_index,
            "token_count": len(chunk_tokens),
            "text": chunk_text,
        })

        if end >= len(tokens):
            break

        start += chunk_size - overlap

    return chunks


def extract_page_markers(text: str) -> List[int]:
    """Extract page numbers from inserted [PAGE N] markers."""
    matches = re.findall(r"\[PAGE\s+(\d+)\]", text)
    return [int(m) for m in matches]


def print_summary(chunks: List[Dict[str, Any]]) -> None:
    if not chunks:
        print("No chunks created.")
        return

    token_counts = [c["token_count"] for c in chunks]

    print("Chunking complete")
    print(f"  chunks:      {len(chunks)}")
    print(f"  min tokens:  {min(token_counts)}")
    print(f"  max tokens:  {max(token_counts)}")
    print(f"  avg tokens:  {sum(token_counts) // len(token_counts)}")
    print()
    print("Sample chunk:")
    print("-" * 80)
    sample = chunks[0]
    print(f"chunk_id:    {sample['chunk_id']}")
    print(f"source:      {sample['source']}")
    print(f"page_start:  {sample['page_start']}")
    print(f"page_end:    {sample['page_end']}")
    print(f"tokens:      {sample['token_count']}")
    print()
    print(sample["text"][:1200])
    print("-" * 80)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunk extracted PDF pages for RAG.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input raw pages JSONL file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output chunks JSONL file")
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="Source document name")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Chunk size in tokens")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="Overlap in tokens")
    parser.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS, help="Minimum characters per chunk")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    encoding = tiktoken.get_encoding("cl100k_base")

    raw_pages = read_jsonl(input_path)
    page_blocks = build_page_blocks(raw_pages)

    chunks = chunk_pages(
        page_blocks=page_blocks,
        source=args.source,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        min_chars=args.min_chars,
        encoding=encoding,
    )

    write_jsonl(output_path, chunks)
    print_summary(chunks)
    print(f"\nWrote: {output_path}")


if __name__ == "__main__":
    main()
```

---

## 7. Run the script

From the project root:

```bash
python scripts/chunk_pages.py \
  --input data/raw_pages.jsonl \
  --output data/chunks.jsonl \
  --source infineon_manual.pdf
```

Example output:

```text
Chunking complete
  chunks:      187
  min tokens:  421
  max tokens:  800
  avg tokens:  793

Sample chunk:
--------------------------------------------------------------------------------
chunk_id:    chunk-000001
source:      infineon_manual.pdf
page_start:  1
page_end:    2
tokens:      800
...
--------------------------------------------------------------------------------

Wrote: data/chunks.jsonl
```

---

## 8. Inspect the output

Check first lines:

```bash
head -n 3 data/chunks.jsonl
```

Or pretty-print one chunk:

```bash
python - <<'PY'
import json

with open("data/chunks.jsonl", "r", encoding="utf-8") as f:
    first = json.loads(next(f))

print(json.dumps(first, indent=2, ensure_ascii=False)[:3000])
PY
```

You should see:

- `chunk_id`
- `source`
- `page_start`
- `page_end`
- `chunk_index`
- `token_count`
- `text`

---

## 9. Quality check

Do a fast manual check.

Open 5–10 random chunks and ask:

### Good signs

- chunk has enough context to understand the topic;
- page markers are visible;
- text is not empty;
- text is not only header/footer noise;
- tables are ugly but still somewhat readable;
- token count is roughly around 600–900.

### Bad signs

- chunks contain mostly repeated headers/footers;
- chunks start/end in very confusing places;
- many chunks have broken single words only;
- tables are completely unusable;
- `page_start` / `page_end` is often `null`;
- chunk count is suspiciously tiny or huge.

For PoC, do not overreact to imperfect chunks. We only need “good enough to search”.

---

## 10. Recommended initial settings

Use this first:

```bash
python scripts/chunk_pages.py \
  --chunk-size 800 \
  --overlap 120 \
  --source infineon_manual.pdf
```

If answers later feel too broad/noisy:

```bash
--chunk-size 600 --overlap 100
```

If answers later miss context:

```bash
--chunk-size 1000 --overlap 150
```

Do not tune endlessly now. Step 3 and Step 4 will reveal whether chunking is good enough.

---

## 11. What this script does well

This Step 2 script is intentionally simple and robust.

It gives us:

- JSONL chunks;
- token-sized text blocks;
- page metadata;
- source metadata;
- overlap;
- reproducible output;
- easy inspection.

That is enough for the next step: embeddings.

---

## 12. What this script does not solve yet

It does **not** yet solve:

- perfect table extraction;
- section-title detection;
- chapter hierarchy;
- register-aware chunking;
- warning/note preservation;
- duplicate header/footer removal;
- hybrid keyword/vector search;
- document versioning.

That is fine.

Those are later improvements after we have a complete working loop.

---

## 13. Definition of done for Step 2

Step 2 is done when:

1. `data/chunks.jsonl` exists;
2. chunks have non-empty text;
3. chunks have `chunk_id`, `source`, `page_start`, `page_end`, `token_count`;
4. first 5–10 inspected chunks look usable enough;
5. the number of chunks is plausible for the document size.

Example:

```text
PDF has 300 pages
chunks.jsonl has 300–700 chunks
```

That would be plausible.

If a 300-page manual produces only 20 chunks or 10,000 chunks, something is wrong.

---

## 14. Next step

Step 3 will be:

```text
chunks.jsonl
  ↓
embeddings
  ↓
ChromaDB
```

Goal of Step 3:

> Store chunks in a vector database so we can search them semantically.

But before Step 3, make sure Step 2 output looks reasonable.

Do not chase perfection.

The correct PoC flow is:

```text
usable extraction
  ↓
usable chunking
  ↓
usable retrieval
  ↓
then improve weak parts
```
