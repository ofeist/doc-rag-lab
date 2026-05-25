#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import fitz


def parse_page_ranges(value: str, total_pages: int) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    seen_pages: set[int] = set()

    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue

        if "-" in part:
            raw_start, raw_end = part.split("-", 1)
            page_start = int(raw_start.strip())
            page_end = int(raw_end.strip())
        else:
            page_start = int(part)
            page_end = page_start

        if page_start < 1:
            raise ValueError("--page-ranges values must be >= 1")
        if page_end < page_start:
            raise ValueError(f"Invalid page range: {part}")
        if page_start > total_pages:
            raise ValueError(f"Page range starts beyond PDF page count ({total_pages}): {part}")

        page_end = min(page_end, total_pages)
        unique_pages = [page for page in range(page_start, page_end + 1) if page not in seen_pages]
        if not unique_pages:
            continue

        range_start = unique_pages[0]
        previous_page = unique_pages[0]
        for page in unique_pages:
            seen_pages.add(page)
            if page == previous_page or page == previous_page + 1:
                previous_page = page
                continue
            ranges.append((range_start, previous_page))
            range_start = page
            previous_page = page
        ranges.append((range_start, previous_page))

    if not ranges:
        raise ValueError("--page-ranges did not contain any valid pages")

    return ranges


def extract_pages(
    pdf_path: Path,
    max_pages: int | None = None,
    page_start: int = 1,
    page_end: int | None = None,
    page_ranges: str | None = None,
) -> list[dict]:
    """
    Extract text from a PDF page-by-page.

    This is a smoke test, not the final ingestion pipeline.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    records: list[dict] = []

    total_pages = len(doc)
    if page_ranges is not None:
        if max_pages is not None or page_start != 1 or page_end is not None:
            raise ValueError("--page-ranges cannot be combined with --max-pages, --page-start, or --page-end")
        ranges = parse_page_ranges(page_ranges, total_pages)
    else:
        if page_start < 1:
            raise ValueError("--page-start must be >= 1")
        if page_start > total_pages:
            raise ValueError(f"--page-start exceeds PDF page count ({total_pages})")
        if page_end is not None and page_end < page_start:
            raise ValueError("--page-end must be >= --page-start")

        start_index = page_start - 1
        end_index = total_pages if page_end is None else min(page_end, total_pages)

        if max_pages is not None:
            if max_pages < 1:
                raise ValueError("--max-pages must be >= 1")
            end_index = min(end_index, start_index + max_pages)

        ranges = [(start_index + 1, end_index)]

    for range_start, range_end in ranges:
        for page_number in range(range_start, range_end + 1):
            page_index = page_number - 1
            page = doc[page_index]
            text = page.get_text("text")

            records.append(
                {
                    "source": pdf_path.name,
                    "source_path": str(pdf_path),
                    "page": page_number,
                    "page_index": page_index,
                    "total_pages": total_pages,
                    "char_count": len(text),
                    "text": text,
                }
            )

    doc.close()
    return records


def write_jsonl(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_preview(
    records: list[dict],
    preview_pages: int = 3,
    preview_chars: int = 1000,
) -> None:
    for record in records[:preview_pages]:
        print("\n" + "=" * 80)
        print(f"PAGE {record['page']} | chars={record['char_count']}")
        print("=" * 80)
        print(record["text"][:preview_chars])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract page-by-page text from a PDF into JSONL."
    )
    parser.add_argument("pdf", type=Path, help="Path to the PDF file, e.g. docs/sample.pdf")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/raw_pages.jsonl"),
        help="Output JSONL path. Default: data/raw_pages.jsonl",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional page count limit for smoke testing, e.g. --max-pages 10",
    )
    parser.add_argument(
        "--page-start",
        type=int,
        default=1,
        help="First PDF page to extract, 1-based. Default: 1",
    )
    parser.add_argument(
        "--page-end",
        type=int,
        default=None,
        help="Last PDF page to extract, 1-based and inclusive.",
    )
    parser.add_argument(
        "--page-ranges",
        default=None,
        help="Comma-separated 1-based PDF page ranges, e.g. 115-126,257,310-312.",
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Do not print page preview to terminal.",
    )

    args = parser.parse_args()

    records = extract_pages(
        args.pdf,
        max_pages=args.max_pages,
        page_start=args.page_start,
        page_end=args.page_end,
        page_ranges=args.page_ranges,
    )
    write_jsonl(records, args.out)

    print(f"Extracted pages: {len(records)}")
    print(f"Output written to: {args.out}")

    if not args.no_preview:
        print_preview(records)


if __name__ == "__main__":
    main()
