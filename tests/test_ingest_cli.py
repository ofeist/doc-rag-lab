import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ingest_document_help_exposes_chunk_mode() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ingest_document.py", "--help"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "--chunk-mode" in result.stdout
    assert "generic" in result.stdout
    assert "mixed" in result.stdout
    assert "--keep-intermediate-artifacts" in result.stdout
