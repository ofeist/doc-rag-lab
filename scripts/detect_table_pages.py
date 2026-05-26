#!/usr/bin/env python3
"""
Detect likely table-heavy pages from extracted page JSONL.

This is an experiment only. It reads raw page text, emits candidate-page JSONL,
and does not modify ingest, chunking, retrieval, or answer generation.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterator


DEFAULT_INPUT = "data/raw_pages.jsonl"
DEFAULT_OUTPUT = "data/table_page_candidates.jsonl"
DEFAULT_MIN_SCORE = 0.5

TABLE_TITLE = re.compile(r"^Table\s+\d+", re.IGNORECASE)
ADDRESS_START = re.compile(r"^[0-9A-F]{4} [0-9A-F]{4}H$")
ADDRESS_END = re.compile(r"^- [0-9A-F]{4} [0-9A-F]{4}H$")
HEX_TOKEN = re.compile(r"\b[0-9A-F]{2,8}H\b")

TABLE_TITLE_TERMS = [
    "address map",
    "register",
]

HEADER_TERMS = [
    "Address Range",
    "Size",
    "Description",
    "Access Type",
    "Read",
    "Write",
    "Bit",
    "Field",
    "Reset",
]

ACCESS_TERMS = [
    "Access",
    "Reserved",
    "BBBBE",
    "SPBBE",
    "SRIBE",
    "PFLASH",
    "DSPR",
    "PSPR",
    "LMURAM",
    "DLMU",
    "Boot ROM",
]


def parse_page_ranges(spec: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                raise SystemExit(f"Invalid page range '{part}': start > end")
            ranges.append((start, end))
        else:
            page = int(part)
            ranges.append((page, page))
    if not ranges:
        raise SystemExit(f"--page-ranges produced no pages: {spec!r}")
    return ranges


def page_in_ranges(page: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= page <= end for start, end in ranges)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} in {path}") from exc


def count_case_insensitive(text: str, term: str) -> int:
    return text.lower().count(term.lower())


def detect_page(record: dict[str, Any]) -> dict[str, Any]:
    page = int(record.get("page", -1))
    text = str(record.get("text", ""))
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    lower_text = text.lower()

    table_title_count = sum(1 for line in non_empty_lines if TABLE_TITLE.match(line))
    table_title_term_count = sum(count_case_insensitive(text, term) for term in TABLE_TITLE_TERMS)
    address_start_count = sum(1 for line in non_empty_lines if ADDRESS_START.match(line))
    address_end_count = sum(1 for line in non_empty_lines if ADDRESS_END.match(line))
    hex_token_count = len(HEX_TOKEN.findall(text))
    access_keyword_count = sum(count_case_insensitive(text, term) for term in ACCESS_TERMS)
    column_header_hits = [term for term in HEADER_TERMS if term.lower() in lower_text]

    score = 0.0
    reasons: list[str] = []

    if table_title_count > 0 or table_title_term_count > 0:
        score += 0.20
        reasons.append("contains table title or table-like title terms")

    if address_start_count >= 3 and address_end_count >= 3:
        score += 0.25
        reasons.append("contains multiple split hex address ranges")

    if address_start_count >= 10:
        score += 0.20
        reasons.append("contains dense address-map rows")

    if len(column_header_hits) >= 3:
        score += 0.15
        reasons.append("contains table column header terms")

    if access_keyword_count >= 5:
        score += 0.10
        reasons.append("contains repeated access/table values")

    if hex_token_count >= 10:
        score += 0.10
        reasons.append("contains high hex-token density")

    table_likelihood = min(score, 1.0)

    if address_start_count >= 3 and address_end_count >= 3 and (
        "address map" in lower_text or len(column_header_hits) >= 3
    ):
        page_type = "address_map_table"
    elif table_title_count > 0 or len(column_header_hits) >= 3:
        page_type = "generic_table"
    elif table_likelihood > 0:
        page_type = "prose"
    else:
        page_type = "unknown"

    if page_type in {"address_map_table", "generic_table"}:
        recommended_chunker = "table_row_group"
    else:
        recommended_chunker = "generic"

    return {
        "page": page,
        "table_likelihood": round(table_likelihood, 2),
        "page_type": page_type,
        "recommended_chunker": recommended_chunker,
        "signals": {
            "table_title_count": table_title_count,
            "table_title_term_count": table_title_term_count,
            "address_start_count": address_start_count,
            "address_end_count": address_end_count,
            "hex_token_count": hex_token_count,
            "access_keyword_count": access_keyword_count,
            "column_header_hits": column_header_hits,
        },
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect likely table-heavy pages from raw page JSONL.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input raw pages JSONL.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output candidate pages JSONL.")
    parser.add_argument(
        "--min-score",
        type=float,
        default=DEFAULT_MIN_SCORE,
        help=f"Minimum table_likelihood to write. Default: {DEFAULT_MIN_SCORE}",
    )
    parser.add_argument(
        "--page-ranges",
        default=None,
        help="Optional page ranges, e.g. 90-102 or 90-94,96,100-102.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}")
        return 1

    if not 0.0 <= args.min_score <= 1.0:
        print("ERROR: --min-score must be between 0.0 and 1.0")
        return 1

    ranges = parse_page_ranges(args.page_ranges) if args.page_ranges else None

    scanned = 0
    candidates: list[dict[str, Any]] = []
    for record in read_jsonl(input_path):
        page = int(record.get("page", -1))
        if ranges is not None and not page_in_ranges(page, ranges):
            continue
        scanned += 1
        detected = detect_page(record)
        if float(detected["table_likelihood"]) >= args.min_score:
            candidates.append(detected)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for item in candidates:
            f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")

    address_map_count = sum(1 for item in candidates if item["page_type"] == "address_map_table")

    print(f"Scanned pages: {scanned}")
    print(f"Detected table-heavy pages: {len(candidates)}")
    print(f"Detected address-map pages: {address_map_count}")
    print(f"Output: {output_path}")

    if candidates:
        print()
        print("Top candidates:")
        ranked = sorted(candidates, key=lambda item: item["table_likelihood"], reverse=True)[:10]
        for item in ranked:
            reason_text = "; ".join(item["reasons"]) if item["reasons"] else "no reasons"
            print(
                f"page {item['page']} score={item['table_likelihood']:.2f} "
                f"type={item['page_type']} reasons={reason_text}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
