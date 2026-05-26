import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from retrieval_mode import (
    corpus_has_table_row_groups,
    is_table_like_query,
    resolve_retrieval_mode,
)


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def test_corpus_has_table_row_groups_detects_table_chunks(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    write_jsonl(
        chunks,
        [
            {"chunk_type": "generic_page"},
            {"chunk_type": "table_row_group"},
        ],
    )

    assert corpus_has_table_row_groups(chunks) is True


def test_corpus_has_table_row_groups_false_for_generic_only(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    write_jsonl(chunks, [{"chunk_type": "generic_page"}])

    assert corpus_has_table_row_groups(chunks) is False


def test_table_like_query_detector_matches_address_questions() -> None:
    assert is_table_like_query("What address range maps to Program Flash 0?") is True


def test_auto_selects_bm25_table_boost_for_table_query_and_table_corpus(
    tmp_path: Path,
) -> None:
    chunks = tmp_path / "chunks.jsonl"
    write_jsonl(chunks, [{"chunk_type": "table_row_group"}])

    assert (
        resolve_retrieval_mode(
            requested_mode="auto",
            query="What address range maps to Program Flash 0?",
            chunks_path=chunks,
        )
        == "bm25_table_boost"
    )


def test_auto_selects_hybrid_for_prose_query_even_with_table_corpus(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    write_jsonl(chunks, [{"chunk_type": "table_row_group"}])

    assert (
        resolve_retrieval_mode(
            requested_mode="auto",
            query="What does the startup software do after reset?",
            chunks_path=chunks,
        )
        == "hybrid"
    )


def test_auto_selects_hybrid_for_table_query_without_table_corpus(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    write_jsonl(chunks, [{"chunk_type": "generic_page"}])

    assert (
        resolve_retrieval_mode(
            requested_mode="auto",
            query="What address range maps to Program Flash 0?",
            chunks_path=chunks,
        )
        == "hybrid"
    )


def test_manual_mode_is_not_changed(tmp_path: Path) -> None:
    chunks = tmp_path / "chunks.jsonl"
    write_jsonl(chunks, [{"chunk_type": "table_row_group"}])

    assert (
        resolve_retrieval_mode(
            requested_mode="hybrid",
            query="What address range maps to Program Flash 0?",
            chunks_path=chunks,
        )
        == "hybrid"
    )
