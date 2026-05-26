import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from chunk_pages import build_chunks


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def test_generic_chunks_emit_schema_compatible_fields(tmp_path: Path) -> None:
    raw_pages = tmp_path / "raw_pages.jsonl"

    write_jsonl(
        raw_pages,
        [
            {
                "page": 1,
                "text": (
                    "This is a simple prose page. "
                    "It contains enough text to produce a normal generic chunk. "
                    "No table structure is required for this test."
                ),
            }
        ],
    )

    chunks = build_chunks(
        raw_pages_path=raw_pages,
        source="test.pdf",
        chunk_size=80,
        overlap=10,
    )

    assert chunks
    chunk = chunks[0]

    assert chunk["chunk_type"] == "generic_page"
    assert chunk["section_title"] == ""
    assert chunk["table_title"] == ""
    assert chunk["table_context"] == ""
    assert chunk["column_headers"] == []
    assert chunk["row_count"] == 0

    required_fields = {
        "chunk_id",
        "source",
        "page_start",
        "page_end",
        "page_chunk_index",
        "chunk_index",
        "token_count",
        "text",
        "chunk_type",
        "section_title",
        "table_title",
        "table_context",
        "column_headers",
        "row_count",
    }

    assert required_fields.issubset(chunk.keys())
