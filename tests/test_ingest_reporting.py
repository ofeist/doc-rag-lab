import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ingest_document import (
    print_mixed_report,
    summarize_chunks,
    summarize_table_candidates,
)


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_summarize_chunks_counts_chunk_types(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"

    write_jsonl(
        chunks_path,
        [
            {"chunk_type": "generic_page", "page_start": 1, "page_end": 1},
            {"chunk_type": "table_row_group", "page_start": 2, "page_end": 2},
            {"chunk_type": "table_row_group", "page_start": 3, "page_end": 3},
            {"chunk_type": "generic_residual", "page_start": 2, "page_end": 2},
        ],
    )

    # summarize_chunks returns (Counter, routed_pages) in the P3-20 implementation.
    chunk_types, routed_pages = summarize_chunks(chunks_path)

    assert chunk_types["generic_page"] == 1
    assert chunk_types["table_row_group"] == 2
    assert chunk_types["generic_residual"] == 1
    assert routed_pages == [2, 3]


def test_summarize_table_candidates_counts_page_types(tmp_path: Path) -> None:
    candidates_path = tmp_path / "candidates.jsonl"

    write_jsonl(
        candidates_path,
        [
            {
                "page": 1,
                "page_type": "address_map_table",
                "recommended_chunker": "table_row_group",
                "table_likelihood": 0.9,
            },
            {
                "page": 2,
                "page_type": "generic_table",
                "recommended_chunker": "generic",
                "table_likelihood": 0.7,
            },
            {
                "page": 3,
                "page_type": "prose",
                "recommended_chunker": "generic",
                "table_likelihood": 0.1,
            },
        ],
    )

    summary = summarize_table_candidates(candidates_path)

    assert summary["candidate_count"] == 3
    assert summary["address_map_table"] == 1
    assert summary["generic_table"] == 1


def test_mixed_report_warns_when_no_table_row_group(tmp_path: Path, capsys) -> None:
    candidates_summary = {
        "candidate_count": 0,
        "address_map_table": 0,
        "generic_table": 0,
    }
    chunk_types = {
        "generic_page": 3,
        "table_row_group": 0,
        "generic_residual": 0,
    }

    print_mixed_report(
        doc_id="test_doc",
        pdf=Path("test.pdf"),
        page_ranges="1-3",
        raw_pages_path=tmp_path / "raw.jsonl",
        candidates_path=tmp_path / "candidates.jsonl",
        chunks_path=tmp_path / "chunks.jsonl",
        db_path=tmp_path / "chroma",
        collection="technical_docs",
        page_count=3,
        chunk_count=3,
        candidates_summary=candidates_summary,
        chunk_types=chunk_types,
        routed_pages=[],
    )

    captured = capsys.readouterr()

    assert "WARNING" in captured.out
    assert "no table_row_group chunks were produced" in captured.out


def test_mixed_report_warns_when_too_many_pages_are_table_routed(tmp_path: Path, capsys) -> None:
    candidates_summary = {
        "candidate_count": 10,
        "address_map_table": 10,
        "generic_table": 0,
    }
    chunk_types = {
        "generic_page": 0,
        "table_row_group": 10,
        "generic_residual": 0,
    }

    print_mixed_report(
        doc_id="test_doc",
        pdf=Path("test.pdf"),
        page_ranges="1-10",
        raw_pages_path=tmp_path / "raw.jsonl",
        candidates_path=tmp_path / "candidates.jsonl",
        chunks_path=tmp_path / "chunks.jsonl",
        db_path=tmp_path / "chroma",
        collection="technical_docs",
        page_count=10,
        chunk_count=10,
        candidates_summary=candidates_summary,
        chunk_types=chunk_types,
        routed_pages=list(range(1, 11)),
    )

    captured = capsys.readouterr()

    assert "WARNING" in captured.out
    assert "more than 60% of pages were routed to table_row_group" in captured.out
