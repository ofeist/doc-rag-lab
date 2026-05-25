#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from chunk_pages import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, build_chunks, write_jsonl as write_chunks_jsonl
from embed_chunks import DEFAULT_MODEL, embed_chunks
from extract_pages import extract_pages, write_jsonl as write_pages_jsonl


DEFAULT_RAW_PAGES = Path("data/raw_pages.jsonl")
DEFAULT_CHUNKS = Path("data/chunks.jsonl")
DEFAULT_DB = Path("vector_db/chroma")
DEFAULT_COLLECTION = "technical_docs"


def add_doc_id(records: list[dict], doc_id: str) -> list[dict]:
    for record in records:
        record["doc_id"] = doc_id
    return records


def print_summary(
    doc_id: str,
    pdf: Path,
    page_ranges: str | None,
    raw_pages_path: Path,
    chunks_path: Path,
    db_path: Path,
    collection: str,
    page_count: int,
    chunk_count: int,
) -> None:
    summary = {
        "doc_id": doc_id,
        "pdf": str(pdf),
        "page_ranges": page_ranges or "full",
        "raw_pages": str(raw_pages_path),
        "chunks": str(chunks_path),
        "db": str(db_path),
        "collection": collection,
        "pages": page_count,
        "chunks_written": chunk_count,
    }
    print()
    print("Ingest summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the PDF ingest pipeline: extract, chunk, embed."
    )
    parser.add_argument("--pdf", type=Path, required=True, help="Path to the source PDF.")
    parser.add_argument(
        "--page-ranges",
        default=None,
        help="Optional comma-separated 1-based PDF page ranges, e.g. 115-126,257,310-312. Omit for full PDF ingest.",
    )
    parser.add_argument("--doc-id", required=True, help="Stable slice/document id added to metadata.")
    parser.add_argument("--raw-pages", type=Path, default=DEFAULT_RAW_PAGES, help="Raw pages JSONL path.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS, help="Chunks JSONL path.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Persistent ChromaDB directory.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Chroma collection name.")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Chunk size in tokens.")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="Chunk overlap in tokens.")
    parser.add_argument("--embedding-model", default=DEFAULT_MODEL, help="SentenceTransformer model name.")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing ChromaDB directory before embedding.",
    )
    args = parser.parse_args()

    print("Step 1/3: extracting PDF pages")
    pages = extract_pages(args.pdf, page_ranges=args.page_ranges)
    add_doc_id(pages, args.doc_id)
    write_pages_jsonl(pages, args.raw_pages)
    print(f"Extracted pages: {len(pages)}")
    print(f"Raw pages written to: {args.raw_pages}")

    print()
    print("Step 2/3: chunking extracted pages")
    chunks = build_chunks(
        raw_pages_path=args.raw_pages,
        source=str(args.pdf),
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    add_doc_id(chunks, args.doc_id)
    write_chunks_jsonl(args.chunks, chunks)
    print(f"Wrote chunks: {len(chunks)}")
    print(f"Chunks written to: {args.chunks}")

    print()
    print("Step 3/3: embedding chunks")
    embed_chunks(
        chunks_path=args.chunks,
        db_path=args.db,
        collection_name=args.collection,
        model_name=args.embedding_model,
        batch_size=args.batch_size,
        reset=args.reset,
    )

    print_summary(
        doc_id=args.doc_id,
        pdf=args.pdf,
        page_ranges=args.page_ranges,
        raw_pages_path=args.raw_pages,
        chunks_path=args.chunks,
        db_path=args.db,
        collection=args.collection,
        page_count=len(pages),
        chunk_count=len(chunks),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
