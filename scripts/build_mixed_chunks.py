#!/usr/bin/env python3
"""
Build an experimental mixed chunk corpus.

This combines generic token-window chunks for non-table pages with table-aware
row-group chunks plus residual chunks for pages selected by detect_table_pages.py.
It does not replace the normal ingest pipeline.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import tiktoken

from build_table_aware_chunks import (
    build_residual_chunks,
    build_row_group_chunks,
    parse_pages,
    read_jsonl,
)


DEFAULT_INPUT = "data/raw_pages.jsonl"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 120
DEFAULT_TABLE_GROUP_SIZE = 4
DEFAULT_TABLE_RESIDUAL_CHUNK_SIZE = 300
DEFAULT_TABLE_RESIDUAL_OVERLAP = 60
DEFAULT_MIN_TABLE_SCORE = 0.5


def load_candidate_pages(path: Path, min_score: float) -> tuple[set[int], int]:
    if not path.exists():
        raise SystemExit(f"--table-candidates not found: {path}")

    selected: set[int] = set()
    total = 0
    for line_number, record in enumerate(read_jsonl(path), start=1):
        total += 1
        missing = [
            field
            for field in ("page", "table_likelihood", "recommended_chunker")
            if field not in record
        ]
        if missing:
            fields = ", ".join(missing)
            raise SystemExit(f"Invalid candidate record on line {line_number}: missing {fields}")

        try:
            page = int(record["page"])
            score = float(record["table_likelihood"])
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"Invalid candidate record on line {line_number}: bad page/score") from exc

        if str(record["recommended_chunker"]) == "table_row_group" and score >= min_score:
            selected.add(page)

    return selected, total


def build_generic_page_chunks(
    records: list[dict[str, Any]],
    *,
    source: str,
    doc_id: str,
    chunk_size: int,
    overlap: int,
    encoding: Any,
    start_index: int,
    page_chunk_counter: dict[int, int],
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    global_index = start_index

    for record in sorted(records, key=lambda item: int(item["page"])):
        page = int(record["page"])
        text = str(record.get("text", "")).replace("\x00", "").strip()
        if not text:
            continue

        tokens = encoding.encode(text)
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            piece = encoding.decode(tokens[start:end]).strip()
            if piece:
                page_chunk_index = page_chunk_counter.get(page, 0)
                page_chunk_counter[page] = page_chunk_index + 1
                chunks.append(
                    {
                        "chunk_id": f"mixed-{global_index:06d}",
                        "doc_id": doc_id,
                        "source": source,
                        "page_start": page,
                        "page_end": page,
                        "page_chunk_index": page_chunk_index,
                        "chunk_index": global_index,
                        "token_count": len(tokens[start:end]),
                        "chunk_type": "generic_page",
                        "section_title": "",
                        "table_title": "",
                        "table_context": "",
                        "column_headers": [],
                        "row_count": 0,
                        "text": piece,
                    }
                )
                global_index += 1
            if end == len(tokens):
                break
            start += chunk_size - overlap

    return chunks


def renumber_chunks(chunks: list[dict[str, Any]], encoding: Any) -> list[dict[str, Any]]:
    ordered = sorted(
        chunks,
        key=lambda item: (
            int(item["page_start"]),
            int(item["page_chunk_index"]),
            int(item["chunk_index"]),
        ),
    )
    for index, chunk in enumerate(ordered):
        chunk["chunk_id"] = f"mixed-{index:06d}"
        chunk["chunk_index"] = index
        chunk["token_count"] = len(encoding.encode(str(chunk.get("text", ""))))
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser(description="Build experimental mixed generic/table-aware chunks.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Extracted pages JSONL.")
    parser.add_argument("--output", required=True, help="Output mixed chunks JSONL (do not commit).")
    parser.add_argument("--doc-id", required=True, help="doc_id written into chunk metadata.")
    parser.add_argument("--source", required=True, help="Source document path for metadata.")
    parser.add_argument("--table-candidates", required=True, help="Detector output JSONL.")
    parser.add_argument(
        "--min-table-score",
        type=float,
        default=DEFAULT_MIN_TABLE_SCORE,
        help=f"Minimum table_likelihood for table page selection. Default: {DEFAULT_MIN_TABLE_SCORE}",
    )
    parser.add_argument(
        "--section-title",
        default="",
        help="Section title repeated in table-aware chunks and stripped as running header.",
    )
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Generic chunk size.")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="Generic chunk overlap.")
    parser.add_argument(
        "--table-group-size",
        type=int,
        default=DEFAULT_TABLE_GROUP_SIZE,
        help="Max table rows per table_row_group chunk.",
    )
    parser.add_argument(
        "--table-residual-chunk-size",
        type=int,
        default=DEFAULT_TABLE_RESIDUAL_CHUNK_SIZE,
        help="Token window for non-table residual text on detected table pages.",
    )
    parser.add_argument(
        "--table-residual-overlap",
        type=int,
        default=DEFAULT_TABLE_RESIDUAL_OVERLAP,
        help="Token overlap for non-table residual text on detected table pages.",
    )
    args = parser.parse_args()

    if args.overlap >= args.chunk_size:
        raise SystemExit("--overlap must be smaller than --chunk-size")
    if args.table_residual_overlap >= args.table_residual_chunk_size:
        raise SystemExit("--table-residual-overlap must be smaller than --table-residual-chunk-size")
    if not 0.0 <= args.min_table_score <= 1.0:
        raise SystemExit("--min-table-score must be between 0.0 and 1.0")

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"--input not found: {input_path}")

    records = list(read_jsonl(input_path))
    if not records:
        raise SystemExit(f"No pages found in --input: {input_path}")
    for record in records:
        if "page" not in record or "text" not in record:
            raise SystemExit("Each input page record must contain page and text")

    table_pages, candidate_count = load_candidate_pages(Path(args.table_candidates), args.min_table_score)

    table_records = [record for record in records if int(record["page"]) in table_pages]
    generic_records = [record for record in records if int(record["page"]) not in table_pages]

    if not table_records:
        print("WARNING: no table pages selected; output will contain generic_page chunks only.")

    encoding = tiktoken.get_encoding("cl100k_base")
    page_chunk_counter: dict[int, int] = {}
    all_chunks: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    residual_chunks: list[dict[str, Any]] = []
    stats = {"segments_accepted": 0, "segments_skipped": 0}

    if table_records:
        rows, residual, stats = parse_pages(table_records, args.section_title.strip().lower())
        row_chunks = build_row_group_chunks(
            rows,
            source=args.source,
            doc_id=args.doc_id,
            section_title=args.section_title,
            group_size=args.table_group_size,
            encoding=encoding,
            start_index=0,
            page_chunk_counter=page_chunk_counter,
        )
        residual_chunks = build_residual_chunks(
            residual,
            source=args.source,
            doc_id=args.doc_id,
            section_title=args.section_title,
            chunk_size=args.table_residual_chunk_size,
            overlap=args.table_residual_overlap,
            encoding=encoding,
            start_index=len(row_chunks),
            page_chunk_counter=page_chunk_counter,
        )
        all_chunks.extend(row_chunks)
        all_chunks.extend(residual_chunks)

    generic_chunks = build_generic_page_chunks(
        generic_records,
        source=args.source,
        doc_id=args.doc_id,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        encoding=encoding,
        start_index=len(all_chunks),
        page_chunk_counter=page_chunk_counter,
    )
    all_chunks.extend(generic_chunks)
    all_chunks = renumber_chunks(all_chunks, encoding)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    selected_pages = sorted({int(record["page"]) for record in table_records})
    generic_pages = sorted({int(record["page"]) for record in generic_records})
    seg_total = stats["segments_accepted"] + stats["segments_skipped"]

    print(f"Wrote {len(all_chunks)} chunks to {args.output}")
    print(f"  input pages             : {len(records)}")
    print(f"  loaded candidates       : {candidate_count}")
    print(f"  detected table pages    : {len(selected_pages)}")
    print(f"  generic pages           : {len(generic_pages)}")
    print(f"  selected table pages    : {selected_pages}")
    print(f"  generic page list       : {generic_pages}")
    print(f"  generic_page chunks     : {len(generic_chunks)}")
    print(f"  table_row_group chunks  : {len([c for c in all_chunks if c['chunk_type'] == 'table_row_group'])} ({len(rows)} rows)")
    print(f"  generic_residual chunks : {len(residual_chunks)}")
    print(
        f"  segment markers         : accepted={stats['segments_accepted']} "
        f"skipped={stats['segments_skipped']} (of {seg_total})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
