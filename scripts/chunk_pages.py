#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Iterator

import tiktoken


DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 120


def read_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} in {path}: {exc}") from exc


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def chunk_tokens(tokens: list[int], chunk_size: int, overlap: int) -> Iterator[list[int]]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        yield tokens[start:end]

        if end == len(tokens):
            break

        start += chunk_size - overlap


def normalize_text(text: str) -> str:
    # Minimal cleanup only. Do not over-clean technical docs yet.
    return text.replace("\x00", "").strip()


def build_chunks(
    raw_pages_path: Path,
    source: str,
    chunk_size: int,
    overlap: int,
) -> list[dict]:
    encoding = tiktoken.get_encoding("cl100k_base")
    chunks: list[dict] = []
    global_chunk_index = 0

    for page_record in read_jsonl(raw_pages_path):
        page = page_record.get("page")
        text = normalize_text(page_record.get("text", ""))

        if page is None:
            raise ValueError(f"Missing 'page' field in record: {page_record}")

        if not text:
            continue

        tokens = encoding.encode(text)

        for page_chunk_index, token_chunk in enumerate(
            chunk_tokens(tokens, chunk_size=chunk_size, overlap=overlap)
        ):
            chunk_text = encoding.decode(token_chunk).strip()

            if not chunk_text:
                continue

            chunks.append(
                {
                    "chunk_id": f"chunk-{global_chunk_index:06d}",
                    "source": source,
                    "page_start": page,
                    "page_end": page,
                    "page_chunk_index": page_chunk_index,
                    "chunk_index": global_chunk_index,
                    "token_count": len(token_chunk),
                    "text": chunk_text,
                }
            )
            global_chunk_index += 1

    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk extracted PDF pages into JSONL chunks with stable page metadata."
    )
    parser.add_argument(
        "--input",
        default="data/raw_pages.jsonl",
        help="Input JSONL file created by extract_pages.py",
    )
    parser.add_argument(
        "--output",
        default="data/chunks.jsonl",
        help="Output JSONL chunks file",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source document label/path used in metadata, e.g. docs/infineon-manual.pdf",
    )
    parser.add_argument(
        "--chunk-size",
        "--chunk-tokens",
        dest="chunk_size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Chunk size in tokens. Default: {DEFAULT_CHUNK_SIZE}",
    )
    parser.add_argument(
        "--overlap",
        "--overlap-tokens",
        dest="overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        help=f"Overlap in tokens. Default: {DEFAULT_OVERLAP}",
    )

    args = parser.parse_args()

    chunks = build_chunks(
        raw_pages_path=Path(args.input),
        source=args.source,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )

    write_jsonl(Path(args.output), chunks)

    print(f"Wrote {len(chunks)} chunks to {args.output}")

    if chunks:
        first = chunks[0]
        print("\nFirst chunk preview:")
        print(
            json.dumps(
                {
                    "chunk_id": first["chunk_id"],
                    "source": first["source"],
                    "page_start": first["page_start"],
                    "page_end": first["page_end"],
                    "token_count": first["token_count"],
                    "text_preview": first["text"][:300],
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
