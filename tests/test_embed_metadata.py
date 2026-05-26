import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from embed_chunks import safe_metadata


def test_safe_metadata_preserves_chunk_type_and_table_scalars() -> None:
    chunk = {
        "doc_id": "doc",
        "source": "test.pdf",
        "page_start": 10,
        "page_end": 10,
        "chunk_index": 1,
        "page_chunk_index": 0,
        "token_count": 42,
        "chunk_type": "table_row_group",
        "section_title": "Memory Maps",
        "table_title": "Table 26",
        "table_context": "Segment 8",
        "row_count": 4,
        "column_headers": ["Address", "Size"],
        "text": "do not persist this",
    }

    metadata = safe_metadata(chunk)

    assert metadata["chunk_type"] == "table_row_group"
    assert metadata["section_title"] == "Memory Maps"
    assert metadata["table_title"] == "Table 26"
    assert metadata["table_context"] == "Segment 8"
    assert metadata["row_count"] == 4

    assert "column_headers" not in metadata
    assert "text" not in metadata


def test_safe_metadata_preserves_generic_chunk_defaults() -> None:
    chunk = {
        "doc_id": "doc",
        "source": "test.pdf",
        "page_start": 1,
        "page_end": 1,
        "chunk_index": 0,
        "page_chunk_index": 0,
        "token_count": 10,
        "chunk_type": "generic_page",
        "section_title": "",
        "table_title": "",
        "table_context": "",
        "row_count": 0,
    }

    metadata = safe_metadata(chunk)

    assert metadata["chunk_type"] == "generic_page"
    assert metadata["section_title"] == ""
    assert metadata["table_title"] == ""
    assert metadata["table_context"] == ""
    assert metadata["row_count"] == 0
