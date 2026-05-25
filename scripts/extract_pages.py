#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import fitz


def extract_pages(pdf_path: Path, max_pages: int | None = None) -> list[dict]:
    """
    Extract text from a PDF page-by-page.

    This is a smoke test, not the final ingestion pipeline.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    records: list[dict] = []

    total_pages = len(doc)
    pages_to_process = total_pages if max_pages is None else min(max_pages, total_pages)

    for page_index in range(pages_to_process):
        page = doc[page_index]
        text = page.get_text("text")

        records.append(
            {
                "source": pdf_path.name,
                "source_path": str(pdf_path),
                "page": page_index + 1,
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
        help="Optional limit for smoke testing, e.g. --max-pages 10",
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Do not print page preview to terminal.",
    )

    args = parser.parse_args()

    records = extract_pages(args.pdf, args.max_pages)
    write_jsonl(records, args.out)

    print(f"Extracted pages: {len(records)}")
    print(f"Output written to: {args.out}")

    if not args.no_preview:
        print_preview(records)


if __name__ == "__main__":
    main()
