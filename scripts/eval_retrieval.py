#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def load_questions(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    if not isinstance(questions, list):
        raise ValueError(f"Eval file must contain a JSON list: {path}")

    for item in questions:
        if "id" not in item or "question" not in item or "expected_pages" not in item:
            raise ValueError(f"Invalid eval item: {item}")
        if not item["expected_pages"]:
            raise ValueError(f"Eval item has no expected pages: {item['id']}")

    return questions


def page_hit(meta: dict[str, Any], expected_pages: set[int]) -> bool:
    page_start = int(meta.get("page_start", -1))
    page_end = int(meta.get("page_end", page_start))
    return any(page_start <= page <= page_end for page in expected_pages)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate retrieval hit@k over a Chroma collection.")
    parser.add_argument(
        "--eval",
        default="eval/boot_bmhd_eval.json",
        help="Path to retrieval eval JSON file.",
    )
    parser.add_argument("--db", default="vector_db/chroma", help="Persistent ChromaDB directory.")
    parser.add_argument("--collection", default="technical_docs", help="Chroma collection name.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="SentenceTransformer model name. Must match embed_chunks.py.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve.")
    parser.add_argument(
        "--fail-under-hit3",
        type=float,
        default=None,
        help="Optional hit@3 threshold between 0 and 1 that makes the command fail if not met.",
    )
    args = parser.parse_args()

    questions = load_questions(Path(args.eval))

    db_path = Path(args.db)
    if not db_path.exists():
        raise FileNotFoundError(f"Chroma DB not found: {db_path}. Run embed_chunks.py first.")

    print(f"Loading embedding model: {args.model}")
    model = SentenceTransformer(args.model)

    client = chromadb.PersistentClient(
        path=str(db_path),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_collection(name=args.collection)

    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_k = 0

    print()
    print(f"Eval file: {args.eval}")
    print(f"Questions: {len(questions)}")
    print(f"Top-k: {args.top_k}")
    print("=" * 120)

    for item in questions:
        expected_pages = {int(page) for page in item["expected_pages"]}
        query_embedding = model.encode(
            [item["question"]],
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()[0]

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=args.top_k,
            include=["metadatas", "distances"],
        )

        metas = results["metadatas"][0]
        distances = results["distances"][0]
        top_pages = [f"{m.get('page_start')}-{m.get('page_end')}" for m in metas]

        this_hit_at_1 = bool(metas) and page_hit(metas[0], expected_pages)
        this_hit_at_3 = any(page_hit(meta, expected_pages) for meta in metas[:3])
        this_hit_at_k = any(page_hit(meta, expected_pages) for meta in metas)

        hit_at_1 += int(this_hit_at_1)
        hit_at_3 += int(this_hit_at_3)
        hit_at_k += int(this_hit_at_k)

        status = "PASS" if this_hit_at_3 else "FAIL"
        distance_text = ", ".join(f"{distance:.4f}" for distance in distances[:3])

        print(f"{item['id']} {status}")
        print(f"  question: {item['question']}")
        print(f"  expected: {sorted(expected_pages)}")
        print(f"  top_pages: {top_pages}")
        print(f"  top_distances: {distance_text}")
        if item.get("notes"):
            print(f"  notes: {item['notes']}")
        print()

    total = len(questions)
    print("=" * 120)
    print(f"hit@1: {hit_at_1}/{total} = {hit_at_1 / total:.2%}")
    print(f"hit@3: {hit_at_3}/{total} = {hit_at_3 / total:.2%}")
    print(f"hit@{args.top_k}: {hit_at_k}/{total} = {hit_at_k / total:.2%}")

    hit_at_3_ratio = hit_at_3 / total
    if args.fail_under_hit3 is not None and hit_at_3_ratio < args.fail_under_hit3:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
