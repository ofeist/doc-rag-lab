#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path

from build_mixed_chunks import (
    DEFAULT_MIN_TABLE_SCORE,
    DEFAULT_TABLE_GROUP_SIZE,
    DEFAULT_TABLE_RESIDUAL_CHUNK_SIZE,
    DEFAULT_TABLE_RESIDUAL_OVERLAP,
)
from chunk_pages import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, build_chunks, write_jsonl as write_chunks_jsonl
from embed_chunks import DEFAULT_MODEL, embed_chunks
from extract_pages import extract_pages, write_jsonl as write_pages_jsonl


DEFAULT_RAW_PAGES = Path("data/raw_pages.jsonl")
DEFAULT_CHUNKS = Path("data/chunks.jsonl")
DEFAULT_DB = Path("vector_db/chroma")
DEFAULT_COLLECTION = "technical_docs"

SCRIPTS_DIR = Path(__file__).resolve().parent


def add_doc_id(records: list[dict], doc_id: str) -> list[dict]:
    for record in records:
        record["doc_id"] = doc_id
    return records


def count_jsonl_lines(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def run_script(name: str, script_args: list[str]) -> None:
    """Run a sibling pipeline script with the current interpreter."""
    cmd = [sys.executable, str(SCRIPTS_DIR / name), *script_args]
    subprocess.run(cmd, check=True)


def print_summary(
    chunk_mode: str,
    doc_id: str,
    pdf: Path,
    page_ranges: str | None,
    raw_pages_path: Path,
    chunks_path: Path,
    db_path: Path,
    collection: str,
    page_count: int,
    chunk_count: int,
    candidates_path: Path | None = None,
) -> None:
    summary = {
        "chunk_mode": chunk_mode,
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
    if candidates_path is not None:
        summary["table_candidates"] = str(candidates_path)
    print()
    print("Ingest summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def run_generic_ingest(args: argparse.Namespace) -> int:
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
        chunk_mode="generic",
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


def run_mixed_ingest(args: argparse.Namespace) -> int:
    # Detector-driven mixed ingest (P3-19). Orchestrates the proven experimental
    # scripts over doc_id-scoped intermediate files under data/. These are
    # generated artifacts and stay gitignored; artifact cleanup is P3-21.
    raw_pages_path = Path(f"data/raw_pages_{args.doc_id}.jsonl")
    candidates_path = Path(f"data/table_page_candidates_{args.doc_id}.jsonl")
    chunks_path = Path(f"data/chunks_{args.doc_id}.jsonl")

    print("Step 1/4: extracting PDF pages")
    pages = extract_pages(args.pdf, page_ranges=args.page_ranges)
    add_doc_id(pages, args.doc_id)
    write_pages_jsonl(pages, raw_pages_path)
    print(f"Extracted pages: {len(pages)}")
    print(f"Raw pages written to: {raw_pages_path}")

    print()
    print("Step 2/4: detecting table-heavy pages")
    run_script(
        "detect_table_pages.py",
        [
            "--input", str(raw_pages_path),
            "--output", str(candidates_path),
            "--min-score", str(args.min_table_score),
        ],
    )

    print()
    print("Step 3/4: building mixed chunks")
    run_script(
        "build_mixed_chunks.py",
        [
            "--input", str(raw_pages_path),
            "--output", str(chunks_path),
            "--doc-id", args.doc_id,
            "--source", str(args.pdf),
            "--table-candidates", str(candidates_path),
            "--min-table-score", str(args.min_table_score),
            "--section-title", args.section_title,
            "--chunk-size", str(args.chunk_size),
            "--overlap", str(args.overlap),
            "--table-group-size", str(args.table_group_size),
            "--table-residual-chunk-size", str(args.table_residual_chunk_size),
            "--table-residual-overlap", str(args.table_residual_overlap),
        ],
    )
    chunk_count = count_jsonl_lines(chunks_path)

    print()
    print("Step 4/4: embedding chunks")
    embed_chunks(
        chunks_path=chunks_path,
        db_path=args.db,
        collection_name=args.collection,
        model_name=args.embedding_model,
        batch_size=args.batch_size,
        reset=args.reset,
    )

    print_summary(
        chunk_mode="mixed",
        doc_id=args.doc_id,
        pdf=args.pdf,
        page_ranges=args.page_ranges,
        raw_pages_path=raw_pages_path,
        chunks_path=chunks_path,
        db_path=args.db,
        collection=args.collection,
        page_count=len(pages),
        chunk_count=chunk_count,
        candidates_path=candidates_path,
    )
    return 0


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
    parser.add_argument("--raw-pages", type=Path, default=DEFAULT_RAW_PAGES, help="Raw pages JSONL path (generic mode).")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS, help="Chunks JSONL path (generic mode).")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Persistent ChromaDB directory.")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Chroma collection name.")
    parser.add_argument(
        "--chunk-size",
        "--chunk-tokens",
        dest="chunk_size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Generic chunk size in tokens.",
    )
    parser.add_argument(
        "--overlap",
        "--overlap-tokens",
        dest="overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        help="Generic chunk overlap in tokens.",
    )
    parser.add_argument("--embedding-model", default=DEFAULT_MODEL, help="SentenceTransformer model name.")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing ChromaDB directory before embedding.",
    )
    parser.add_argument(
        "--chunk-mode",
        choices=["generic", "mixed"],
        default="generic",
        help=(
            "Chunking mode. 'generic' (default) keeps page-aware token-window "
            "chunks. 'mixed' runs detector-driven mixed chunking "
            "(extract -> detect_table_pages -> build_mixed_chunks -> embed)."
        ),
    )
    mixed_group = parser.add_argument_group("mixed mode options")
    mixed_group.add_argument(
        "--section-title",
        default="",
        help="Section title repeated in table-aware chunks and stripped as running header.",
    )
    mixed_group.add_argument(
        "--min-table-score",
        type=float,
        default=DEFAULT_MIN_TABLE_SCORE,
        help=f"Minimum table_likelihood for table page selection. Default: {DEFAULT_MIN_TABLE_SCORE}",
    )
    mixed_group.add_argument(
        "--table-group-size",
        type=int,
        default=DEFAULT_TABLE_GROUP_SIZE,
        help=f"Max table rows per table_row_group chunk. Default: {DEFAULT_TABLE_GROUP_SIZE}",
    )
    mixed_group.add_argument(
        "--table-residual-chunk-size",
        type=int,
        default=DEFAULT_TABLE_RESIDUAL_CHUNK_SIZE,
        help=f"Token window for non-table residual text on detected table pages. Default: {DEFAULT_TABLE_RESIDUAL_CHUNK_SIZE}",
    )
    mixed_group.add_argument(
        "--table-residual-overlap",
        type=int,
        default=DEFAULT_TABLE_RESIDUAL_OVERLAP,
        help=f"Token overlap for non-table residual text on detected table pages. Default: {DEFAULT_TABLE_RESIDUAL_OVERLAP}",
    )
    args = parser.parse_args()

    if args.chunk_mode == "mixed":
        return run_mixed_ingest(args)
    return run_generic_ingest(args)


if __name__ == "__main__":
    raise SystemExit(main())
