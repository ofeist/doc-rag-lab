#!/usr/bin/env python3
"""
P3-2 experiment: table-aware row-group chunking for the ``memory_map`` slice ONLY.

This is a focused retrieval experiment, not a production parser and not a change
to the normal ingest pipeline (``scripts/chunk_pages.py`` is left untouched).

Input:
    data/raw_pages.jsonl   (expected to contain memory_map pages, default 90-102
                            of the AURIX TC3xx Part 1 user manual)

Output (experimental artifact, do NOT commit):
    data/chunks_table_aware_memory_map.jsonl

Idea
----
PyMuPDF text extraction of the AURIX address-map tables is highly regular: each
table row is emitted as a small run of single-field lines, e.g.

    8000 0000H
    - 802F FFFFH
    3 Mbyte
    Program Flash 0 (PF0)
    Access
    SRIBE

We detect those rows, group a few consecutive ones, and repeat the section
title, table title, segment context and column headers in every chunk so each
row group is independently retrievable.

Non-table text (prose, the Table 23 acronym list, footnotes) falls back to plain
token-window chunking so the experimental file is a *complete* retrieval corpus
for the slice and the comparison against the generic 300/60 baseline stays fair
(the retrieval eval is page-level, so every expected page must be represented).

Segment detection is best-effort and guarded: a bare integer 0-15 is only
accepted as a segment marker when the next content line is an address range or a
table column header. The run report prints how many segment markers were
accepted vs. skipped so the reliability of this heuristic is visible.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterator

import tiktoken


DEFAULT_PDF = "docs/infineon-aurix-tc3xx-part1-usermanual-en.pdf"
DEFAULT_DOC_ID = "memory_map"
SECTION_TITLE = "Memory Maps (MEMMAP)"
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
    "memory maps (memmap)",
}
BOILERPLATE_RE = [
    re.compile(r"^\d+-\d+$"),          # page label, e.g. 2-6
    re.compile(r"^V\d+\.\d+\.\d+$"),   # version, e.g. V2.0.0
    re.compile(r"^MEMMAP"),            # running footer id, e.g. MEMMAPV0.1.21
    re.compile(r"^\d{4}-\d{2}$"),      # date, e.g. 2021-02
]


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


def is_boilerplate(line: str) -> bool:
    low = line.strip().lower()
    if low in BOILERPLATE_EXACT:
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


def parse_pages(records: list[dict]) -> tuple[list[dict], dict[int, list[str]], dict[str, int]]:
    """Return (rows, residual_lines_by_page, stats).

    rows: ordered list of {page, table_title, segment, text} row records.
    residual_lines_by_page: page -> ordered non-table, non-boilerplate lines.
    """
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
            if is_boilerplate(s):
                consumed[i] = True
                i += 1
                continue

            # Table title block: a line that is *only* "Table NN".
            m = TABLE_TITLE.match(s)
            if m:
                consumed[i] = True
                j = i + 1
                desc = ""
                while j < len(lines):
                    t = lines[j].strip()
                    if not t or is_boilerplate(t):
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

            # Column header tokens: skip, they are repeated structure.
            if is_header_token(s):
                consumed[i] = True
                i += 1
                continue

            # Segment marker (guarded): bare 0-15 followed by an address/header line.
            if is_segment_marker(s):
                k = i + 1
                nxt = None
                while k < len(lines):
                    t = lines[k].strip()
                    if not t or is_boilerplate(t):
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
                # fall through: treat as residual text

            # Address-map row: "AAAA AAAAH" then "- BBBB BBBBH" then field lines.
            if ADDR_START.match(s):
                consumed[i] = True
                start_addr = s
                end_addr = ""
                j = i + 1
                while j < len(lines):
                    t = lines[j].strip()
                    if not t or is_boilerplate(t):
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
                    if not t or is_boilerplate(t):
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
    source: str,
    doc_id: str,
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
        header_lines = [SECTION_TITLE]
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
                "chunk_id": f"mmtable-{global_index:06d}",
                "doc_id": doc_id,
                "source": source,
                "page_start": page,
                "page_end": page,
                "page_chunk_index": page_chunk_index,
                "chunk_index": global_index,
                "token_count": len(encoding.encode(text)),
                "chunk_type": "table_row_group",
                "section_title": SECTION_TITLE,
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
                        "chunk_id": f"mmtable-{global_index:06d}",
                        "doc_id": doc_id,
                        "source": source,
                        "page_start": page,
                        "page_end": page,
                        "page_chunk_index": page_chunk_index,
                        "chunk_index": global_index,
                        "token_count": len(tokens[start:end]),
                        "chunk_type": "generic_residual",
                        "section_title": SECTION_TITLE,
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
        description="Build experimental table-aware row-group chunks for the memory_map slice."
    )
    parser.add_argument("--input", default="data/raw_pages.jsonl", help="Extracted pages JSONL.")
    parser.add_argument(
        "--output",
        default="data/chunks_table_aware_memory_map.jsonl",
        help="Experimental output chunks JSONL (do not commit).",
    )
    parser.add_argument("--source", default=DEFAULT_PDF, help="Source document path for metadata.")
    parser.add_argument("--doc-id", default=DEFAULT_DOC_ID, help="doc_id written into chunk metadata.")
    parser.add_argument("--page-start", type=int, default=90, help="First memory_map page to use.")
    parser.add_argument("--page-end", type=int, default=102, help="Last memory_map page to use.")
    parser.add_argument("--group-size", type=int, default=4, help="Max table rows per row-group chunk.")
    parser.add_argument("--residual-chunk-size", type=int, default=300, help="Token window for non-table text.")
    parser.add_argument("--residual-overlap", type=int, default=60, help="Token overlap for non-table text.")
    args = parser.parse_args()

    if args.residual_overlap >= args.residual_chunk_size:
        raise SystemExit("--residual-overlap must be smaller than --residual-chunk-size")

    records = [
        r
        for r in read_jsonl(Path(args.input))
        if args.page_start <= int(r["page"]) <= args.page_end
    ]
    if not records:
        raise SystemExit(
            f"No pages in range {args.page_start}-{args.page_end} found in {args.input}"
        )

    encoding = tiktoken.get_encoding("cl100k_base")
    rows, residual, stats = parse_pages(records)

    page_chunk_counter: dict[int, int] = {}
    row_chunks = build_row_group_chunks(
        rows,
        source=args.source,
        doc_id=args.doc_id,
        group_size=args.group_size,
        encoding=encoding,
        start_index=0,
        page_chunk_counter=page_chunk_counter,
    )
    residual_chunks = build_residual_chunks(
        residual,
        source=args.source,
        doc_id=args.doc_id,
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
