#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Any


CONFIG_PATH = Path("configs/slices.json")
REQUIRED_FIELDS = [
    "description",
    "pdf",
    "page_ranges",
    "doc_id",
    "collection",
    "eval",
    "answer_output",
    "grading",
    "default_retrieval_mode",
    "default_top_k",
    "default_candidate_k",
    "default_rrf_k",
    "default_model",
    "default_max_tokens",
    "recommended_chunk_tokens",
    "recommended_overlap_tokens",
    "recommended_retrieval_mode",
]


def load_config(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a JSON object: {path}")
    for slice_id, config in data.items():
        if not isinstance(slice_id, str) or not slice_id:
            raise ValueError("Slice ids must be non-empty strings.")
        if not isinstance(config, dict):
            raise ValueError(f"Slice config must be an object: {slice_id}")
    return data


def validate_slice(slice_id: str, config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in config:
            errors.append(f"{slice_id}: missing field '{field}'")

    for field in ("pdf", "eval"):
        value = config.get(field)
        if isinstance(value, str) and value and not Path(value).exists():
            errors.append(f"{slice_id}: referenced {field} does not exist: {value}")

    if config.get("doc_id") != slice_id:
        errors.append(f"{slice_id}: doc_id should match slice id")

    return errors


def main() -> int:
    config = load_config(CONFIG_PATH)
    errors: list[str] = []

    for slice_id, slice_config in config.items():
        errors.extend(validate_slice(slice_id, slice_config))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: {len(config)} slices configured")
    for slice_id in config:
        print(f"- {slice_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
