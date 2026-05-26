import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ingest_document import cleanup_mixed_intermediates


def test_cleanup_mixed_intermediates_removes_raw_and_candidates(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    candidates = tmp_path / "candidates.jsonl"
    chunks = tmp_path / "chunks.jsonl"

    raw.write_text("raw\n", encoding="utf-8")
    candidates.write_text("candidates\n", encoding="utf-8")
    chunks.write_text("chunks\n", encoding="utf-8")

    deleted = cleanup_mixed_intermediates([raw, candidates], keep=False)

    assert raw.exists() is False
    assert candidates.exists() is False
    assert chunks.exists() is True
    assert deleted == [raw, candidates]


def test_cleanup_mixed_intermediates_keeps_files_when_requested(tmp_path: Path) -> None:
    raw = tmp_path / "raw.jsonl"
    candidates = tmp_path / "candidates.jsonl"

    raw.write_text("raw\n", encoding="utf-8")
    candidates.write_text("candidates\n", encoding="utf-8")

    deleted = cleanup_mixed_intermediates([raw, candidates], keep=True)

    assert raw.exists() is True
    assert candidates.exists() is True
    assert deleted == []
