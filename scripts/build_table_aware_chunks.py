#!/usr/bin/env python3
"""
Experimental table-aware row-group chunk builder (generalized interface).

This generalizes the CLI of ``scripts/build_memory_map_table_chunks.py`` so the
same table-aware chunking can be pointed at other table-heavy slices via flags
(input, output, doc-id, source, page ranges, section title, group/residual
sizes) instead of memory_map-hardcoded constants.

It is still an *experiment*, not the normal ingest pipeline:
- it does not change ``scripts/chunk_pages.py`` or ``scripts/ingest_document.py``
- it makes no model/API calls
- its row/table heuristics are tuned to AURIX-style address-map tables

Pipeline:
    raw_pages.jsonl -> filter --page-ranges -> detect multiline address rows
    -> group rows into table_row_group chunks (context repeated per chunk)
    -> generic_residual chunks for non-table text -> JSONL for embed_chunks.py

The retrieval eval is page-level, so non-table text is kept as generic_residual
chunks to preserve full page coverage and a fair comparison.

Segment detection is best-effort and guarded: a bare integer 0-15 is accepted as
a segment marker only when the next content line is an address range or a table
column header. The run report prints accepted vs. skipped markers.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterator

import tiktoken


DEFAULT_COLUMN_HEADERS = ["Segment", "Address Range", "Size", "Description", "Read", "Write"]

ADDR_START = re.compile(r"^[0-9A-F]{4} [0-9A-F]{4}H$")
ADDR_END = re.compile(r"^- [0-9A-F]{4} [0-9A-F]{4}H$")
TABLE_TITLE = re.compile(r"^Table\s+(\d+)\s*$")
FOOTNOTE = re.compile(r"^\d+\)")
SEGMENT_MARKER = re.compile(r"^\d{1,2}$")

HEADER_TOKENS = {
    "segm",
    "ent",
    "segment",
    "address range",
    "size",
    "description",
    "access type",
    "read",
    "write",
}

BOILERPLATE_EXACT = {
    "user’s manual",
    "user's manual",
    "aurix™ tc3xx",
}
BOILERPLATE_RE = [
    re.compile(r"^\d+-\d+$"),          # page label, e.g. 2-6
    re.compile(r"^V\d+\.\d+\.\d+$"),   # version, e.g. V2.0.0
    re.compile(r"^MEMMAP"),            # running footer id, e.g. MEMMAPV0.1.21
    re.compile(r"^\d{4}-\d{2}$"),      # date, e.g. 2021-02
]


def parse_page_ranges(spec: str) -> list[tuple[int, int]]:
    """Parse "90-102" or "90-94,96,100-102" into inclusive (start, end) ranges."""
    ranges: list[tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start > end:
                raise SystemExit(f"Invalid page range '{part}': start > end")
            ranges.append((start, end))
        else:
            value = int(part)
            ranges.append((value, value))
    if not ranges:
        raise SystemExit(f"--page-ranges produced no pages: {spec!r}")
    return ranges


def page_in_ranges(page: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= page <= end for start, end in ranges)


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} in {path}") from exc


def is_boilerplate(line: str, section_title_low: str) -> bool:
    low = line.strip().lower()
    if low in BOILERPLATE_EXACT:
        return True
    if section_title_low and low == section_title_low:
        return True
    return any(rx.match(line.strip()) for rx in BOILERPLATE_RE)


def is_header_token(line: str) -> bool:
    return line.strip().lower() in HEADER_TOKENS


def is_segment_marker(line: str) -> bool:
    s = line.strip()
    return bool(SEGMENT_MARKER.match(s)) and 0 <= int(s) <= 15


def render_row(start: str, end: str, rest: list[str]) -> str:
    fields = [f"{start} - {end}"] + [r for r in rest if r]
    return " | ".join(fields)


def parse_pages(
    records: list[dict], section_title_low: str
) -> tuple[list[dict], dict[int, list[str]], dict[str, int]]:
    """Return (rows, residual_lines_by_page, stats)."""
    rows: list[dict[str, Any]] = []
    residual: dict[int, list[str]] = {}
    stats = {"segments_accepted": 0, "segments_skipped": 0}

    current_table_title = ""
    current_segment: str | None = None

    for record in records:
        page = int(record["page"])
        lines = record.get("text", "").split("\n")
        consumed = [False] * len(lines)

        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if not s:
                consumed[i] = True
                i += 1
                continue
            if is_boilerplate(s, section_title_low):
                consumed[i] = True
                i += 1
                continue

            m = TABLE_TITLE.match(s)
            if m:
                consumed[i] = True
                j = i + 1
                desc = ""
                while j < len(lines):
                    t = lines[j].strip()
                    if not t or is_boilerplate(t, section_title_low):
                        consumed[j] = True
                        j += 1
                        continue
                    if is_header_token(t) or ADDR_START.match(t) or is_segment_marker(t):
                        break
                    desc = t
                    consumed[j] = True
                    j += 1
                    break
                current_table_title = f"Table {m.group(1)} {desc}".strip()
                i = j
                continue

            if is_header_token(s):
                consumed[i] = True
                i += 1
                continue

            if is_segment_marker(s):
                k = i + 1
                nxt = None
                while k < len(lines):
                    t = lines[k].strip()
                    if not t or is_boilerplate(t, section_title_low):
                        k += 1
                        continue
                    nxt = t
                    break
                if nxt is not None and (ADDR_START.match(nxt) or is_header_token(nxt)):
                    current_segment = s
                    stats["segments_accepted"] += 1
                    consumed[i] = True
                    i += 1
                    continue
                stats["segments_skipped"] += 1

            if ADDR_START.match(s):
                consumed[i] = True
                start_addr = s
                end_addr = ""
                j = i + 1
                while j < len(lines):
                    t = lines[j].strip()
                    if not t or is_boilerplate(t, section_title_low):
                        consumed[j] = True
                        j += 1
                        continue
                    if ADDR_END.match(t):
                        end_addr = t[2:].strip()
                        consumed[j] = True
                        j += 1
                    break
                rest: list[str] = []
                while j < len(lines):
                    t = lines[j].strip()
                    if not t or is_boilerplate(t, section_title_low):
                        consumed[j] = True
                        j += 1
                        continue
                    if (
                        ADDR_START.match(t)
                        or TABLE_TITLE.match(t)
                        or is_segment_marker(t)
                        or is_header_token(t)
                        or FOOTNOTE.match(t)
                    ):
                        break
                    rest.append(t)
                    consumed[j] = True
                    j += 1
                rows.append(
                    {
                        "page": page,
                        "table_title": current_table_title,
                        "segment": current_segment,
                        "text": render_row(start_addr, end_addr, rest),
                    }
                )
                i = j
                continue

            i += 1  # leave unconsumed -> residual

        residual[page] = [
            lines[idx].strip()
            for idx in range(len(lines))
            if not consumed[idx] and lines[idx].strip()
        ]

    return rows, residual, stats


def build_row_group_chunks(
    rows: list[dict[str, Any]],
    *,
    source: str,
    doc_id: str,
    section_title: str,
    group_size: int,
    encoding: Any,
    start_index: int,
    page_chunk_counter: dict[int, int],
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    global_index = start_index

    i = 0
    while i < len(rows):
        group = [rows[i]]
        j = i + 1
        while (
            j < len(rows)
            and len(group) < group_size
            and rows[j]["page"] == rows[i]["page"]
            and rows[j]["table_title"] == rows[i]["table_title"]
            and rows[j]["segment"] == rows[i]["segment"]
        ):
            group.append(rows[j])
            j += 1

        head = rows[i]
        header_lines = []
        if section_title:
            header_lines.append(section_title)
        if head["table_title"]:
            header_lines.append(head["table_title"])
        if head["segment"] is not None:
            header_lines.append(f"Segment: {head['segment']}")
        header_lines.append("Columns: " + " | ".join(DEFAULT_COLUMN_HEADERS))
        body = "\n".join(r["text"] for r in group)
        text = "\n".join(header_lines) + "\n\n" + body

        page = head["page"]
        page_chunk_index = page_chunk_counter.get(page, 0)
        page_chunk_counter[page] = page_chunk_index + 1

        chunks.append(
            {
                "chunk_id": f"tachunk-{global_index:06d}",
                "doc_id": doc_id,
                "source": source,
                "page_start": page,
                "page_end": page,
                "page_chunk_index": page_chunk_index,
                "chunk_index": global_index,
                "token_count": len(encoding.encode(text)),
                "chunk_type": "table_row_group",
                "section_title": section_title,
                "table_title": head["table_title"],
                "table_context": f"Segment {head['segment']}" if head["segment"] is not None else "",
                "column_headers": DEFAULT_COLUMN_HEADERS,
                "row_count": len(group),
                "text": text,
            }
        )
        global_index += 1
        i = j

    return chunks


def build_residual_chunks(
    residual: dict[int, list[str]],
    *,
    source: str,
    doc_id: str,
    section_title: str,
    chunk_size: int,
    overlap: int,
    encoding: Any,
    start_index: int,
    page_chunk_counter: dict[int, int],
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    global_index = start_index

    for page in sorted(residual):
        text = "\n".join(residual[page]).strip()
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
                        "chunk_id": f"tachunk-{global_index:06d}",
                        "doc_id": doc_id,
                        "source": source,
                        "page_start": page,
                        "page_end": page,
                        "page_chunk_index": page_chunk_index,
                        "chunk_index": global_index,
                        "token_count": len(tokens[start:end]),
                        "chunk_type": "generic_residual",
                        "section_title": section_title,
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build experimental table-aware row-group chunks for a selected page range."
    )
    parser.add_argument("--input", default="data/raw_pages.jsonl", help="Extracted pages JSONL.")
    parser.add_argument("--output", required=True, help="Experimental output chunks JSONL (do not commit).")
    parser.add_argument("--doc-id", required=True, help="doc_id written into chunk metadata.")
    parser.add_argument("--source", required=True, help="Source document path for metadata.")
    parser.add_argument(
        "--page-ranges",
        required=True,
        help="Pages to use, e.g. '90-102' or '90-94,96,100-102'.",
    )
    parser.add_argument(
        "--section-title",
        default="",
        help="Section title repeated in each chunk and stripped as running header.",
    )
    parser.add_argument("--group-size", type=int, default=4, help="Max table rows per row-group chunk.")
    parser.add_argument("--residual-chunk-size", type=int, default=300, help="Token window for non-table text.")
    parser.add_argument("--residual-overlap", type=int, default=60, help="Token overlap for non-table text.")
    args = parser.parse_args()

    if args.residual_overlap >= args.residual_chunk_size:
        raise SystemExit("--residual-overlap must be smaller than --residual-chunk-size")

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"--input not found: {input_path}")

    ranges = parse_page_ranges(args.page_ranges)
    records = [r for r in read_jsonl(input_path) if page_in_ranges(int(r["page"]), ranges)]
    if not records:
        raise SystemExit(f"No pages matching --page-ranges {args.page_ranges!r} found in {input_path}")

    encoding = tiktoken.get_encoding("cl100k_base")
    section_title_low = args.section_title.strip().lower()
    rows, residual, stats = parse_pages(records, section_title_low)

    page_chunk_counter: dict[int, int] = {}
    row_chunks = build_row_group_chunks(
        rows,
        source=args.source,
        doc_id=args.doc_id,
        section_title=args.section_title,
        group_size=args.group_size,
        encoding=encoding,
        start_index=0,
        page_chunk_counter=page_chunk_counter,
    )
    residual_chunks = build_residual_chunks(
        residual,
        source=args.source,
        doc_id=args.doc_id,
        section_title=args.section_title,
        chunk_size=args.residual_chunk_size,
        overlap=args.residual_overlap,
        encoding=encoding,
        start_index=len(row_chunks),
        page_chunk_counter=page_chunk_counter,
    )

    all_chunks = row_chunks + residual_chunks
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    pages_covered = sorted({c["page_start"] for c in all_chunks})
    seg_total = stats["segments_accepted"] + stats["segments_skipped"]
    seg_reliable = stats["segments_skipped"] == 0 and stats["segments_accepted"] > 0

    print(f"Wrote {len(all_chunks)} chunks to {args.output}")
    print(f"  doc_id                 : {args.doc_id}")
    print(f"  page ranges            : {ranges}")
    print(f"  table_row_group chunks : {len(row_chunks)}  ({len(rows)} rows)")
    print(f"  generic_residual chunks: {len(residual_chunks)}")
    print(f"  pages covered          : {pages_covered}")
    print(
        f"  segment markers        : accepted={stats['segments_accepted']} "
        f"skipped={stats['segments_skipped']} (of {seg_total})"
    )
    if not seg_reliable:
        print(
            "  WARNING: segment detection is NOT fully reliable for this run; "
            "treat table_context as best-effort."
        )


if __name__ == "__main__":
    main()
