#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class Match:
    page: int
    count: int
    snippet: str


def _compact_ws(text: str) -> str:
    return " ".join(text.split())


def _make_snippet(text: str, patterns: list[re.Pattern[str]], max_chars: int) -> str:
    if not text:
        return ""
    matches: list[tuple[int, int]] = []
    for pattern in patterns:
        m = pattern.search(text)
        if m:
            matches.append(m.span())
    if not matches:
        return _compact_ws(text)[:max_chars]

    start, end = sorted(matches, key=lambda x: x[0])[0]
    center = (start + end) // 2
    half = max_chars // 2
    snippet_start = max(0, center - half)
    snippet_end = min(len(text), snippet_start + max_chars)
    snippet = text[snippet_start:snippet_end]
    return _compact_ws(snippet)


def find_pages(
    pdf_path: Path,
    terms: list[str],
    *,
    regex: bool,
    ignore_case: bool,
    max_pages: int | None,
    page_start: int,
    page_end: int | None,
    snippet_chars: int,
) -> list[Match]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not terms:
        raise ValueError("At least one term is required")

    flags = re.IGNORECASE if ignore_case else 0
    patterns: list[re.Pattern[str]] = []
    for term in terms:
        expr = term if regex else re.escape(term)
        patterns.append(re.compile(expr, flags=flags))

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

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

    matches: list[Match] = []
    for page_index in range(start_index, end_index):
        page = doc[page_index]
        text = page.get_text("text") or ""
        count = sum(len(p.findall(text)) for p in patterns)
        if count <= 0:
            continue
        matches.append(
            Match(
                page=page_index + 1,
                count=count,
                snippet=_make_snippet(text, patterns, max_chars=snippet_chars),
            )
        )

    doc.close()
    matches.sort(key=lambda m: (-m.count, m.page))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan a PDF and print pages that match one or more terms."
    )
    parser.add_argument("pdf", type=Path, help="Path to PDF, e.g. docs/manual.pdf")
    parser.add_argument(
        "terms",
        nargs="+",
        help="Terms to search for. Use --regex to treat them as regex patterns.",
    )
    parser.add_argument(
        "--regex",
        action="store_true",
        help="Treat terms as regex patterns (default is literal match).",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Case-sensitive search (default is case-insensitive).",
    )
    parser.add_argument(
        "--page-start",
        type=int,
        default=1,
        help="First PDF page to scan, 1-based. Default: 1",
    )
    parser.add_argument(
        "--page-end",
        type=int,
        default=None,
        help="Last PDF page to scan, 1-based and inclusive.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional page count limit for smoke testing.",
    )
    parser.add_argument(
        "--snippet-chars",
        type=int,
        default=180,
        help="Max characters shown per match snippet. Default: 180",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=50,
        help="How many matching pages to print. Default: 50",
    )

    args = parser.parse_args()

    rows = find_pages(
        args.pdf,
        args.terms,
        regex=args.regex,
        ignore_case=not args.case_sensitive,
        max_pages=args.max_pages,
        page_start=args.page_start,
        page_end=args.page_end,
        snippet_chars=args.snippet_chars,
    )

    print(f"PDF: {args.pdf}")
    print(f"Terms: {args.terms}")
    print(f"Matches: {len(rows)}")
    print("=" * 120)

    for row in rows[: args.top]:
        print(f"page={row.page:<5} count={row.count:<4} {row.snippet}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

