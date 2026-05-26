#!/usr/bin/env python3

import json
from pathlib import Path


TABLE_LIKE_TERMS = [
    "address range",
    "size",
    "segment",
    "cpu0",
    "cpu1",
    "cpu2",
    "cpu3",
    "dspr",
    "pspr",
    "dlmu",
    "lmuram",
    "boot rom",
    "program flash",
    "data flash",
    "pflash",
    "eeprom",
    "ucb",
    "cfs",
    "sota",
]


def is_table_like_query(query: str) -> bool:
    low = query.lower()
    return any(term in low for term in TABLE_LIKE_TERMS)


def corpus_has_table_row_groups(chunks_path: Path) -> bool:
    with chunks_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} in {chunks_path}") from exc
            if record.get("chunk_type") == "table_row_group":
                return True
    return False


def auto_selection_reason(query: str, has_table_row_groups: bool) -> str:
    table_like = is_table_like_query(query)
    if table_like and has_table_row_groups:
        return "table-like query and table_row_group chunks present"
    if not table_like:
        return "query is not table-like"
    return "no table_row_group chunks present"


def resolve_retrieval_mode(requested_mode: str, query: str, chunks_path: Path) -> str:
    if requested_mode != "auto":
        return requested_mode
    if is_table_like_query(query) and corpus_has_table_row_groups(chunks_path):
        return "bm25_table_boost"
    return "hybrid"
